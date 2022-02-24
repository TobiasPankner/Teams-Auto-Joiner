from dataclasses import dataclass
@dataclass
class Meeting:
    name:str
    uri:str
    members_list:list = None
    
    def get_members():
        pass