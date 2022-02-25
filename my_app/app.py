import time
from fng_api import *
from classes.bot import *
from classes.meeting import *
from helpers.browser_initier import *
from helpers.config_loader import *
from helpers.identity_faker import *

config = load_config()

manager = Bot_manager('manager_bots_teams',Bot_teams('CESI2022','Héloise GUYONNET','72 route de paris','44300 Nantes','0631665912','49 ans','hguyonnet@gmail.com',init_browser(config)))

meeting = Meeting('conférence',config.get("conversation_url"), manager.bot_master)

meeting.start()
manager.generate_bots(int(input('Nombre de bots : ')), config)
manager.connect_bots(meeting.uri)
meeting.get_members()

print(' Liste des membres ', meeting.members_list)

time.sleep(60)

manager.disconnect_bots()