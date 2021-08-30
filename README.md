# Teams-Auto-Joiner
[![GitHub stars](https://img.shields.io/github/stars/TobiasPankner/Teams-Auto-Joiner.svg?style=social&label=Star)](https://GitHub.com/TobiasPankner/Teams-Auto-Joiner/stargazers/)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=3TU2XDBK2JFU4&source=url)

- [Prerequisites](#prerequisites)
- [Configuration options](#configuration-options)
- [Run the script](#run-the-script)

Python script to automatically join Microsoft Teams meetings.
Automatically turns off your microphone and camera before joining. Automatic login and blacklist can be set in the config file.

Always joins the newest meeting and leaves either after a specified time, if you are the last person in the meeting or only if a new one is available (see [Configuration options](#configuration-options) for more information).
I also made a short tutorial video on how to setup the bot: https://youtu.be/YgkSOqfIjf4

![Demo](https://imgur.com/VQOJl8w.gif)

## Prerequisites  
  
 - Python3 ([Download](https://www.python.org/downloads/))  
   
## Configuration options  
  
- **email/password:**  
The email/password of your Microsoft account. In case you don't want to store your credentials on disk, you can leave any of them empty and you will be prompted to enter them. If you leave them empty in the prompt too, you will have to enter them in the browser.   

- **run_at_time:**  
Time to start the script at. Input is a string of the hour and minute in 24h format, if you want it to start immediately leave this empty. 
If a time before the current time is given, the next day is used. Also make sure that you entered your email and password.
For example, if you want the script to start searching meetings at 6 in the morning on the next day, you would input `06:00` in the config.

- **meeting_mode:**
Change which meetings should be joined. Modes 1, 2 and 3 are available.  
`1` Both channel and calendar meetings  
`2` Only channel meetings  
`3` Only calendar meetings  

- **organisation_num:**
If your Teams account is in multiple organisations, as seen in the example below, change the organisation_num to the number of the list item (counting starts from 0), 
set to -1 to never change organisation.  

    <img width="30%" src="https://imgur.com/4NTVrqj.png">

- **random_delay:**
Adds a random delay (random integer between the two parameters, in seconds) before joining a meeting. Can be useful so the bot seems more "human like" or to avoid being one of the first few people to join a meeting. For a fixed delay, set both parameters to the same Integer.  
eg: [30,30] will add a fixed delay of 30s before joining the meet.

- **check_interval:**
The amount of seconds to wait before checking for meetings again. Only integer numbers greater than 1 are allowed.

- **join_message:**
A chat message sent when a meeting is joined.

- **auto_leave_after_min:**
If set to a value greater than zero, the bot leaves every meeting after the specified time (in minutes). Useful if you know the length of your meeting, if this is left a the default the bot will stay in the meeting until a new one is available.

- **leave_if_last:**
If true, leaves the meeting if you are the last person in it.

- **leave_threshold_number:**
Sets the threshold for people to leave the meeting before the bot leaves the meeting.  
For example:  
Peak members of meeting: 20  
Current members of meeting: 5  
Leave threshold set to 15  
Because 15 people have left the meeting, the bot leaves.  
(Must enable leave_if_last for this to work) 

- **leave_threshold_percentage:**
Sets the threshold percentage of people still in the meeting before auto leaving. The same as 
leave_threshold_number but with percentage of the current members to the peak.  
(Must enable leave_if_last for this to work)

- **pause_search:**
If true, doesn't search for new meetings while there is one active. Keep in mind to set auto_leave_after_min or leave_if_last,
otherwise the bot will not search for meetings again.

- **headless:**
If true, runs Chrome in headless mode (does not open GUI window and runs in background).

- **mute_audio:**
If true, mutes all sound output of the browser. This doesn't effect your microphone.

- **chrome_type:**
Valid options: `google-chrome`, `chromium`, `msedge`. By default, google chrome is used, but the script can also be used with Chromium or Microsoft Edge.

- **blacklist:**
A list of Teams and their channels to ignore. Meetings ocurring in these channels will not be joined.
If you have a Team called "Test1" and, within that, two channels called "General" and "Channel1" and you don't want to join meetings in the "General" Channel:  
    ```json
    "blacklist": [
      {
        "team_name": "Test1",
        "channel_names": [
          "General"
        ]
      }
    ]
    ```
   If you want to blacklist all the channels in a team, leave the square brackets empty: `"channel_names": []`.

- **blacklist_meeting_re:**
If calendar meeting title matches a regular expression, it goes to blacklist.
Leave empty to attend to all calendar meetings.  

- **discord_webhook_url:**
For getting Discord notifications you have to specify a [Discord webhook url](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).  

    ```json 
    "discord_webhook_url" : "your_discord_channel_webHook_url" 
    ```

## Run the script

 1. Rename the [config.json.example](config.json.example) file to "config.json"
 2. Edit the "config.json" file to fit your preferences (optional)
 3. Install dependencies:   ```pip install -r requirements.txt```
 4. Run [auto_joiner.py](auto_joiner.py): `python auto_joiner.py`
 5. After starting, teams might be in Grid view, if this is the case change the view to list [(How to do)](https://support.microsoft.com/en-us/office/view-and-organize-your-teams-b9dd0d8c-243a-43a4-9501-ec8017fec32e)
<img src="https://i.imgur.com/GODoJYf.png?2" width="300" height="245" />
