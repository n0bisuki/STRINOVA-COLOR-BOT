# STRINOVA - Advanced Game Enhancement System

## ⚠️ DISCLAIMER

**This project is for educational purposes only.** This code is designed to demonstrate advanced concepts in computer vision, input automation, configuration management, and game mechanics analysis. **This software is NOT intended to cause any damage to games, systems, or any software/hardware.**

Use of this software to cheat in online games or to gain unfair advantages in multiplayer environments is strictly against the terms of service of most games and can result in account bans, legal consequences, or other penalties. **The author assumes no responsibility for any misuse of this code.**

---

## 📋 Project Overview

STRINOVA is an advanced Python-based system demonstrating sophisticated game enhancement techniques. It showcases professional-grade architecture with modular configuration management, multi-threaded processing, computer vision integration, and hardware automation—all designed for **educational and research purposes only**.

**If you need any support or have questions, please join our Discord server:**  
🔗 **Discord:** https://discord.gg/j7Faupsf4h

---

## 📁 File Documentation

### 1. **index.py** - Application Entry Point
**Location:** `STRINOVA/index.py` (Lines 1-22)

**Purpose:**  
Main application bootstrap that initializes the settings system and launches the core application.

**Key Functions:**
- **Settings Initialization:** Creates a `SettingsManager` instance to handle INI-based configuration
- **Configuration Export:** Converts settings to dictionary format for backward compatibility
- **Application Launch:** Instantiates and runs the `NeoRant` core system

**Workflow:**
```
index.py → SettingsManager() → NeoRant(settings, settings_manager)
```

**Features:**
- Colorama initialization for terminal color support
- Clean separation between configuration and application logic
- Settings validation and auto-migration

---

### 2. **util/settings_manager.py** - Advanced Configuration System
**Location:** `STRINOVA/util/settings_manager.py` (Lines 1-404)

**Purpose:**  
Professional-grade settings management system using INI file format with full CRUD operations, validation, and backup compatibility.

**Key Features:**

#### **Configuration Sections**

**AIM Section** - Targeting behavior parameters:
```ini
[AIM]
XFOV=113              # Horizontal field of view (pixels)
YFOV=84               # Vertical field of view (pixels)
SMOOTHNESS=1          # Targeting smoothness factor
HEAD_OFFSET=0.5       # Pixel offset for head targeting
AIM_SMOOTHING_FACTOR=0.1  # Exponential smoothing coefficient
```

**SENSITIVITY Section** - Movement sensitivity tuning:
```ini
[SENSITIVITY]
MOVESPEED=0.5                 # Base movement multiplier
INGAME_SENSITIVITY=3          # In-game mouse sensitivity
Y_SPEED_MULTIPLIER=1.0        # Y-axis speed adjustment
```

**RECOIL Section** - Recoil compensation system:
```ini
[RECOIL]
RECOIL_MODE=offset           # 'offset' or 'move' mode
RECOIL_X=0                   # Horizontal recoil compensation
RECOIL_Y=0                   # Vertical recoil compensation
MAX_OFFSET=100               # Maximum recoil offset
RECOIL_RECOVER=0             # Recovery speed per frame
```

**CONTROLS Section** - Keyboard/input bindings:
```ini
[CONTROLS]
AIM_ASSIST_KEY=0x01          # Mouse button 1 (left click)
FLICK_KEY=0x04               # Mouse button 4 (side button)
```

**TOGGLES Section** - Feature activation keys:
```ini
[TOGGLES]
FOV_TOGGLE=False             # Show/hide FOV visualization
FPS_TOGGLE=False             # Show/hide FPS counter
CHEAT_TOGGLE_KEY=0x74        # F5 key
IMGUI_TOGGLE_KEY=0x75        # F6 key
TRIGGER_KEY=0x43             # C key
```

**COLORS Section** - Visual element configuration:
```ini
[COLORS]
ANIME_COLOR=strinova_purple   # Target color detection
BOX_ENABLED=True              # Enemy bounding box display
BOX_COLOR=red                 # Box outline color
HEAD_ENABLED=True             # Head marker display
HEAD_COLOR=yellow             # Head marker color
LINE_ENABLED=True             # Line to target display
LINE_COLOR=green              # Line color
```

#### **Core Methods**

- **`__init__(config_file)`** - Initialize manager and load/create config
- **`get(section, key, fallback)`** - Retrieve string value
- **`get_int/get_float/get_bool()`** - Type-safe value retrieval
- **`update(section, key, value)`** - Update single value and auto-save
- **`update_multiple(updates)`** - Batch update multiple values
- **`get_all_settings()`** - Export all settings as nested dictionary
- **`get_section(section)`** - Get all values from specific section
- **`export_to_dict()`** - Legacy-compatible flat dictionary export
- **`reset_to_defaults(confirm=True)`** - Full reset to defaults
- **`reset_section_to_defaults(section)`** - Reset specific section

#### **Advanced Features**

