import json
import random
import re
import time
from threading import Timer

from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

browser: webdriver.Chrome = None
config = None
active_meeting = None
uuid_regex = r"\b[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}\b"
hangup_thread: Timer = None


class Meeting:
    def __init__(self, started_at, id):
        self.started_at = started_at
        self.id = id


class Channel:
    def __init__(self, name, meetings, blacklisted=False):
        self.name = name
        self.meetings = meetings
        self.blacklisted = blacklisted

    def __str__(self):
        return self.name + " [BLACKLISTED]" if self.blacklisted else self.name

    def get_elem(self, parent):
        try:
            channel_elem = parent.find_element_by_css_selector(f"ul>ng-include>li[data-tid*='channel-{self.name}-li']")
        except exceptions.NoSuchElementException:
            return None

        return channel_elem


class Team:
    def __init__(self, name, elem, channels=None):
        if channels is None:
            channels = []
        self.name = name
        self.elem = elem
        self.channels = channels

    def __str__(self):
        channel_string = '\n\t'.join([str(channel) for channel in self.channels])

        return f"{self.name}\n\t{channel_string}"

    def expand_channels(self):
        try:
            elem = self.elem.find_element_by_css_selector("div[class='channels']")
        except exceptions.NoSuchElementException:
            try:
                self.elem.click()
                elem = self.elem.find_element_by_css_selector("div[class='channels']")
            except exceptions.NoSuchElementException:
                return None
        return elem

    def init_channels(self):
        channels_elem = self.expand_channels()

        channel_elems = channels_elem.find_elements_by_css_selector("ul>ng-include>li")

        channel_names = [channel_elem.get_attribute("data-tid") for channel_elem in channel_elems]
        channel_names = [channel_name[channel_name.find('-channel-') + 9:channel_name.rfind("-li")] for channel_name
                         in
                         channel_names if channel_name is not None]

        self.channels = [Channel(channel_name, []) for channel_name in channel_names]

    def check_blacklist(self):
        blacklist = config['blacklist']
        blacklist_item = next((team for team in blacklist if team['team_name'] == self.name), None)
        if blacklist_item is None:
            return

        if len(blacklist_item['channel_names']) == 0:
            for channel in self.channels:
                channel.blacklisted = True
        else:
            blacklist_channels = [x for x in self.channels if x.name in blacklist_item['channel_names']]
            for blacklist_channel in blacklist_channels:
                blacklist_channel.blacklisted = True

    def update_meetings(self):
        channels = self.expand_channels()

        for channel in self.channels:
            if channel.blacklisted:
                continue

            channel_elem = channel.get_elem(channels)
            try:
                active_meeting_elem = channel_elem.find_element_by_css_selector(
                    "a>active-calls-counter[is-meeting='true']")
            except exceptions.NoSuchElementException:
                continue

            active_meeting_elem.click()

            if wait_till_found("button[ng-click='ctrl.joinCall()']", 60) is None:
                continue

            join_meeting_elems = browser.find_elements_by_css_selector("button[ng-click='ctrl.joinCall()']")

            meeting_ids = []
            for join_meeting_elem in join_meeting_elems:
                try:
                    uuid = re.search(uuid_regex, join_meeting_elem.get_attribute('track-data'))
                    if uuid is None:
                        continue

                    meeting_ids.append(uuid.group(0))
                except exceptions.StaleElementReferenceException:
                    continue

            # remove duplicates
            meeting_ids = list(dict.fromkeys(meeting_ids))

            for meeting_id in meeting_ids:
                if meeting_id not in [meeting.id for meeting in channel.meetings]:
                    channel.meetings.append(Meeting(time.time(), meeting_id))

    def update_elem(self):
        self.elem = browser.find_element_by_css_selector(
            f"ul>li[role='treeitem'][class='match-parent team left-rail-item-kb-l2']>div[data-tid='team-{self.name}-li']")


def load_config():
    global config
    with open('config.json') as json_data_file:
        config = json.load(json_data_file)


def wait_till_found(sel, timeout):
    try:
        element_present = EC.presence_of_element_located((By.CSS_SELECTOR, sel))
        WebDriverWait(browser, timeout).until(element_present)

        return browser.find_element_by_css_selector(sel)
    except exceptions.TimeoutException:
        print("Timeout waiting for element.")
        return None


