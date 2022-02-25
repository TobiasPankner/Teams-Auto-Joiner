from dataclasses import dataclass
from classes.bot import Bot_teams
from selenium.common import exceptions
import time

@dataclass
class Meeting:
    name: str
    uri: str
    master_bot: Bot_teams
    members_list: list = None

    def start(self):
        self.master_bot.connect(self.uri)

    def get_members(self):
        # open the meeting member side page
        try:
            self.master_bot.browser.execute_script("document.getElementById('roster-button').click()")
        except exceptions.JavascriptException:
            print("Failed to open meeting member page")
            return None

        self.members_list = self.master_bot.browser.execute_script("""
            var result = []; 
            var all = document.querySelectorAll("li[data-tid^='participantsInCall-']"); 
            for (var i=0, max=all.length; i < max; i++) { 
                result.push(all[i].getAttribute('data-tid').replace('participantsInCall-','')); 
            } 
            return result;
        """)

        time.sleep(2)

        # close the meeting member side page, this only makes a difference if pause_search is true
        try:
            self.master_bot.browser.execute_script("document.getElementById('roster-button').click()")
        except exceptions.JavascriptException:
            # if the roster button doesn't exist click the three dots button before
            try:
                self.master_bot.browser.execute_script("document.getElementById('callingButtons-showMoreBtn').click()")
                time.sleep(1)
                self.master_bot.browser.execute_script("document.getElementById('roster-button').click()")
            except exceptions.JavascriptException:
                print("Failed to close meeting member page, this might result in an error on next search")