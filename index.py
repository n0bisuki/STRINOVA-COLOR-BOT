"""
STRINOVA - Advanced Game Enhancement System
============================================
DISCLAIMER: This project is for EDUCATIONAL PURPOSES ONLY.
This software is NOT intended to cause any damage to games, systems, or software.
Misuse of this software may violate game Terms of Service and result in account bans.
The author assumes NO responsibility for any misuse of this code.

For support and questions, join our Discord community:
Discord: https://discord.gg/j7Faupsf4h
"""

import os 
import sys
import json
import psutil
import time
import ctypes
import colorama
import threading
import win32api
from util.setting import *
from util.display import *
from util.settings_manager import SettingsManager
from NeoRant import NeoRant

if __name__ == '__main__':   
    colorama.init()
    # Initialize settings manager with INI format 
    
    settings_manager = SettingsManager() 
    settings = settings_manager.export_to_dict() 
    app = NeoRant(settings,settings_manager)
