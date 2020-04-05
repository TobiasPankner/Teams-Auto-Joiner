# Teams-Auto-Joiner
Python script to automatically join Microsoft Teams meetings.
Automatically turns off your microphone and camera before joining. Automatic login and blacklist can be set in the config file.

![Demo](https://imgur.com/VQOJl8w.gif)
## Prerequisites

 - Python3 ([Download](https://www.python.org/downloads/))
 - Chrome WebDriver for your version of Google Chrome ([Download](https://chromedriver.chromium.org/downloads))
 - Include the WebDriver location in your PATH environment variable ([Tutorial](https://zwbetz.com/download-chromedriver-binary-and-add-to-your-path-for-automated-functional-testing/))

## Run the script

 1. Rename the [config.json.example](config.json.example) file to "config.json"
 2. Edit the "config.json" file to fit your preferences (optional)
 3. Install dependencies: `pip install -r requirements.txt`
 4. Run [main.py](/src/main.py): `python src/main.py`
