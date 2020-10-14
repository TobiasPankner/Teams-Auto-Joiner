import json
import random
import re
import time
from datetime import datetime
from threading import Timer

from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.utils import ChromeType
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from msedge.selenium_tools import Edge, EdgeOptions

browser: webdriver.Chrome = None
config = None
meetings = []
current_meeting = None
already_joined_ids = []
active_correlation_id = ""
hangup_thread: Timer = None
conversation_link = "https://teams.microsoft.com/_#/conversations/a"
mode = 3
uuid_regex = r"\b[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}\b"


class Team:
    def __init__(self, name, t_id, channels=None):
        self.name = name
        self.t_id = t_id
        if channels is None:
            self.get_channels()
        else:
            self.channels = channels

        self.check_blacklist()

    def __str__(self):
        channel_string = '\n\t'.join([str(channel) for channel in self.channels])

        return f"{self.name}\n\t{channel_string}"

    def get_elem(self):
        team_header = browser.find_element_by_css_selector(f"h3[id='{self.t_id}'")
        team_elem = team_header.find_element_by_xpath("..")
        return team_elem

    def expand_channels(self):
        try:
            self.get_elem().find_element_by_css_selector("div.channels")
        except exceptions.NoSuchElementException:
            try:
                self.get_elem().click()
                self.get_elem().find_element_by_css_selector("div.channels")
            except (exceptions.NoSuchElementException, exceptions.ElementNotInteractableException):
                return None

    def get_channels(self):
        self.expand_channels()
        channels = self.get_elem().find_elements_by_css_selector(".channels > ul > ng-include > li")

        channel_names = [channel.get_attribute("data-tid") for channel in channels]
        channel_names = [channel_name[channel_name.find("channel-") + 8:channel_name.find("-li")] for channel_name in
                         channel_names if channel_name is not None]

        channels_ids = [channel.get_attribute("id").replace("channel-", "") for channel in channels]

        meeting_states = []
        for channel in channels:
            try:
                channel.find_element_by_css_selector("a > active-calls-counter")
                meeting_states.append(True)
            except exceptions.NoSuchElementException:
                meeting_states.append(False)

        self.channels = [Channel(channel_names[i], channels_ids[i], has_meeting=meeting_states[i]) for i in
                         range(len(channel_names))]

    def check_blacklist(self):
        blacklist = config['blacklist']
        blacklist_item = next((bl_team for bl_team in blacklist if bl_team['team_name'] == self.name), None)
        if blacklist_item is None:
            return

        if len(blacklist_item['channel_names']) == 0:
            for channel in self.channels:
                channel.blacklisted = True
        else:
            for channel in self.channels:
                if channel.name in blacklist_item['channel_names']:
                    channel.blacklisted = True


class Channel:
    def __init__(self, name, c_id, blacklisted=False, has_meeting=False):
        self.name = name
        self.c_id = c_id
        self.blacklisted = blacklisted
        self.has_meeting = has_meeting

    def __str__(self):
        return self.name + (" [BLACKLISTED]" if self.blacklisted else "") + (" [MEETING]" if self.has_meeting else "")


class Meeting:
    def __init__(self, m_id, time_started, title, calendar_meeting=False, channel_id=None):
        self.m_id = m_id
        self.time_started = time_started
        self.title = title
        self.calendar_meeting = calendar_meeting
        self.calendar_blacklisted = calendar_meeting and self.check_blacklist_calendar_meeting()
        self.channel_id = channel_id

    def check_blacklist_calendar_meeting(self):
        if "blacklist_meeting_re" in config and config['blacklist_meeting_re'] != "":

            regex = config['blacklist_meeting_re']
            return True if re.search(regex, self.title) else False

    def __str__(self):
        return f"\t{self.title} {self.time_started}" + (" [Calendar]" if self.calendar_meeting else " [Channel]") + (
            " [BLACKLISTED]" if self.calendar_blacklisted else "")


