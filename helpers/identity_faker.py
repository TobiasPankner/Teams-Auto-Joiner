from fng_api import *

def getFakeName():
    identity = getIdentity(country=["fr"],nameset=["fr"],minage="18",maxage="35",gender="85")
    return identity