def get_teams():
    # find all team names
    team_elems = browser.find_elements_by_css_selector(
        "ul>li[role='treeitem']>div:not(.ts-tree-header)")
    team_names = [team_elem.get_attribute("data-tid") for team_elem in team_elems]
    team_names = [team_name[team_name.find('team-') + 5:team_name.rfind("-li")] for team_name in team_names]

    team_list = [Team(team_names[i], team_elems[i], None) for i in range(len(team_elems))]
    return team_list


def join_newest_meeting(teams):
    global active_meeting, hangup_thread

    meeting_to_join = Meeting(-1, None) if active_meeting is None else active_meeting
    meeting_team = None
    meeting_channel = None

    for team in teams:
        for channel in team.channels:
            if channel.blacklisted:
                continue

            for meeting in channel.meetings:
                if meeting.started_at > meeting_to_join.started_at:
                    meeting_to_join = meeting
                    meeting_team = team
                    meeting_channel = channel

    if meeting_team is None:
        return False

    hangup()

    channels_elem = meeting_team.expand_channels()

    meeting_channel.get_elem(channels_elem).click()

    join_btn = wait_till_found(f"button[track-data*='{meeting_to_join.id}']", 30)
    if join_btn is None:
        return

    join_btn.click()

    join_now_btn = wait_till_found("button[data-tid='prejoin-join-button']", 30)
    if join_now_btn is None:
        return

    # turn camera off
    video_btn = browser.find_element_by_css_selector("toggle-button[data-tid='toggle-video']>div>button")
    video_is_on = video_btn.get_attribute("aria-pressed")
    if video_is_on == "true":
        video_btn.click()

    # turn mic off
    audio_btn = browser.find_element_by_css_selector("toggle-button[data-tid='toggle-mute']>div>button")
    audio_is_on = audio_btn.get_attribute("aria-pressed")
    if audio_is_on == "true":
        audio_btn.click()

    if 'random_delay' in config and config['random_delay']:
        delay = random.randrange(10, 31, 1)
        print(f"Wating for {delay}s")
        time.sleep(delay)

    join_now_btn.click()

    browser.find_element_by_css_selector("span[data-tid='appBarText-Teams']").click()

    active_meeting = meeting_to_join

    if 'auto_leave_after_min' in config and config['auto_leave_after_min'] > 0:
        hangup_thread = Timer(config['auto_leave_after_min']*60, hangup)
        hangup_thread.start()

    return True


def hangup():
    try:
        hangup_btn = browser.find_element_by_css_selector("button[data-tid='call-hangup']")
        hangup_btn.click()

        if hangup_thread:
            hangup_thread.cancel()
    except exceptions.NoSuchElementException:
        return


def main():
    global browser, config

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    browser = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=chrome_options)

    load_config()

    browser.get("https://teams.microsoft.com")

    if config['email'] != "" and config['password'] != "":
        login_email = wait_till_found("input[type='email']", 30)
        if login_email is not None:
            login_email.send_keys(config['email'])
            time.sleep(1)

        # find the element again to avoid StaleElementReferenceException
        login_email = wait_till_found("input[type='email']", 5)
        if login_email is not None:
            login_email.send_keys(Keys.ENTER)

        login_pwd = wait_till_found("input[type='password']", 30)
        if login_pwd is not None:
            login_pwd.send_keys(config['password'])
            time.sleep(1)

        # find the element again to avoid StaleElementReferenceException
        login_pwd = wait_till_found("input[type='password']", 5)
        if login_pwd is not None:
            login_pwd.send_keys(Keys.ENTER)

        time.sleep(1)
        keep_logged_in = wait_till_found("input[id='idBtn_Back']", 5)
        if keep_logged_in is not None:
            keep_logged_in.click()

    print("Waiting for correct page...")
    if wait_till_found("div[data-tid='team-channel-list']", 60 * 5) is None:
        exit(1)

    teams = get_teams()
    for team in teams:
        team.init_channels()
        team.check_blacklist()

    print("\nFound Teams and Channels: ")
    for team in teams:
        print(team)

    if 'start_automatically' not in config or not config['start_automatically']:
        sel_str = "\nStart [s], Reload teams [r], Quit [q]\n"

        selection = input(sel_str).lower()
        while selection != 's':
            if selection == 'q':
                browser.close()
                exit(0)
            if selection == 'r':
                load_config()
                teams = get_teams()
                for team in teams:
                    team.init_channels()
                    team.check_blacklist()

                for team in teams:
                    print(team)

            selection = input(sel_str).lower()

    print("\nWorking...")

    while 1:
        time.sleep(2)
        for team in teams:
            team.update_meetings()

        if join_newest_meeting(teams):
            for team in teams:
                team.update_elem()


if __name__ == "__main__":
    main()