def load_config():
    global config
    with open('config.json') as json_data_file:
        config = json.load(json_data_file)


def init_browser():
    global browser

    if "chrome_type" in config and config['chrome_type'] == "msedge":
        chrome_options = EdgeOptions()
        chrome_options.use_chromium = True

    else:
        chrome_options = webdriver.ChromeOptions()

    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--use-fake-ui-for-media-stream')
    chrome_options.add_experimental_option('prefs', {
        'credentials_enable_service': False,
        'profile.default_content_setting_values.media_stream_mic': 1,
        'profile.default_content_setting_values.media_stream_camera': 1,
        'profile.default_content_setting_values.geolocation': 1,
        'profile.default_content_setting_values.notifications': 1,
        'profile': {
            'password_manager_enabled': False
        }
    })

    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])

    if 'headless' in config and config['headless']:
        chrome_options.add_argument('--headless')
        print("Enabled headless mode")

    if 'mute_audio' in config and config['mute_audio']:
        chrome_options.add_argument("--mute-audio")

    if 'chrome_type' in config:
        if config['chrome_type'] == "chromium":
            browser = webdriver.Chrome(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install(),
                                       options=chrome_options)
        elif config['chrome_type'] == "msedge":
            browser = Edge(EdgeChromiumDriverManager().install(), options=chrome_options)
        else:
            browser = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    else:
        browser = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

    # make the window a minimum width to show the meetings menu
    window_size = browser.get_window_size()
    if window_size['width'] < 1200:
        print("Resized window width")
        browser.set_window_size(1200, window_size['height'])

    if window_size['height'] < 850:
        print("Resized window height")
        browser.set_window_size(window_size['width'], 850)


def wait_until_found(sel, timeout, print_error=True):
    try:
        element_present = EC.visibility_of_element_located((By.CSS_SELECTOR, sel))
        WebDriverWait(browser, timeout).until(element_present)

        return browser.find_element_by_css_selector(sel)
    except exceptions.TimeoutException:
        if print_error:
            print(f"Timeout waiting for element: {sel}")
        return None


def switch_to_teams_tab():
    teams_button = wait_until_found("button.app-bar-link > ng-include > svg.icons-teams", 5)
    if teams_button is not None:
        teams_button.click()


def switch_to_calendar_tab():
    calendar_button = wait_until_found("button.app-bar-link > ng-include > svg.icons-calendar", 5)
    if calendar_button is not None:
        calendar_button.click()


def change_organisation(org_num):
    select_change_org = wait_until_found("button.tenant-switcher", 20)
    if select_change_org is None:
        print("Something went wrong while changing the organisation")
        return

    select_change_org.click()

    change_org = wait_until_found(f"li.tenant-option[aria-posinset='{org_num}']", 20)
    if change_org is None:
        print("Something went wrong while changing the organisation")
        return

    change_org.click()
    time.sleep(5)

    use_web_instead = wait_until_found(".use-app-lnk", 5, print_error=False)
    if use_web_instead is not None:
        use_web_instead.click()

    time.sleep(1)


def prepare_page(include_calendar):
    try:
        browser.execute_script("document.getElementById('toast-container').remove()")
    except exceptions.JavascriptException:
        pass

    if include_calendar:
        switch_to_calendar_tab()

        view_switcher = wait_until_found(".ms-CommandBar-secondaryCommand > div > button[class*='__topBarContent']", 5)

        if view_switcher is not None:
            try:
                browser.execute_script("arguments[0].click();", view_switcher)
                time.sleep(2)
            except Exception as e:
                print(e)
                return

            day_button = wait_until_found(
                "li[role='presentation'].ms-ContextualMenu-item>button[aria-posinset='1']", 2, print_error=False)
            if day_button is None:
                browser.execute_script("arguments[0].click();", view_switcher)
                time.sleep(2)

            day_button = wait_until_found(
                "li[role='presentation'].ms-ContextualMenu-item>button[aria-posinset='1']", 2)
            if day_button is not None:
                try:
                    day_button.click()
                    time.sleep(2)
                except Exception as e:
                    print(e)
                    pass


