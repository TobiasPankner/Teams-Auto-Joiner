import json
import time
from datetime import datetime

from dataclasses import dataclass
from helpers.identity_faker import *
from helpers.browser_initier import *
from helpers.config_loader import *
from helpers.identity_faker import *
from helpers.web_selector_fonder import *

@dataclass
class Bot_teams:
    guid: str
    name: str
    address: str
    city: str
    phone: str
    age: int
    email: str
    browser: str
    
    def connect(self):
        def turn_camera_off(self):
            # turn camera off
            video_btn = self.browser.find_element_by_css_selector("toggle-button[data-tid='toggle-video']>div>button")
            video_is_on = video_btn.get_attribute("aria-pressed")
            if video_is_on == "true":
                video_btn.click()
                print("Video disabled")
                return True
            else :
                return False
        
        def turn_mic_off(self) :
            # turn mic off
            audio_btn = self.browser.find_element_by_css_selector("toggle-button[data-tid='toggle-mute']>div>button")
            audio_is_on = audio_btn.get_attribute("aria-pressed")
            if audio_is_on == "true":
                audio_btn.click()
                print("Microphone off")
                return True
            else : 
                return False
        
        #connect in web client
        self.browser.find_element_by_css_selector("button[data-tid='joinOnWeb']").click()
        
        #Waiting init of meeting
        time.sleep(10)
        turn_camera_off(self)
        turn_mic_off(self)
        
        # register the user name
        username = wait_until_found(self.browser, "input[name='username']", 45)
        if username is not None:
            username.send_keys(self.name)
        else : 
            return False
        
        #Use join btn to enter in meeting
        join_now_btn = wait_until_found(self.browser, "button[data-tid='prejoin-join-button']", 5)
        if join_now_btn is not None:
            join_now_btn.click()
            print('Meeting joined succefuly')
        else : 
            return False
    
    def disconnect(self):
        hangup_thread: Timer = None
        def hang_up(self):
            try:
                self.browser.execute_script("document.getElementById('hangup-button').click()")
                if hangup_thread:
                    hangup_thread.cancel()
                return True
            except exceptions.NoSuchElementException:
                return False
        hang_up(self)
        return True
            
    def send_message():
        pass
    
    def answer_form():
        pass

@dataclass
class Bot_manager:
    name:str
    bots_list:list = None

    def generate_bots(self,bots_quantity,config):
        self.bots_list = list()
        for i in range(bots_quantity) :
            bot_identity = getFakeName()
            self.bots_list.append(
                Bot_teams(
                    bot_identity.guid,
                    bot_identity.name,
                    bot_identity.address,
                    bot_identity.city,
                    bot_identity.phone,
                    bot_identity.age,
                    bot_identity.email,
                    init_browser(config)))

    def connect_bots(self,config):
        for bot in self.bots_list :
            bot.browser.get(config.get("conversation_url"))
            bot.connect()
        return True
    
    def disconnect_bots(self):
        for bot in self.bots_list :
            bot.disconnect()
        return True
    
    
