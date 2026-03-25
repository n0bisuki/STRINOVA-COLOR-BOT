"""
STRINOVA - Core Application Logic
==================================
DISCLAIMER: This project is for EDUCATIONAL PURPOSES ONLY.
This software is NOT intended to cause any damage to games, systems, or software.
Misuse of this software may violate game Terms of Service and result in account bans.
The author assumes NO responsibility for any misuse of this code.

For support and questions, join our Discord community:
Discord: https://discord.gg/j7Faupsf4h
"""

import os
import cv2
import sys
import time
import math
import json
import psutil
import random 
import string
import win32api
import winsound
import threading
import numpy as np
from capture import Capture
from screen_capture import ScreenCapture
from termcolor import colored
from mouse import ArduinoMouse
from ImGuI.overlay import ImGuiOverlay 
from util.setting import get_color_bounds
from fov_window import show_detection_window, toggle_window



class NeoRant:
    def __init__(self, settings,settings_manager): 
        # One time calls
        self.last_time = time.time()
        self._key_prev = {}
        self.launcher_pid  = 0
        self.recoil_offset = 0
        self.TRIGGER_TOGGLE = False
        self.TOGGLED_CHEATE = True 
        self.WINDOW_TOGGLE = 0x71
        self.move_x, self.move_y = (0, 0)
        self.previous_x, self.previous_y = (0, 0) 
        self.settings_manager = settings_manager

        #  finally get all settings AIM
        self.XFOV = int(settings.get("XFOV",113))
        self.YFOV = int(settings.get("YFOV",84)) 
        self.SMOOTHNESS = int(settings.get("SMOOTHNESS",1)) 
        self.HEAD_OFFSET = float(settings.get("HEAD_OFFSET", 0))
        self.AIM_SMOOTHING_FACTOR = float(settings.get("AIM_SMOOTHING_FACTOR",0.1))

        # finally get all settings SENSITIVITY
        self.MOVESPEED = float(settings.get("MOVESPEED", 0.5))
        self.INGAME_SENSITIVITY = float(settings.get("INGAME_SENSITIVITY",3)) 
        self.Y_SPEED_MULTIPLIER = float(settings.get("Y_SPEED_MULTIPLIER",1.0))

        # Recoil configuration parameters  
        self.RECOIL_MODE = settings.get("RECOIL_MODE",'offset')
        self.RECOIL_X = int(settings.get("RECOIL_X",0))
        self.RECOIL_Y = int(settings.get("RECOIL_Y",0))
        self.MAX_OFFSET = int(settings.get("MAX_OFFSET",100))
        self.RECOIL_RECOVER = int(settings.get("RECOIL_RECOVER",0)) 

        # finally get all settings CONTROLS
        self.AIM_ASSIST_KEY = settings.get("AIM_ASSIST_KEY",'0x01')
        self.FLICK_KEY = settings.get("FLICK_KEY",'0x04')


        # finally get all settings TOGGLES
        fov_toggle_val = settings.get("FOV_TOGGLE", "True")
        self.FOV_TOGGLE = fov_toggle_val if isinstance(fov_toggle_val, bool) else fov_toggle_val.lower() == 'true'
        fps_toggle_val = settings.get("FPS_TOGGLE", "True")  
        self.FPS_TOGGLE = fps_toggle_val if isinstance(fps_toggle_val, bool) else fps_toggle_val.lower() == 'true'
        self.CHEAT_TOGGLE_KEY = settings.get("CHEAT_TOGGLE_KEY",'0x74')
        self.IMGUI_TOGGLE_KEY = settings.get("IMGUI_TOGGLE_KEY",'0x75')
        self.TRIGGER_KEY = settings.get("TRIGGER_KEY",'0x43')

        # finally get all settings COLORS
        self.ANIME_COLOR=settings.get("ANIME_COLOR","strinova_purple")
        box_enabled_val = settings.get("BOX_ENABLED", "True")
        self.BOX_ENABLED = box_enabled_val if isinstance(box_enabled_val, bool) else box_enabled_val.lower() == 'true'
        self.BOX_COLOR=settings.get("BOX_COLOR","1.0, 1.0, 0.0, 1.0")
        head_enabled_val = settings.get("HEAD_ENABLED", "True")
        self.HEAD_ENABLED = head_enabled_val if isinstance(head_enabled_val, bool) else head_enabled_val.lower() == 'true'
        self.HEAD_COLOR=settings.get("HEAD_COLOR","1.0, 1.0, 0.0, 1.0")
        line_enabled_val = settings.get("LINE_ENABLED", "True")
        self.LINE_ENABLED = line_enabled_val if isinstance(line_enabled_val, bool) else line_enabled_val.lower() == 'true'
        self.LINE_COLOR=settings.get("LINE_COLOR","0.0, 1.0, 0.0, 1.0")


        
        # Read MOVESPEED from settings; fallback to computed default
        self.refresh_init()

        self.monitor_width = win32api.GetSystemMetrics(0)
        self.monitor_height = win32api.GetSystemMetrics(1)
        self.CENTER_X, self.CENTER_Y = self.monitor_width // 2, self.monitor_height // 2
        self.x = self.CENTER_X - self.XFOV // 2
        self.y = self.CENTER_Y - self.YFOV // 2
 
        
        # Track time for delta calculations
        self.screen_capture = ScreenCapture(self, False)
        self.arduinomouse = ArduinoMouse(self)
        
        # Track previous key states for edge detection (press once)
        self.overlay = ImGuiOverlay(self)
        self.overlay.init_window()
        self.overlay.Hide_from_taskbar()
        threading.Thread(target=self.listener_keybind, daemon=True).start() 
        # threading.Thread(target=self.random_app_name, daemon=True).start() 
        threading.Thread(target=self.listener, daemon=True).start() 
        self.overlay.render_loop() 

    
    def refresh_init(self):
        self.MOVESPEED = float(self.MOVESPEED* (self.INGAME_SENSITIVITY / 1.0)) 
        self.FLICKSPEED = 1.07437623 * (self.INGAME_SENSITIVITY ** -0.9936827126)


    def random_app_name(self):
        while True:
            app_names = [
                "Discord","Visual Studio Code","Chrome","PyCharm","Firefox","Sublime Text","Notepad++","Atom",
                "Microsoft Word","Excel","PowerPoint","Photoshop","Illustrator","Premiere Pro","Audacity","Blender",
                "Unity","Maya","Eclipse","Android Studio","Spotify","Zoom","Slack","WhatsApp",
                "Telegram","Microsoft Teams","Trello","GitHub","GitLab","Jupyter Notebook","Google Docs","Google Sheets",
                "Google Slides","Adobe Acrobat","Adobe InDesign","Adobe After Effects","Adobe Lightroom","Audacity","GIMP","Krita",
                "VLC Media Player","iTunes","Microsoft Edge","Safari","Opera","Notion","Figma","Microsoft Outlook",
            ]
            random_app = random.choice(app_names)
            random_text = ''.join(random.choices(string.ascii_letters + string.digits, k=10))  # 10 random characters 
            os.system("title " + f"{random_app} {random_text}") 
            time.sleep(2)

    def play(self, s):
        winsound.Beep(1000 if s == "cheatOn" else 500, 200)
  
    def listener(self):
        while True: 
            if self.TOGGLED_CHEATE and self.TRIGGER_TOGGLE:
                self.process("trigger")   
            if self.TOGGLED_CHEATE and ((win32api.GetAsyncKeyState(int(self.AIM_ASSIST_KEY, 16)) & 0x8000) != 0 ):
                self.process("move") 
            elif self.TOGGLED_CHEATE and ((win32api.GetAsyncKeyState(int(self.FLICK_KEY, 16)) & 0x8000) != 0): 
                self.process("flick") 
            time.sleep(0.003)  

            
            
    def listener_keybind(self):
        while True:
            # Prepare key bindings once
            bindings = [
                (int(self.CHEAT_TOGGLE_KEY, 16), self.Cheat_Toggled),  
                (int(self.TRIGGER_KEY, 16), self.Trigger_Toggled),    
            ]
            for vk, action in bindings:
                pressed = (win32api.GetAsyncKeyState(vk) & 0x8000) != 0
                prev = self._key_prev.get(vk, False) 
                if pressed and not prev and action is not None: 
                    threading.Thread(target=action, daemon=True).start()
                self._key_prev[vk] = pressed
            time.sleep(0.005)
 
    def Cheat_Toggled(self):
        self.TOGGLED_CHEATE = not self.TOGGLED_CHEATE
        self.play("cheatOn" if self.TOGGLED_CHEATE else "cheatOff") 

    def Trigger_Toggled(self):
        self.TRIGGER_TOGGLE = not self.TRIGGER_TOGGLE
        self.play("play") 



    def calculate_aim(self, x, y):
        if x is not None and y is not None:
            # Calculate x and y speed (normalize first, then apply sensitivity)
            raw_x = x * self.INGAME_SENSITIVITY
            raw_y = y * self.INGAME_SENSITIVITY * self.Y_SPEED_MULTIPLIER 
            # Apply smoothing with the previous x and y value
            smoothed_x = (1 - self.AIM_SMOOTHING_FACTOR) * self.AIM_SMOOTHING_FACTOR * raw_x 
            smoothed_y = (1 - self.AIM_SMOOTHING_FACTOR) * self.AIM_SMOOTHING_FACTOR * raw_y 
            
            return (smoothed_x, smoothed_y)
        else: 
            return (0, 0)

    def apply_recoil(self, delta_time):
        if delta_time != 0:
            # Mode move just applies configured movement to the move values
            if self.RECOIL_MODE == 'move' and win32api.GetAsyncKeyState(0x01) < 0:
                self.move_x += self.RECOIL_X * delta_time
                self.move_y += self.RECOIL_Y * delta_time
            # Mode offset moves the camera upward, so it aims below target
            elif self.RECOIL_MODE == 'offset':
                # Add recoil_y to the offset when mouse1 is down
                if win32api.GetAsyncKeyState(0x01) < 0:
                    if self.recoil_offset < self.MAX_OFFSET:
                        self.recoil_offset += self.RECOIL_Y * delta_time
                        if self.recoil_offset > self.MAX_OFFSET:
                            self.recoil_offset = self.MAX_OFFSET
                # Start resetting the offset bit by bit if mouse1 is not down
                else:
                    if self.recoil_offset > 0:
                        self.recoil_offset -= self.RECOIL_RECOVER * delta_time
                        if self.recoil_offset < 0:
                            self.recoil_offset = 0
        else:
            # Reset recoil offset if recoil is off
            self.recoil_offset = 0 

    def process(self, action): 
        # Calculate delta time for recoil
        current_time = time.time()
        delta_time = current_time - self.last_time
        self.last_time = current_time 
        # Handle flick action (works with or without target) 
        if action == "trigger" :
            self.trigger()
        if action == "flick":
            self.flick()
        elif action == "move": 
            self.move(delta_time)

    def trigger(self):
        self.arduinomouse.click() 

    def flick(self):
        # Use head position if available, otherwise fallback to target
        # if self.screen_capture.head_position is not None:
        #     x, y = self.screen_capture.head_position
        if self.screen_capture.target is not None:
            x, y = self.screen_capture.target
        else:
            return  # No target available
            
        x, y = self.calculate_aim(x, y)  
        self.arduinomouse.move(x, y)
        
        if self.screen_capture.trigger:
            self.arduinomouse.click()


    def move(self, delta_time):
        if self.screen_capture.target is None:
            return
        x, y = self.screen_capture.target 
        x, y = self.calculate_aim(x, y) 
        self.apply_recoil(delta_time) 
        self.arduinomouse.move(x*self.MOVESPEED, y*self.MOVESPEED) 
        self.move_x, self.move_y = (0, 0)