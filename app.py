import time
from fng_api import *
from classes.bot import *
from classes.meeting import *
from helpers.browser_initier import *
from helpers.config_loader import *
from helpers.identity_faker import *

config = load_config()

manager = Bot_manager('manager_bots_teams')
meeting = Meeting('conférence',config.get("conversation_url"))

manager.generate_bots(int(input('Nombre de bots : ')), config)
manager.connect_bots(config)
time.sleep(60)
manager.disconnect_bots()
    