- **Automatic Type Conversion:** Validates and converts values to correct types
- **Legacy Migration:** Backward compatible with old JSON-based configs
- **Auto-Update MOVESPEED:** Recalculates when `INGAME_SENSITIVITY` changes
- **Timestamp Tracking:** Tracks creation and modification times
- **Case Preservation:** Maintains proper key casing (prevents auto-lowercasing)
- **Validation & Backup:** Validates settings and creates defaults if corrupted

---

### 3. **util/setting.py** - Utility Functions
**Location:** `STRINOVA/util/setting.py` (Lines 1-35)

**Purpose:**  
Provides convenient helper functions for settings access and color detection.

**Key Functions:**

```python
def get_settings_manager(config_file="settings.ini"):
    """Get a SettingsManager instance"""
    
def read_args_json_for(game_id: str) -> dict:
    """Load game-specific launch arguments from JSON"""
    
def get_color_bounds(color: str) -> tuple:
    """Get HSV color detection ranges for target colors"""
```

**Supported Colors:**
- **strinova_blackish_purple:** [141, 114, 96] to [156, 255, 255]
- **strinova_red:** [167, 102, 76] to [179, 255, 255]
- **strinova_purple:** [140, 110, 140] to [160, 255, 255]

**Discord Support Link:**
```python
DISCORD = "https://discord.gg/j7Faupsf4h"
```

---

### 4. **NeoRant.py** - Core Application Logic
**Location:** `STRINOVA/NeoRant.py` (Lines 1-245)

**Purpose:**  
Advanced game enhancement engine with multi-threaded monitoring, computer vision target detection, intelligent aiming, recoil compensation, and trigger automation.

**Key Components:**

#### **Initialization**
- Loads all settings from configuration system
- Initializes screen capture with game-specific parameters
- Sets up Arduino mouse interface for precise control
- Creates ImGui overlay for real-time visualization
- Starts three background monitoring threads

#### **Threading Architecture**

Three daemon threads work concurrently:

1. **`listener_keybind()` - Keyboard Input Monitor**
   - Detects cheat toggle key (F5 / 0x74)
   - Detects trigger toggle key (C / 0x43)
   - Uses edge-detection for press-once activation