def get_all_teams():
    team_elems = browser.find_elements_by_css_selector(
        "ul>li[role='treeitem']>div[sv-element]")

    team_names = [team_elem.get_attribute("data-tid") for team_elem in team_elems]
    team_names = [team_name[team_name.find('team-') + 5:team_name.rfind("-li")] for team_name in team_names]

    team_headers = [team_elem.find_element_by_css_selector("h3") for team_elem in team_elems]
    team_ids = [team_header.get_attribute("id") for team_header in team_headers]

    return [Team(team_names[i], team_ids[i]) for i in range(len(team_elems))]


def get_meetings(teams):
    global meetings

    for team in teams:
        for channel in team.channels:
            if channel.has_meeting and not channel.blacklisted:
                browser.execute_script(f'window.location = "{conversation_link}a?threadId={channel.c_id}&ctx=channel";')
                switch_to_teams_tab()

                meeting_elem = wait_until_found(".ts-calling-thread-header", 10)
                if meeting_elem is None:
                    continue
                meeting_elems = browser.find_elements_by_css_selector(".ts-calling-thread-header")
                for meeting_elem in meeting_elems:
                    meeting_id = meeting_elem.get_attribute("id")
                    time_started = int(meeting_id.replace("m", "")[:-3])

                    # already joined calendar meeting
                    correlation_id = meeting_elem.find_element_by_css_selector(
                        "calling-join-button > button").get_attribute("track-data")
                    if active_correlation_id != "" and correlation_id.find(active_correlation_id) != -1:
                        continue

                    meetings.append(
                        Meeting(meeting_id, time_started, f"{team.name} -> {channel.name}", channel_id=channel.c_id))


def get_calendar_meetings():
    global meetings

    if wait_until_found("div[class*='__cardHolder']", 20) is None:
        return

    join_buttons = browser.find_elements_by_css_selector("button[class*='__joinButton'], button[class*='__activeCall']")
    if len(join_buttons) == 0:
        return

    meeting_cards = []
    for join_button in join_buttons:
        meeting_card = join_button.find_element_by_xpath("../../..")
        meeting_cards.append(meeting_card)

    for meeting_card in meeting_cards:
        style_string = meeting_card.get_attribute("style")
        top_offset = float(style_string[style_string.find("top: ") + 5:style_string.find("rem;")])

        minutes_from_midnight = int(top_offset / .135)

        midnight = datetime.now().replace(hour=0, minute=0, second=0)
        midnight = int(datetime.timestamp(midnight))

        start_time = midnight + minutes_from_midnight * 60

        sec_meeting_card = meeting_card.find_element_by_css_selector("div")
        meeting_name = sec_meeting_card.get_attribute("title").replace("\n", " ")

        meeting_id = sec_meeting_card.get_attribute("id")

        meetings.append(Meeting(meeting_id, start_time, meeting_name, calendar_meeting=True))


def decide_meeting():
    global meetings

    newest_meetings = []

    meetings = [meeting for meeting in meetings if not meeting.calendar_blacklisted]
    if len(meetings) == 0:
        return

    meetings.sort(key=lambda x: x.time_started, reverse=True)
    newest_time = meetings[0].time_started

    for meeting in meetings:
        if meeting.time_started >= newest_time:
            newest_meetings.append(meeting)
        else:
            break

    if (current_meeting is None or newest_meetings[0].time_started > current_meeting.time_started) and (
            current_meeting is None or newest_meetings[0].m_id != current_meeting.m_id) and newest_meetings[
        0].m_id not in already_joined_ids:
        return newest_meetings[0]

    return


