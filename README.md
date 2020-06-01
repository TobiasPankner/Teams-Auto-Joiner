# Teams-Auto-Joiner
Python script to automatically join Microsoft Teams meetings.
Automatically turns off your microphone and camera before joining. Automatic login and blacklist can be set in the config file.

Always joins the newest meeting and doesn't leave it unless there is a newer one or the user gets kicked. Automatically leaving after x minutes can be configured in the config file.

![Demo](https://imgur.com/VQOJl8w.gif)
## Prerequisites

 - Python3 ([Download](https://www.python.org/downloads/))

## Run the script

 1. Rename the [config.json.example](config.json.example) file to "config.json"
 2. Edit the "config.json" file to fit your preferences (optional)
 3. Install dependencies: `pip install -r requirements.txt`
 4. Run [auto_joiner.py](auto_joiner.py): `python auto_joiner.py`
 5. After starting, teams might be in Grid view, if this is the case change the view to list
<img src="https://i.imgur.com/GODoJYf.png?2" width="300" height="245" />
