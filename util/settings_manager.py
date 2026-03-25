"""
STRINOVA - Advanced Settings Manager
=====================================
DISCLAIMER: This project is for EDUCATIONAL PURPOSES ONLY.
This software is NOT intended to cause any damage to games, systems, or software.
Misuse of this software may violate game Terms of Service and result in account bans.
The author assumes NO responsibility for any misuse of this code.

For support and questions, join our Discord community:
Discord: https://discord.gg/j7Faupsf4h
"""

import configparser
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

class SettingsManager:
    """Unified settings manager with INI format and CRUD operations"""
    
    def __init__(self, config_file: str = "settings.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        # Preserve option key case (avoid auto-lowercasing like xfov)
        self.config.optionxform = str
        self.default_settings = {
            # Core gameplay parameters split into logical sections
            'AIM': {
                'XFOV': '113',                 # int
                'YFOV': '84',                  # int
                'SMOOTHNESS': '1',             # int
                'HEAD_OFFSET': '0.5',          # float
                'AIM_SMOOTHING_FACTOR': '0.1'  # float
            },
            'SENSITIVITY': {
                'MOVESPEED': '0.5',            # float (auto-updated from INGAME_SENSITIVITY)
                'INGAME_SENSITIVITY': '3',     # int
                'Y_SPEED_MULTIPLIER': '1.0',   # float
            },
            'RECOIL': {
                'RECOIL_MODE': 'offset',       # 'offset' or 'move'
                'RECOIL_X': '0',               # int
                'RECOIL_Y': '0',               # int
                'MAX_OFFSET': '100',           # int
                'RECOIL_RECOVER': '0',         # int
            },
            # Action keys
            'CONTROLS': {
                'AIM_ASSIST_KEY': '0x01',
                'FLICK_KEY': '0x04'
            },
            # Feature toggles and VK toggle keys
            'TOGGLES': {
                'FOV_TOGGLE': 'False',          # on/off
                'FPS_TOGGLE': 'False',          # on/off
                'CHEAT_TOGGLE_KEY': '0x74',    # vk key for cheat on/off
                'IMGUI_TOGGLE_KEY': '0x75',    # vk key for UI on/off
                'TRIGGER_KEY': '0x43'         # trigger on/off, 
            },
            # Visuals and colors (RGBA stored as "r, g, b, a")
            'COLORS': {
                'ANIME_COLOR': 'strinova_purple',
                'BOX_ENABLED': 'True',
                'BOX_COLOR': 'red',   # yellow
                'HEAD_ENABLED': 'True',
                'HEAD_COLOR': 'yellow',  # yellow
                'LINE_ENABLED': 'True',
                'LINE_COLOR': 'green'   # green
            }
        }
        self._ensure_config_exists()
    
    def _ensure_config_exists(self) -> None:
        """Create config file if it doesn't exist"""
        if not os.path.exists(self.config_file):
            self.create_default_config()
        else:
            self._load_config()
            self._validate_and_update()
    
    def _load_config(self) -> None:
        """Load configuration from file"""
        try:
            self.config.read(self.config_file, encoding='utf-8')
        except Exception as e:
            print(f"Error loading config: {e}")
            self.create_default_config()
    
    def _validate_and_update(self) -> None:
        """Validate config and add missing sections/keys"""
        updated = False
        
        for section_name, section_data in self.default_settings.items():
            if not self.config.has_section(section_name):
                self.config.add_section(section_name)
                updated = True
            
            for key, default_value in section_data.items():
                if not self.config.has_option(section_name, key):
                    # Migrate any old lowercase keys to proper case
                    lower_key = key.lower()
                    if self.config.has_option(section_name, lower_key):
                        migrated_value = self.config.get(section_name, lower_key)
                        self.config.remove_option(section_name, lower_key)
                        self.config.set(section_name, key, migrated_value)
                        updated = True
                    else:
                        self.config.set(section_name, key, str(default_value))
                        updated = True
        
        # Backward-compat: migrate old [GAME] keys into new sections if present
        if self.config.has_section('GAME'):
            game = dict(self.config.items('GAME'))
            # AIM keys
            for k in ['XFOV', 'YFOV', 'SMOOTHNESS', 'HEAD_OFFSET', 'AIM_SMOOTHING_FACTOR']:
                if k in game and not self.config.has_option('AIM', k):
                    self.config.set('AIM', k, game[k])
                    updated = True
            # SENSITIVITY keys
            for k in ['INGAME_SENSITIVITY', 'MOVESPEED', 'Y_SPEED_MULTIPLIER']:
                if k in game and not self.config.has_option('SENSITIVITY', k):
                    self.config.set('SENSITIVITY', k, game[k])
                    updated = True
            # RECOIL keys
            for k in ['RECOIL_MODE', 'RECOIL_X', 'RECOIL_Y', 'MAX_OFFSET', 'RECOIL_RECOVER']:
                if k in game and not self.config.has_option('RECOIL', k):
                    self.config.set('RECOIL', k, game[k])
                    updated = True

        # Update MOVESPEED based on INGAME_SENSITIVITY if needed (new sections preferred)
        sens_section = 'SENSITIVITY'
        if self.config.has_section(sens_section):
            try:
                ingame_sens = float(self.config.get(sens_section, 'INGAME_SENSITIVITY', fallback='3'))
                calculated_movespeed = round(0.55 * (ingame_sens / 3.0), 3)
                current_movespeed = float(self.config.get(sens_section, 'MOVESPEED', fallback='0.55'))
                if abs(current_movespeed - calculated_movespeed) > 0.001:
                    self.config.set(sens_section, 'MOVESPEED', str(calculated_movespeed))
                    updated = True
            except (ValueError, TypeError):
                pass
        
        if updated:
            self._update_timestamp()
            self._save_config()
    
    def create_default_config(self) -> None:
        """Create default configuration file"""
        self.config.clear()
        
        for section_name, section_data in self.default_settings.items():
            self.config.add_section(section_name)
            for key, value in section_data.items():
                self.config.set(section_name, key, str(value))
        
        # Set creation timestamp
        current_time = self.get_current_timestamp()
        if not self.config.has_section('METADATA'):
            self.config.add_section('METADATA')
        self.config.set('METADATA', 'created_at', current_time)
        self.config.set('METADATA', 'updated_at', current_time)
        
        # Calculate initial MOVESPEED
        try:
            ingame_sens = float(self.config.get('SENSITIVITY', 'INGAME_SENSITIVITY'))
            movespeed = round(0.55 * (ingame_sens / 3.0), 3)
            self.config.set('SENSITIVITY', 'MOVESPEED', str(movespeed))
        except (ValueError, TypeError):
            pass
        
        self._save_config()
    
    def get(self, section: str, key: str, fallback: Any = None) -> Optional[str]:
        """Get a configuration value"""
        try:
            return self.config.get(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """Get an integer configuration value"""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Get a float configuration value"""
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get a boolean configuration value"""
        try:
            return self.config.getboolean(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def update(self, section: str, key: str, value: Any) -> bool:
        """Update a configuration value"""
        try:
            if not self.config.has_section(section):
                self.config.add_section(section)
            
            self.config.set(section, key, str(value))
            
            # Auto-update MOVESPEED when INGAME_SENSITIVITY changes
            if section == 'SENSITIVITY' and key == 'INGAME_SENSITIVITY':
                try:
                    ingame_sens = float(value)
                    movespeed = round(0.55 * (ingame_sens / 3.0), 3)
                    self.config.set('SENSITIVITY', 'MOVESPEED', str(movespeed))
                except (ValueError, TypeError):
                    pass
            
            self._update_timestamp()
            self._save_config()
            return True
        except Exception as e:
            print(f"Error updating config: {e}")
            return False
    
    def update_multiple(self, updates: Dict[str, Dict[str, Any]]) -> bool:
        """Update multiple configuration values at once"""
        try:
            for section, values in updates.items():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                
                for key, value in values.items():
                    self.config.set(section, key, str(value))
            
            # Handle MOVESPEED recalculation if INGAME_SENSITIVITY was updated
            if 'SENSITIVITY' in updates and 'INGAME_SENSITIVITY' in updates['SENSITIVITY']:
                try:
                    ingame_sens = float(updates['SENSITIVITY']['INGAME_SENSITIVITY'])
                    movespeed = round(0.55 * (ingame_sens / 3.0), 3)
                    self.config.set('SENSITIVITY', 'MOVESPEED', str(movespeed))
                except (ValueError, TypeError):
                    pass
            
            self._update_timestamp()
            self._save_config()
            return True
        except Exception as e:
            print(f"Error updating multiple configs: {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, Dict[str, str]]:
        """Get all settings as a dictionary"""
        result = {}
        for section_name in self.config.sections():
            result[section_name] = dict(self.config.items(section_name))
        return result
    
    def get_section(self, section: str) -> Dict[str, str]:
        """Get all values from a specific section"""
        try:
            return dict(self.config.items(section))
        except configparser.NoSectionError:
            return {}
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
    
    def get_created_time(self) -> Optional[str]:
        """Get creation timestamp"""
        return self.get('METADATA', 'created_at')
    
    def get_updated_time(self) -> Optional[str]:
        """Get last update timestamp"""
        return self.get('METADATA', 'updated_at')
    
    def _update_timestamp(self) -> None:
        """Update the last modified timestamp"""
        if not self.config.has_section('METADATA'):
            self.config.add_section('METADATA')
        self.config.set('METADATA', 'updated_at', self.get_current_timestamp())
    
    def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def reset_to_defaults(self, confirm: bool = False) -> bool:
        """Reset configuration to default values"""
        if not confirm:
            print(f"Would reset config: {self.config_file}")
            print("Call with confirm=True to actually reset")
            return False
            
        try:
            # Remove current config file if it exists
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
                print(f"Removed existing config: {self.config_file}")
            
            # Create fresh default config
            self.create_default_config()
            print(f"Reset to default configuration: {self.config_file}")
            return True
            
        except Exception as e:
            print(f"Error resetting config: {e}")
            return False
    
    def reset_section_to_defaults(self, section_name: str) -> bool:
        """Reset a specific section to default values"""
        try:
            if section_name not in self.default_settings:
                print(f"Unknown section: {section_name}")
                return False
            
            # Remove existing section if it exists
            if self.config.has_section(section_name):
                self.config.remove_section(section_name)
            
            # Add section with default values
            self.config.add_section(section_name)
            for key, value in self.default_settings[section_name].items():
                self.config.set(section_name, key, str(value))
            
            self._update_timestamp()
            self._save_config()
            print(f"Reset section '{section_name}' to defaults")
            return True
            
        except Exception as e:
            print(f"Error resetting section {section_name}: {e}")
            return False
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export settings to a flat dictionary (for backward compatibility)"""
        # Merge new sections into a legacy-compatible "game_settings" view
        game_settings = {}
        for sec in ('AIM', 'SENSITIVITY', 'RECOIL'):
            try:
                game_settings.update(self.get_section(sec))
            except Exception:
                pass
        # Also include legacy GAME if present
        if self.config.has_section('GAME'):
            game_settings.update(self.get_section('GAME'))
        control_settings = self.get_section('CONTROLS')
        toggle_settings = self.get_section('TOGGLES')
        color_settings = self.get_section('COLORS')
        
        # Convert to the format expected by the original code
        result = {}
        
        # Game settings with type conversion
        for key, value in game_settings.items():
            if key in ['XFOV', 'YFOV', 'SMOOTHNESS', 'INGAME_SENSITIVITY']:
                try:
                    result[key.upper()] = int(value)
                except ValueError:
                    result[key.upper()] = value
            elif key in ['HEAD_OFFSET', 'MOVESPEED']:
                try:
                    result[key.upper()] = float(value)
                except ValueError:
                    result[key.upper()] = value
            else:
                result[key.upper()] = value
        
        # Control settings
        for key, value in control_settings.items():
            if key == 'FOV_TOGGLE':
                result[key] = value.lower() == 'true'
            else:
                result[key] = value
        
        # Toggle settings (ensure backward-compatible names)
        # Accept both lowercase (legacy) and proper-case keys
        if 'fov_toggle' in toggle_settings:
            result['FOV_TOGGLE'] = toggle_settings['fov_toggle'].lower() == 'true'
        elif 'FOV_TOGGLE' in toggle_settings:
            result['FOV_TOGGLE'] = toggle_settings['FOV_TOGGLE'].lower() == 'true'
        
        # Add FPS_TOGGLE support
        if 'fps_toggle' in toggle_settings:
            result['FPS_TOGGLE'] = toggle_settings['fps_toggle'].lower() == 'true'
        elif 'FPS_TOGGLE' in toggle_settings:
            result['FPS_TOGGLE'] = toggle_settings['FPS_TOGGLE'].lower() == 'true'
            
        if 'cheat_toggle_key' in toggle_settings:
            result['CHEAT_TOGGLE'] = toggle_settings['cheat_toggle_key']
        elif 'CHEAT_TOGGLE_KEY' in toggle_settings:
            result['CHEAT_TOGGLE'] = toggle_settings['CHEAT_TOGGLE_KEY']
        if 'imgui_toggle_key' in toggle_settings:
            # Backward compatibility with previous UI_TOGGLE naming
            result['UI_TOGGLE'] = toggle_settings['imgui_toggle_key']
        elif 'IMGUI_TOGGLE_KEY' in toggle_settings:
            result['UI_TOGGLE'] = toggle_settings['IMGUI_TOGGLE_KEY']
        if 'trigger_enabled' in toggle_settings:
            result['TRIGGER_TOGGLE'] = toggle_settings['trigger_enabled'].lower() == 'true'
        elif 'TRIGGER_ENABLED' in toggle_settings:
            result['TRIGGER_TOGGLE'] = toggle_settings['TRIGGER_ENABLED'].lower() == 'true'
        
        # Colors and visuals
        for k, v in color_settings.items():
            # Keep as strings or booleans as appropriate
            if k.endswith('_ENABLED'):
                result[k] = v.lower() == 'true'
            else:
                result[k] = v
        
        return result