2. **`listener() - Action Processor**
   - Monitors aim assist key (left mouse button)
   - Monitors flick key (side mouse button)
   - Triggers appropriate action based on key state

3. **ImGui Render Loop - Overlay Display**
   - Renders real-time overlay information
   - Hidden from taskbar
   - Displays targeting visualization

#### **Aiming System**

**`calculate_aim(x, y)` - Intelligent Aim Calculation**
```python
# Steps:
1. Apply in-game sensitivity: raw_x = x * INGAME_SENSITIVITY
2. Apply Y-axis multiplier for recoil/drop compensation
3. Exponential smoothing with previous values
4. Returns calibrated aim vector
```

**Features:**
- Sensitivity multiplication for game-specific calibration
- Y-axis independent multiplier for vertical drop compensation
- Exponential smoothing to reduce jitter (AIM_SMOOTHING_FACTOR)
- Continuity with previous frame values

#### **Recoil Compensation System**

**Two Recoil Modes:**

1. **'move' Mode:** Directly adds recoil to movement
   - Applied when mouse button 1 is down
   - Adds RECOIL_X to horizontal movement
   - Adds RECOIL_Y to vertical movement

2. **'offset' Mode:** Aims below target to compensate
   - Accumulates recoil offset while shooting
   - Offset clamped to MAX_OFFSET
   - Gradually recovers at RECOIL_RECOVER rate
   - More natural feeling, adjusts crosshair position

#### **Action Processing**

**`process(action)` - Main action dispatcher**
- Calculates delta time for frame-rate independent updates
- Routes to specific action handler based on action type

**Actions:**

1. **`move()` - Continuous targeting**
   - Applies recoil compensation
   - Moves mouse toward target at MOVESPEED rate
   - Frame-rate dependent smoothing

2. **`flick()` - Rapid snap-to-target**
   - Quick aim at detected head position
   - Optional auto-trigger on successful flick
   - No recoil compensation needed

3. **`trigger()` - Automated clicking**
   - Fires mouse button automatically
   - Triggered when TRIGGER_TOGGLE is active

#### **Toggle Methods**

- **`Cheat_Toggled()`** - Enables/disables all aiming features
- **`Trigger_Toggled()`** - Activates/deactivates auto-trigger

#### **Color Detection**

Integrated with `util/setting.py`:
- Supports multiple target color profiles (purple, red, etc.)
- Uses HSV color space for robust detection
- Configurable via COLORS section in settings

#### **State Management**

Key state variables:
```python
TOGGLED_CHEATE          # Master on/off switch
TRIGGER_TOGGLE          # Auto-trigger enabled
recoil_offset          # Current recoil compensation offset
move_x, move_y         # Movement accumulator
previous_x, previous_y # Previous frame position for smoothing
last_time              # For delta time calculations
```

---

## 🔧 Technology Stack

**Core Libraries:**
- **OpenCV** (`cv2`) - Computer vision and image processing
- **NumPy** (`np`) - Numerical computing and arrays
- **ConfigParser** - INI file configuration management
- **PyWin32** (`win32api`) - Windows system integration
- **ImGui** - Overlay GUI rendering
- **Colorama** - Terminal color output
- **TermColor** - Colored terminal text
- **PSUtil** - Process utilities

**Architecture Patterns:**
- Multi-threaded event monitoring
- State machine for toggle features
- Delta-time based physics calculations
- Exponential smoothing for jitter reduction
- Configuration validation and auto-migration

---

## 🎮 How It Works (Technical Flow)

1. **Startup:** `index.py` initializes `SettingsManager`
2. **Config Validation:** Settings are loaded/created with validation
3. **App Init:** `NeoRant` initializes with validated settings
4. **Threading:** Three background threads start monitoring
5. **Overlay:** ImGui renders visualization loop
6. **Key Detection:**
   - F5 toggles cheat on/off
   - C toggles auto-trigger
7. **Targeting Loop:**
   - When cheat is ON and aim key is held:
     - Screen capture targets with color detection
     - Closest target identified
     - Aim calculated with sensitivity & smoothing
     - Recoil compensation applied
     - Mouse moves toward target
   - When flick key is held:
     - Rapid snap-to-head position
     - Optional auto-trigger if trigger enabled
8. **Auto-Trigger:**
   - When trigger is ON, mouse clicks automatically
   - Can be combined with other actions

---

## 📝 Configuration Guide

All settings are in `settings.ini` and can be modified in real-time:

**Performance Tuning:**
- Increase `AIM_SMOOTHING_FACTOR` (0-1) for less jitter, higher latency
- Adjust `MOVESPEED` for movement speed per frame
- Modify `XFOV`/`YFOV` to change detection zone

**Sensitivity Calibration:**
- Set `INGAME_SENSITIVITY` to match game settings
- Use `Y_SPEED_MULTIPLIER` for vertical drop compensation
- Calibrate `HEAD_OFFSET` for headshot consistency

**Recoil Compensation:**
- Set `RECOIL_MODE` to 'offset' for camera adjustment or 'move' for direct movement
- Configure `RECOIL_X`/`RECOIL_Y` based on weapon
- Set `MAX_OFFSET` for maximum deviation
- Adjust `RECOIL_RECOVER` for recovery speed

**Keybindings:**
- Hex keycodes: 0x01=LMB, 0x04=Button4, 0x74=F5, 0x75=F6, 0x43=C
- Change `CHEAT_TOGGLE_KEY` or `TRIGGER_KEY` as needed

**Visual Customization:**
- Enable/disable boxes, head markers, lines
- Configure colors for different visual elements
- Set `ANIME_COLOR` for target detection profile

---

## 🚀 Requirements

- Python 3.7+
- Windows OS (uses Win32 API)
- Arduino device (for mouse control)
- OpenCV
- NumPy
- ConfigParser (built-in)

See `requirements.txt` for all dependencies.

---

## ⚖️ Legal & Ethical Considerations

**This code is provided for educational and research purposes only.**

- ❌ **Do NOT use** this code to cheat in online multiplayer games
- ❌ **Do NOT use** this code to violate any game's Terms of Service
- ❌ **Do NOT use** this code to gain unfair advantages in competitive play
- ✅ **DO use** this code to learn about computer vision applications
- ✅ **DO use** this code to understand game mechanics and automation
- ✅ **DO study** this code to improve advanced Python programming skills
- ✅ **DO explore** configuration management patterns and architecture

**Potential consequences of misuse:**
- Permanent game account bans
- Legal action from game developers/publishers
- Hardware damage (if improperly interfacing with Arduino)
- Network/system issues from automation conflicts

---

## 💬 Support & Community

Need help? Have questions? Join our community Discord server:

🔗 **Discord Server:** https://discord.gg/j7Faupsf4h

Feel free to ask questions about:
- Computer vision and image processing
- Advanced Python programming
- Multithreading and concurrency
- Windows API integration
- Game mechanics analysis
- Configuration management patterns
- Mouse automation techniques

---

## 📜 License & Attribution

This project is provided as-is for educational purposes. Users are responsible for ensuring they comply with all applicable laws and terms of service agreements.

---

## 🔬 Learning Resources & Advanced Concepts

This project demonstrates several sophisticated programming concepts:

### **Computer Vision**
- HSV color space conversion and analysis
- Contour detection and morphological operations
- Real-time image processing optimization

### **System Programming**
- Windows API integration (win32api, winsound)
- Serial communication with hardware devices
- Multi-threaded event-driven architecture

### **Software Architecture**
- Configuration management patterns (INI-based)
- Type-safe settings validation
- Backward compatibility and migration strategies
- State machine implementation

### **Game Mechanics**
- Sensitivity calibration algorithms
- Recoil compensation techniques (offset vs movement)
- Exponential smoothing for jitter reduction
- Delta-time based frame-rate independent updates

### **UI/Graphics**
- ImGui overlay rendering
- Real-time visualization during gameplay
- Taskbar hiding and window management

### **Hardware Integration**
- Arduino mouse control via serial interface
- Precision timing for input automation
- Safe hardware communication protocols

Study this code to deepen your understanding of professional-grade Python systems!

---

**Last Updated:** 2026-03-25  
**Version:** Educational Release - Advanced System
**Complexity Level:** Intermediate to Advanced