def join_meeting(meeting):
    global hangup_thread, current_meeting, already_joined_ids, active_correlation_id

    hangup()

    if meeting.calendar_meeting:
        switch_to_calendar_tab()
        join_btn = wait_until_found(f"div[id='{meeting.m_id}'] > div > button", 5)

    else:
        browser.execute_script(f'window.location = "{conversation_link}a?threadId={meeting.channel_id}&ctx=channel";')
        switch_to_teams_tab()

        join_btn = wait_until_found(f"div[id='{meeting.m_id}'] > calling-join-button > button", 5)

    if join_btn is None:
        return

    browser.execute_script("arguments[0].click()", join_btn)

    join_now_btn = wait_until_found("button[data-tid='prejoin-join-button']", 30)
    if join_now_btn is None:
        return

    uuid = re.search(uuid_regex, join_now_btn.get_attribute("track-data"))
    if uuid is not None:
        active_correlation_id = uuid.group(0)
    else:
        active_correlation_id = ""
    # turn camera off
    video_btn = browser.find_element_by_css_selector("toggle-button[data-tid='toggle-video']>div>button")
    video_is_on = video_btn.get_attribute("aria-pressed")
    if video_is_on == "true":
        video_btn.click()
        print("Video off")

    # turn mic off
    audio_btn = browser.find_element_by_css_selector("toggle-button[data-tid='toggle-mute']>div>button")
    audio_is_on = audio_btn.get_attribute("aria-pressed")
    if audio_is_on == "true":
        audio_btn.click()
        print("Audio off")

    if 'random_delay' in config and config['random_delay']:
        delay = random.randrange(10, 31, 1)
        print(f"Wating for {delay}s")
        time.sleep(delay)

    # find again to avoid stale element exception
    join_now_btn = wait_until_found("button[data-tid='prejoin-join-button']", 5)
    if join_now_btn is None:
        return
    join_now_btn.click()

    current_meeting = meeting
    already_joined_ids.append(meeting.m_id)

    print(f"Joined meeting: {meeting.title}")

    if mode != 3:
        switch_to_teams_tab()
    else:
        switch_to_calendar_tab()

    if 'auto_leave_after_min' in config and config['auto_leave_after_min'] > 0:
        hangup_thread = Timer(config['auto_leave_after_min'] * 60, hangup)
        hangup_thread.start()


def get_meeting_members():
    meeting_elems = browser.find_elements_by_css_selector(".one-call")
    for meeting_elem in meeting_elems:
        try:
            meeting_elem.click()
            break
        except:
            continue

    time.sleep(2)
    browser.execute_script("document.getElementById('roster-button').click()")

    time.sleep(2)
    participants_elem = browser.find_element_by_css_selector("calling-roster-section[section-key='participantsInCall'] .roster-list-title")
    attendees_elem = browser.find_element_by_css_selector("calling-roster-section[section-key='attendeesInMeeting'] .roster-list-title")

    if participants_elem is not None:
        participants = [int(s) for s in participants_elem.get_attribute("aria-label").split() if s.isdigit()]
    else:
        participants = 0

    if attendees_elem is not None:
        attendees = [int(s) for s in attendees_elem.get_attribute("aria-label").split() if s.isdigit()]
    else:
        attendees = 0

    if mode != 3:
        switch_to_teams_tab()
    else:
        switch_to_calendar_tab()

    return sum(participants + attendees)


def hangup():
    global current_meeting, active_correlation_id
    if current_meeting is None:
        return

    try:
        hangup_btn = browser.find_element_by_css_selector("button[data-tid='call-hangup']")
        hangup_btn.click()

        print(f"Left Meeting: {current_meeting.title}")

        current_meeting = None

        if hangup_thread:
            hangup_thread.cancel()

        return True
    except exceptions.NoSuchElementException:
        return False


