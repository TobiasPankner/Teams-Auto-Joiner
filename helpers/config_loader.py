import json

def load_config():
    global config
    with open('config.json', encoding='utf-8') as json_data_file:
        config = json.load(json_data_file)
    return config