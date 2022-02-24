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
from fng_api import *

browser: webdriver.Chrome = None
total_members = None
config = None
meetings = []

active_correlation_id = ""
hangup_thread: Timer = None
conversation_link = "https://teams.microsoft.com/_#/conversations/a"
mode = 3
uuid_regex = r"\b[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}\b"
#Chargement du JSON de config en variable global
def load_config():
    global config
    with open('config.json', encoding='utf-8') as json_data_file:
        config = json.load(json_data_file)

#Méthode qui initialise le navigateur grâce au information du JSON de config
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
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--incognito')
    chrome_options.add_argument('--disable-notifications')

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
    chrome_options.add_argument('--no-sandbox')

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


def get_meeting_members():

    # open the meeting member side page
    try:
        browser.execute_script("document.getElementById('roster-button').click()")
    except exceptions.JavascriptException:
        print("Failed to open meeting member page")
        return None

    members = len(browser.find_elements_by_css_selector("li[data-tid^='participantsInCall-'"))
    print(members)
    time.sleep(2)

    # close the meeting member side page, this only makes a difference if pause_search is true
    try:
        browser.execute_script("document.getElementById('roster-button').click()")
    except exceptions.JavascriptException:
        # if the roster button doesn't exist click the three dots button before
        try:
            browser.execute_script("document.getElementById('callingButtons-showMoreBtn').click()")
            time.sleep(1)
            browser.execute_script("document.getElementById('roster-button').click()")
        except exceptions.JavascriptException:
            print("Failed to close meeting member page, this might result in an error on next search")

    return members


def hangup():
    try:
        browser.execute_script("document.getElementById('hangup-button').click()")

        if hangup_thread:
            hangup_thread.cancel()

        return True
    except exceptions.NoSuchElementException:
        return False


# Handles logic for leave number threshold and percent threshold. Return True for did hangup, or False for did not.
def handle_leave_threshold(current_meeting_members, total_meeting_members):
    print(f"Current members in meeting: {current_meeting_members}")
    print(f"Total members of the meeting: {total_meeting_members}")
    leave_number = config["leave_threshold_number"]
    leave_percentage = config["leave_threshold_percentage"]

    if leave_number is not None and leave_number != "" and int(leave_number) > 0:
        if (total_meeting_members - current_meeting_members) >= int(leave_number):
            print("Leave threshold (absolute) triggered")
            hangup()
            return True

    if leave_percentage is not None and leave_percentage != "" and 0 < int(leave_percentage) <= 100:
        if (current_meeting_members / total_meeting_members) * 100 < int(leave_percentage):
            print("Leave threshold (percentage) triggered")
            hangup()
            return True

    if 0 < current_meeting_members < 3:
        print("Last attendee in meeting")
        hangup()
        return True

    return False

def getFakeName():
    identity = getIdentity(country=["fr"],nameset=["fr"],minage="18",maxage="35",gender="85")
    return identity.name

def main():
    global config, meetings, mode, conversation_link, total_members, name

    conversation_link = config["conversation_url"]
    init_browser()
    browser.get(conversation_link)

    #connect in web client
    joinOnWeb = browser.find_element_by_css_selector("button[data-tid='joinOnWeb']")
    joinOnWeb.click()

    #Waiting init of meeting
    time.sleep(15)

    # turn camera off
    video_btn = browser.find_element_by_css_selector("toggle-button[data-tid='toggle-video']>div>button")
    video_is_on = video_btn.get_attribute("aria-pressed")
    if video_is_on == "true":
        video_btn.click()
        print("Video disabled")

    # turn mic off
    audio_btn = browser.find_element_by_css_selector("toggle-button[data-tid='toggle-mute']>div>button")
    audio_is_on = audio_btn.get_attribute("aria-pressed")
    if audio_is_on == "true":
        audio_btn.click()
        print("Microphone off")

    #Generate username
    name = getFakeName()
    username = wait_until_found("input[name='username']", 45)
    if username is not None:
        username.send_keys(name)

    # find the element again to avoid StaleElementReferenceException
    '''username = wait_until_found("input[name='username']", 5)
    if username is not None:
        username.send_keys(Keys.ENTER)
    '''

    #Use join btn to enter in meeting
    join_now_btn = wait_until_found("button[data-tid='prejoin-join-button']", 5)
    if join_now_btn is None:
        return
    join_now_btn.click()
    print('Meeting joined succefuly')

    if "join_message" in config and config["join_message"] != "":
        time.sleep(10)
        try:
            browser.execute_script("document.getElementById('chat-button').click()")
            text_input = wait_until_found('div[role="textbox"] > div', 5)

            js_change_text = """
              var elm = arguments[0], txt = arguments[1];
              elm.innerHTML = txt;
              """

            browser.execute_script(js_change_text, text_input, config["join_message"])

            time.sleep(5)
            send_button = wait_until_found("#send-message-button", 5)
            send_button.click()
            print(f'Sent message {config["join_message"]}')
        except (exceptions.JavascriptException, exceptions.ElementNotInteractableException):
            print("Failed to send join message")
            pass

    check_interval = 5
    if "check_interval" in config and config['check_interval'] > 1:
        check_interval = config['check_interval']

    interval_count = 0
    total_members = 0
    while 1:
        members_count = None
        members_count = get_meeting_members()

        if members_count and members_count > total_members:
            total_members = members_count

        if members_count is not None and total_members is not None:
            if handle_leave_threshold(members_count, total_members):
                total_members = None

        interval_count += 1

        #Fermeture si raccrocher
        if browser.current_url.__contains__("post-calling"):
            break

        time.sleep(check_interval)


if __name__ == "__main__":
    try:
        load_config()
    except Exception as e:
        print("Configuration file missing or in wrong format")
        print(str(e))
        exit(1)

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