def main():
    global config, meetings, mode, conversation_link

    mode = 1
    if "meeting_mode" in config and 0 < config["meeting_mode"] < 4:
        mode = config["meeting_mode"]

    init_browser()

    browser.get("https://teams.microsoft.com")

    if config['email'] != "" and config['password'] != "":
        login_email = wait_until_found("input[type='email']", 30)
        if login_email is not None:
            login_email.send_keys(config['email'])

        # find the element again to avoid StaleElementReferenceException
        login_email = wait_until_found("input[type='email']", 5)
        if login_email is not None:
            login_email.send_keys(Keys.ENTER)

        login_pwd = wait_until_found("input[type='password']", 10)
        if login_pwd is not None:
            login_pwd.send_keys(config['password'])

        # find the element again to avoid StaleElementReferenceException
        login_pwd = wait_until_found("input[type='password']", 5)
        if login_pwd is not None:
            login_pwd.send_keys(Keys.ENTER)

        keep_logged_in = wait_until_found("input[id='idBtn_Back']", 5)
        if keep_logged_in is not None:
            keep_logged_in.click()
        else:
            print("Login Unsuccessful, recheck entries in config.json")

        use_web_instead = wait_until_found(".use-app-lnk", 5, print_error=False)
        if use_web_instead is not None:
            use_web_instead.click()

    # if additional organisations are setup in the config file
    if 'organisation_num' in config and config['organisation_num'] > 1:
        change_organisation(config['organisation_num'])

    print("Waiting for correct page...", end='')
    if wait_until_found("#teams-app-bar", 60 * 5) is None:
        exit(1)

    print("\rFound page, do not click anything on the webpage from now on.")
    # wait a bit so the meetings are initialized
    time.sleep(5)

    if mode != 2:
        prepare_page(include_calendar=True)
    else:
        prepare_page(include_calendar=False)

    if mode != 3:
        switch_to_teams_tab()

        url = browser.current_url
        url = url[:url.find("conversations/") + 14]
        conversation_link = url

        teams = get_all_teams()

        if len(teams) == 0:
            print("Not Teams found, is MS Teams in list mode? (switch to mode 3 if you only want calendar meetings)")
            exit(1)

        print()
        for team in teams:
            print(team)

    check_interval = 10
    if "check_interval" in config and config['check_interval'] > 1:
        check_interval = config['check_interval']

    interval_count = 0
    while 1:
        timestamp = datetime.now()
        print(f"\n[{timestamp:%H:%M:%S}] Looking for new meetings")

        if mode != 3:
            switch_to_teams_tab()
            teams = get_all_teams()

            if len(teams) == 0:
                print("Nothing found, is Teams in list mode?")
                exit(1)
            else:
                get_meetings(teams)

        if mode != 2:
            switch_to_calendar_tab()
            get_calendar_meetings()

        if len(meetings) > 0:
            print("Found meetings: ")
            for meeting in meetings:
                print(meeting)

            meeting_to_join = decide_meeting()
            if meeting_to_join is not None:
                join_meeting(meeting_to_join)

        meetings = []

        if "leave_if_last" in config and config['leave_if_last'] and interval_count % 5 == 0 and interval_count > 0:
            if current_meeting is not None:
                members = get_meeting_members()

                if 0 < members <= 2:
                    print("Last attendee in meeting")
                    hangup()
                    interval_count = 0

        interval_count += 1

        time.sleep(check_interval)


if __name__ == "__main__":
    load_config()

    if 'run_at_time' in config and config['run_at_time'] != "":
        now = datetime.now()
        run_at = datetime.strptime(config['run_at_time'], "%H:%M").replace(year=now.year, month=now.month, day=now.day)

        if run_at.time() < now.time():
            run_at = datetime.strptime(config['run_at_time'], "%H:%M").replace(year=now.year, month=now.month,
                                                                               day=now.day + 1)

        start_delay = (run_at - now).total_seconds()

        print(f"Waiting until {run_at} ({int(start_delay)}s)")
        time.sleep(start_delay)

    try:
        main()
    finally:
        if browser is not None:
            browser.quit()

        if hangup_thread is not None:
            hangup_thread.cancel()
