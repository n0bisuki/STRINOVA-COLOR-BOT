"""
STRINOVA - Configuration Utilities
===================================
DISCLAIMER: This project is for EDUCATIONAL PURPOSES ONLY.
This software is NOT intended to cause any damage to games, systems, or software.
Misuse of this software may violate game Terms of Service and result in account bans.
The author assumes NO responsibility for any misuse of this code.

For support and questions, join our Discord community:
Discord: https://discord.gg/j7Faupsf4h
"""

import ctypes
import os   
import json 
import time  
import requests
import colorama
from util.display import *
from util.settings_manager import SettingsManager
from urllib.parse import urlparse


# JSON functions removed - use SettingsManager instead
from .settings_manager import SettingsManager

def get_settings_manager(config_file="settings.ini"):
    """Get a settings manager instance"""
    return SettingsManager(config_file)


DISCORD = "https://discord.gg/j7Faupsf4h"
 
 

def read_args_json_for(game_id: str) -> dict: 
    ref_path = os.path.abspath(os.path.join(os.getcwd(), "..", "data", f"launch_args_{game_id}.json")) 
    with open(ref_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_color_bounds(color):
    if color == "strinova_blackish_purple":return [141, 114, 96],[156, 255, 255]
    elif color == "strinova_red":return [167, 102, 76],[179, 255, 255]
    elif color == "strinova_purple":return [140, 110, 140], [160, 255, 255]
    else:return [140, 110, 140], [160, 255, 255]

 