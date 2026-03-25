# imgui/overlay.py
import os
import cv2
import time
import glfw
import imgui
import ctypes
import win32gui
import win32con
import win32api
import webbrowser
import numpy as np
from PIL import Image
from OpenGL.GL import *
from ctypes import wintypes
from util.setting import DISCORD 
from util.setting import STRENOVA 
from util.virtual_key_codes import virtual_keys
from imgui.integrations.glfw import GlfwRenderer
# from util.setting import read_json_file, update_json_config 
from util.settings_manager import SettingsManager

user32 = ctypes.windll.user32
GetAsyncKeyState = user32.GetAsyncKeyState

class ImGuiOverlay:
    def __init__(self, hk_self):
        # High-DPI awareness
        ctypes.windll.user32.SetProcessDPIAware()

        # Core references
        self.hk_self = hk_self
        self.title = "Overlay"

        # Screen/cache values
        self.screen_width = hk_self.monitor_width - 1
        self.screen_height = hk_self.monitor_height - 1

        # Window/GLFW/imgui handles
        self.hwnd = None
        self.impl = None
        self.window = None

        # Runtime state
        self.loop = True
        self.show_window = False
        self.last_toggle_time = 0
        self._last_style_check = 0.0
        self.streamDllLoaded = False

        # Key capture / input assignment state
        self.waiting_for_key = None   # Which keybind we're assigning (e.g. "LEFT_MB")
        self.key_input_ready = False  # Set to True externally when a key is captured
        self.last_pressed_key = None  # Captured key value
        
        # Confirmation dialog state
        self.show_reset_confirmation = False

        
        self.cx = int(self.screen_width // 2)
        self.cy = int(self.screen_height // 2)
        
        self.color_list = ['red', 'green', 'white','purple','yellow']

        # UI toggle key (with safe fallback)
        try:
            self._ui_toggle_vk = int(self.hk_self.IMGUI_TOGGLE_KEY, 16)
        except Exception:
            import win32con
            self._ui_toggle_vk = win32con.VK_INSERT

    def init_window(self):
        if not glfw.init():
            raise Exception("Could not initialize GLFW")

        glfw.window_hint(glfw.FLOATING, glfw.TRUE)
        glfw.window_hint(glfw.DECORATED, glfw.FALSE)
        glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, glfw.TRUE)
        # Create hidden first to avoid taskbar entry creation; we'll show after styles are applied
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        # Do not focus when shown
        try:
            glfw.window_hint(glfw.FOCUS_ON_SHOW, glfw.FALSE)
        except Exception:
            pass

        # Create with empty title so nothing leaks into taskbar/alt-tab labels
        self.window = glfw.create_window(
            self.screen_width, self.screen_height, "", None, None
        )
        if not self.window:
            glfw.terminate()
            raise Exception("Failed to create GLFW window")

        glfw.make_context_current(self.window)
        self.hwnd = self.get_hwnd_from_glfw(self.window)
        # Cap to monitor refresh to reduce CPU usage (vsync)
        try:
            glfw.swap_interval(1)
        except Exception:
            pass
        self.make_window_clickthrough(self.hwnd)  
        # Ensure the window doesn't appear on the taskbar right away
        self.Hide_from_taskbar()
        # Make a hidden owner window to ensure this window never shows in taskbar
        try:
            self._owner_hwnd = self._create_hidden_owner_window()
            # Set as owner; owned windows are excluded from the taskbar
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_HWNDPARENT, self._owner_hwnd) 
            win32gui.SetWindowText(self.hwnd, "") 
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNOACTIVATE)
        except Exception:
            self._owner_hwnd = None
            pass

        # Re-apply taskbar hiding when window focus changes (Windows sometimes resets styles)
        def _on_focus(window, focused):
            try:
                self.Hide_from_taskbar()
            except Exception:
                pass
        glfw.set_window_focus_callback(self.window, _on_focus)


        imgui.create_context()

        io = imgui.get_io()
        io.config_flags |= imgui.CONFIG_NAV_ENABLE_KEYBOARD
        imgui.style_colors_dark()
        self.impl = GlfwRenderer(self.window) 
 

        style = imgui.get_style()
        colors = style.colors
        self.purple = (132/255.0, 58/255.0, 255/255.0, 1.0)      # RGBA (0-1)
        self.purple_hovered = (160/255.0, 80/255.0, 255/255.0, 1.0)
        self.purple_active = (100/255.0, 40/255.0, 200/255.0, 1.0)
        # Slightly darkened purple for backgrounds
        self.window_bg = (self.purple[0] * 0.15, self.purple[1] * 0.15, self.purple[2] * 0.15, 0.95)

        # Apply to buttons
        colors[imgui.COLOR_BUTTON] = self.purple
        colors[imgui.COLOR_BUTTON_HOVERED] = self.purple_hovered
        colors[imgui.COLOR_BUTTON_ACTIVE] = self.purple_active

        
        # Slider
        colors[imgui.COLOR_SLIDER_GRAB] = self.purple
        colors[imgui.COLOR_SLIDER_GRAB_ACTIVE] = self.purple_active

        # Tab (left tab selection)
        colors[imgui.COLOR_TAB] = self.purple_hovered
        colors[imgui.COLOR_TAB_ACTIVE] = self.purple
        colors[imgui.COLOR_TAB_HOVERED] = self.purple_hovered
        colors[imgui.COLOR_TAB_UNFOCUSED] = (0.2, 0.2, 0.2, 1.0)   # optional background
        colors[imgui.COLOR_TAB_UNFOCUSED_ACTIVE] = self.purple_active

        # Headers and check marks
        colors[imgui.COLOR_HEADER] = self.purple
        colors[imgui.COLOR_HEADER_HOVERED] = self.purple_hovered
        colors[imgui.COLOR_HEADER_ACTIVE] = self.purple_active
        colors[imgui.COLOR_CHECK_MARK] = self.purple

        # Frame backgrounds (affects slider background)
        colors[imgui.COLOR_FRAME_BACKGROUND] = (self.purple[0], self.purple[1], self.purple[2], 0.25)
        colors[imgui.COLOR_FRAME_BACKGROUND_HOVERED] = (self.purple_hovered[0], self.purple_hovered[1], self.purple_hovered[2], 0.35)
        colors[imgui.COLOR_FRAME_BACKGROUND_ACTIVE] = (self.purple_active[0], self.purple_active[1], self.purple_active[2], 0.50)

        # Window background globally
        colors[imgui.COLOR_WINDOW_BACKGROUND] = self.window_bg

        # Title bar background to match theme
        colors[imgui.COLOR_TITLE_BACKGROUND] = (self.purple[0] * 0.25, self.purple[1] * 0.25, self.purple[2] * 0.25, 1.0)
        colors[imgui.COLOR_TITLE_BACKGROUND_ACTIVE] = (self.purple[0] * 0.35, self.purple[1] * 0.35, self.purple[2] * 0.35, 1.0)
        colors[imgui.COLOR_TITLE_BACKGROUND_COLLAPSED] = (self.purple[0] * 0.18, self.purple[1] * 0.18, self.purple[2] * 0.18, 0.80)

    def make_window_clickthrough(self, hwnd):
        styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        styles |= win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, styles)
        win32gui.SetLayeredWindowAttributes(hwnd, 0, 255, win32con.LWA_ALPHA)

    def set_click_through(self, enable=True):
        styles = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        if enable:
            styles |= win32con.WS_EX_TRANSPARENT
        else:
            styles &= ~win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, styles)

    def get_hwnd_from_glfw(self, window):
        glfw._glfw.glfwGetWin32Window.restype = ctypes.c_void_p
        glfw._glfw.glfwGetWin32Window.argtypes = [ctypes.c_void_p]
        return glfw._glfw.glfwGetWin32Window(window)
 
    def Hide_from_taskbar(self):   
        ex_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        ex_style &= ~win32con.WS_EX_APPWINDOW  # Remove app window style
        ex_style |= win32con.WS_EX_TOOLWINDOW  # Add tool window style
        ex_style |= win32con.WS_EX_NOACTIVATE  # Do not activate -> avoid taskbar/alt-tab
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, ex_style)

        # Force Windows to refresh the non-client area to update styles
        win32gui.SetWindowPos(
            self.hwnd, 0, 0, 0, 0, 0,
            win32con.SWP_NOACTIVATE |
            win32con.SWP_NOMOVE |
            win32con.SWP_NOSIZE |
            win32con.SWP_NOZORDER |
            win32con.SWP_FRAMECHANGED
        )

    def enforce_taskbar_hidden(self):
        """Continuously ensure the overlay stays hidden from the taskbar.
        Some window events can flip WS_EX_APPWINDOW back on; if that happens,
        remove it again and force a non-client refresh.
        """
        try:
            now = time.time()
            # Only check a couple times per second
            if now - self._last_style_check < 0.5:
                return
            self._last_style_check = now
            ex_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
            needs_fix = (ex_style & win32con.WS_EX_APPWINDOW) or not (ex_style & win32con.WS_EX_TOOLWINDOW) or not (ex_style & win32con.WS_EX_NOACTIVATE)
            if needs_fix:
                self.Hide_from_taskbar()
            # Re-assert owner and empty title (infrequently)
            if getattr(self, "_owner_hwnd", None):
                try:
                    win32gui.SetWindowLong(self.hwnd, win32con.GWL_HWNDPARENT, self._owner_hwnd)
                except Exception:
                    pass
            try:
                if win32gui.GetWindowText(self.hwnd):
                    win32gui.SetWindowText(self.hwnd, "")
            except Exception:
                pass
        except Exception:
            pass

    def _create_hidden_owner_window(self):
        """Create an invisible owner window to prevent taskbar button for the overlay.
        Uses the built-in STATIC window class to avoid custom registration.
        """
        hInstance = win32api.GetModuleHandle(None)
        hwnd_owner = win32gui.CreateWindowEx(
            win32con.WS_EX_TOOLWINDOW,  # tool window, no taskbar
            "Static",                   # built-in class
            None,                        # no title
            win32con.WS_POPUP,           # popup style, no border
            0, 0, 0, 0,                  # zero-size and off-screen
            0,                           # no parent
            0,                           # no menu
            hInstance,
            None
        )
        # Keep it hidden just in case
        win32gui.ShowWindow(hwnd_owner, win32con.SW_HIDE)
        return hwnd_owner

    def color_from_name(self, name):
        mapping = {
            "red": (1.0, 0.0, 0.0, 1.0),
            "green": (0.0, 1.0, 0.0, 1.0),
            "white": (1.0, 1.0, 1.0, 1.0),
            "yellow": (1.0, 1.0, 0.0, 1.0),
            "purple":(132/255.0, 58/255.0, 255/255.0, 1.0)  
        }
        return mapping.get(name.lower(), (1.0, 1.0, 1.0, 1.0))  # default white

    def render_loop(self):
        self.set_click_through(not self.show_window) 
        while not glfw.window_should_close(self.window) and self.loop:
            glfw.poll_events()
            self.impl.process_inputs()
            # Ensure the overlay is interactable when ImGui wants mouse/keyboard
            try:
                io = imgui.get_io()
                want_input = self.show_window or io.want_capture_mouse or io.want_capture_keyboard
                self.set_click_through(not want_input)
            except Exception:
                pass
            # Re-enforce hidden state in case Windows toggled styles
            self.enforce_taskbar_hidden()

            # Use cached virtual key to avoid per-frame parsing cost
            if win32api.GetAsyncKeyState(self._ui_toggle_vk) & 0x8000:
                current_time = time.time()
                self.hk_self.play("play") 
                if current_time - self.last_toggle_time > 0.3:
                    self.show_window = not self.show_window
                    self.set_click_through(not self.show_window)
                    self.last_toggle_time = current_time

            imgui.new_frame()

            # Draw FOV box in background every frame
            if self.hk_self.FOV_TOGGLE:
                self.draw_valorant_side_brackets_alt()
            if not self.show_window:
                self.draw_target_overlays()

                
            self.render_watermarks()
            if self.show_window:
                self.render_window()

            imgui.render()
            glClearColor(0, 0, 0, 0)
            glClear(GL_COLOR_BUFFER_BIT)
            self.impl.render(imgui.get_draw_data())
            glfw.swap_buffers(self.window) 

            if win32api.GetAsyncKeyState(win32con.VK_END) & 0x8000:
                break

        self.impl.shutdown()
        glfw.terminate()

    def render_watermarks(self):  
        # Calculate dynamic window height based on content
        base_height = 100  # Base height for minimum content
        fps_height = 15 if self.hk_self.FPS_TOGGLE else 10  # Additional height for FPS
        total_height = base_height + fps_height
        
        # Position window at bottom right with dynamic sizing
        window_width = 170 
        window_height = 150 
        imgui.set_next_window_position(self.screen_width - window_width, self.screen_height - window_height)
        imgui.set_next_window_size(150, total_height)
        
        imgui.push_style_color(imgui.COLOR_WINDOW_BACKGROUND, *[0.1, 0.1, 0.1, 0.1])
        imgui.begin(
            "Watermark Layout",
            True,
            imgui.WINDOW_NO_TITLE_BAR
            | imgui.WINDOW_NO_RESIZE
            | imgui.WINDOW_NO_MOVE
            | imgui.WINDOW_NO_SAVED_SETTINGS
            | imgui.WINDOW_NO_SCROLLBAR
            | imgui.WINDOW_NO_INPUTS,
        )
        text = "Singularity"
        text_width = imgui.calc_text_size(text).x
        window_width = imgui.get_window_width()
        center_x = (window_width - text_width) / 2

        imgui.set_cursor_pos_x(center_x)
        if self.hk_self.TOGGLED_CHEATE: imgui.text_colored(text, *self.color_from_name("purple"))
        else: imgui.text_colored(text, *self.color_from_name("red"))


        # FPS badge (label left, value right)
        if self.hk_self.FPS_TOGGLE:
            fps = self.hk_self.screen_capture.fps
            if fps is not None :
                color = ("green" if fps >= 100 else ("yellow" if fps >= 60 else "red"))
                # 2-column layout
                imgui.columns(2, "wm_fps_cols", border=False)
                # Left: label
                imgui.text("FPS:")
                imgui.next_column()
                # Right: value right-aligned within the column
                value = f"{fps:.0f}"
                val_w = imgui.calc_text_size(value).x
                col_w = imgui.get_column_width()
                # Move cursor so that text ends at the right edge (with small padding)
                right_pad = 8
                imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + max(0, col_w - val_w - right_pad))
                imgui.text_colored(value, *self.color_from_name(color))
                imgui.columns(1)



        imgui.columns(2, "wm_assist_cols", border=False)
        imgui.text("Assist:")
        imgui.next_column()
        value = "Active" if self.hk_self.TOGGLED_CHEATE else "Inactive"
        val_w = imgui.calc_text_size(value).x
        col_w = imgui.get_column_width()
        right_pad = 8
        imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + max(0, col_w - val_w - right_pad))
        imgui.text_colored(
            value,
            *(self.color_from_name("green") if self.hk_self.TOGGLED_CHEATE else self.color_from_name("red"))
        )
        imgui.columns(1)


        imgui.columns(2, "wm_sniper_cols", border=False)
        imgui.text("Sniper:")
        imgui.next_column()
        value = "Active" if self.hk_self.TOGGLED_CHEATE else "Inactive"
        val_w = imgui.calc_text_size(value).x
        col_w = imgui.get_column_width()
        right_pad = 8
        imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + max(0, col_w - val_w - right_pad))
        imgui.text_colored(
            value,
            *(self.color_from_name("green") if self.hk_self.TOGGLED_CHEATE else self.color_from_name("red"))
        )
        imgui.columns(1) 


        imgui.columns(2, "wm_trigger_cols", border=False)
        imgui.text("Trigger:")
        imgui.next_column()
        value = "Active" if (self.hk_self.TOGGLED_CHEATE and self.hk_self.TRIGGER_TOGGLE) else "Inactive"
        val_w = imgui.calc_text_size(value).x
        col_w = imgui.get_column_width()
        right_pad = 8
        imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + max(0, col_w - val_w - right_pad))
        imgui.text_colored(
            value,
            *(self.color_from_name("green") if (self.hk_self.TOGGLED_CHEATE and self.hk_self.TRIGGER_TOGGLE) else self.color_from_name("red"))
        )
        imgui.columns(1)  

        imgui.text("")
        imgui.same_line()
        imgui.text_colored(f"XFOV: {self.hk_self.XFOV}", *self.color_from_name("white"))
        imgui.same_line()
        imgui.text_colored(f"YFOV: {self.hk_self.YFOV}", *self.color_from_name("white"))
        imgui.end()
        imgui.pop_style_color() 
    
    
    def draw_valorant_side_brackets_alt(self):
        """Alternate function that draws the same side brackets as the primary one.
        Kept identical geometry and palette so it renders the same when called ("same to same").
        """
        try: 
            
            xfov = self.hk_self.XFOV
            yfov = self.hk_self.YFOV
            thickness=1.0
            
            if xfov <= 0 or yfov <= 0:
                return

            x1 = int(self.cx - xfov // 2)
            y1 = int(self.cy - yfov // 2)
            x2 = int(self.cx + xfov // 2)
            y2 = int(self.cy + yfov // 2)

            # Choose a draw list
            draw_list = None
            for getter in (getattr(imgui, "get_foreground_draw_list", None),
                           getattr(imgui, "get_background_draw_list", None),
                           getattr(imgui, "get_window_draw_list", None)):
                if getter:
                    try:
                        draw_list = getter()
                    except Exception:
                        draw_list = None
                if draw_list is not None:
                    break
            if draw_list is None:
                return

            def rgba(r, g, b, a):
                return imgui.get_color_u32_rgba(r, g, b, a)

            # Same color palette as primary
            base = rgba(1.0, 1.0, 1.0, 1.0)
            base_soft = rgba(1.0, 1.0, 1.0, 0.35)
            glow_soft = rgba(1.0, 1.0, 1.0, 0.08)
            glow_soft2 = rgba(1.0, 1.0, 1.0, 0.04)

            # Same geometry as primary
            inset = max(10, int(xfov * 0.12))
            bevel = max(12, int(yfov * 0.15))

            L = [
                (x1 + inset, y1),
                (x1,         y1 + bevel),
                (x1,         y2 - bevel),
                (x1 + inset, y2),
            ]
            R = [
                (x2 - inset, y1),
                (x2,         y1 + bevel),
                (x2,         y2 - bevel),
                (x2 - inset, y2),
            ]

            # Keep joins clean: draw as polylines with unified thickness
            inner_gap = max(2, int(min(xfov, yfov) * 0.025))

            # Base layer
            draw_list.add_polyline(L, base, False, thickness)
            draw_list.add_polyline(R, base, False, thickness)
            # Soft overlays, same thickness
            draw_list.add_polyline(L, base_soft, False, thickness)
            draw_list.add_polyline(R, base_soft, False, thickness)
            draw_list.add_polyline(L, glow_soft, False, thickness)
            draw_list.add_polyline(R, glow_soft, False, thickness)
            draw_list.add_polyline(L, glow_soft2, False, thickness)
            draw_list.add_polyline(R, glow_soft2, False, thickness)

            # Inner inset polylines for the fill-toward-center vibe
            L_in = [(x + inner_gap, y) for (x, y) in L]
            R_in = [(x - inner_gap, y) for (x, y) in R]
            draw_list.add_polyline(L_in, base_soft, False, thickness)
            draw_list.add_polyline(R_in, base_soft, False, thickness)
            draw_list.add_polyline(L_in, glow_soft, False, thickness)
            draw_list.add_polyline(R_in, glow_soft, False, thickness) 
        except Exception:
            pass
    
    
    def draw_target_overlays(self):
        """Draw target lines and boxes on screen overlay"""
        try: 
                
            xfov = self.hk_self.XFOV
            yfov = self.hk_self.YFOV



            if xfov <= 0 or yfov <= 0:
                return
 
            # print(self.hk_self.BOX_COLOR)
            # print(self.color_from_name(self.hk_self.BOX_COLOR))

            box_color = imgui.get_color_u32_rgba(*self.color_from_name(self.hk_self.BOX_COLOR))
            head_color = imgui.get_color_u32_rgba(*self.color_from_name(self.hk_self.HEAD_COLOR)) 
            line_color = imgui.get_color_u32_rgba(*self.color_from_name(self.hk_self.LINE_COLOR))
            box_enabled = self.hk_self.BOX_ENABLED
            head_enabled = self.hk_self.HEAD_ENABLED
            line_enabled = self.hk_self.LINE_ENABLED
            thickness= 0.1 
            # print(box_color)

            # Get draw list
            draw_list = None
            for getter in (getattr(imgui, "get_foreground_draw_list", None), 
                getattr(imgui, "get_background_draw_list", None), 
                getattr(imgui, "get_window_draw_list", None)):
                if getter:
                    try:
                        draw_list = getter()
                    except Exception:
                        draw_list = None
                if draw_list is not None:
                    break
            if draw_list is None:
                return 
 
            # Draw target elements like CV2 debug window - use data from main loop only
            if (hasattr(self.hk_self.screen_capture, 'target') and
                self.hk_self.screen_capture.target is not None and
                hasattr(self.hk_self.screen_capture, 'closest_contour')):

                # Get target coordinates (relative to FOV center) - already captured by main loop
                target_rel = self.hk_self.screen_capture.target
                contour = self.hk_self.screen_capture.closest_contour

                
                if contour is not None and box_enabled:
                    # Draw rectangle around target
                    x, y, w, h = cv2.boundingRect(contour)
                    # Convert FOV coordinates to screen coordinates
                    # The FOV region starts at (center_x - fov_width//2, center_y - fov_height//2)
                    fov_start_x = self.cx - xfov//2
                    fov_start_y = self.cy - yfov//2
                    rect_screen_x1 = fov_start_x + x
                    rect_screen_y1 = fov_start_y + y
                    rect_screen_x2 = rect_screen_x1 + w
                    rect_screen_y2 = rect_screen_y1 + h
                    
                    # Draw rectangle around target 
                    draw_list.add_rect(rect_screen_x1, rect_screen_y1, rect_screen_x2, rect_screen_y2, box_color, 0, thickness)
                    

                if target_rel is not None and line_enabled:
                    # Draw line from center to target
                    target_screen_x = self.cx + target_rel[0]
                    target_screen_y = self.cy + target_rel[1] 
                    draw_list.add_line(self.cx, self.cy, target_screen_x, target_screen_y,line_color,thickness)

                # Draw head position if detected
                if (hasattr(self.hk_self.screen_capture, 'head_position') and head_enabled and
                    self.hk_self.screen_capture.head_position is not None): 
                    # Convert FOV coordinates to screen coordinates
                    fov_start_x = self.cx - xfov//2
                    fov_start_y = self.cy - yfov//2  
                    
                    # Draw 2D box around head if head_box is available
                    if (hasattr(self.hk_self.screen_capture, 'head_box') and
                        self.hk_self.screen_capture.head_box is not None):
                        head_box = self.hk_self.screen_capture.head_box
                        # Convert head box coordinates to screen coordinates
                        head_box_x1 = fov_start_x + head_box[0]
                        head_box_y1 = fov_start_y + head_box[1]
                        head_box_x2 = head_box_x1 + head_box[2]
                        head_box_y2 = head_box_y1 + head_box[3]
                        
                        # Draw yellow rectangle around head
                        draw_list.add_rect(head_box_x1, head_box_y1, head_box_x2, head_box_y2, head_color, 0, thickness)
            else:
                pass  # No debug output needed
            
        except Exception as e:
            # print(f"Target Overlay error: {e}")  # Show errors instead of hiding them
                pass 
 
    def desc(self, v): return {item["Value"].upper(): (item["Constant"].replace("VK_", "") if item["Constant"] else item["Description"]) for item in virtual_keys}.get(str(v).upper(), "None")  
    def render_window(self):
        w, h = 700, 420
        imgui.set_next_window_size(w, h, condition=imgui.ONCE)

        # Window style
        imgui.push_style_var(imgui.STYLE_WINDOW_ROUNDING, 10.0)
        imgui.push_style_var(imgui.STYLE_WINDOW_BORDERSIZE, 1.0)
        imgui.push_style_var(imgui.STYLE_FRAME_PADDING, (14, 12))
        # imgui.push_style_color(imgui.COLOR_WINDOW_BACKGROUND, *self.window_bg)
        imgui.push_style_color(imgui.COLOR_WINDOW_BACKGROUND, 0.12, 0.12, 0.15, 0.95)

        imgui.begin(
            "Singularity",
            False,
            # imgui.WINDOW_NO_TITLE_BAR
            # | imgui.WINDOW_NO_RESIZE
            # | imgui.WINDOW_NO_MOVE
            # | imgui.WINDOW_NO_COLLAPSE,
        )

        # --- Sidebar Tabs ---
        imgui.columns(2, "main", border=False)
        imgui.set_column_width(0, 180)

        if not hasattr(self, "active_tab"):
            self.active_tab = "AIM"

        # Sidebar header
        imgui.push_style_color(imgui.COLOR_TEXT, *self.purple)
        imgui.text("SETTINGS")
        imgui.pop_style_color()
        imgui.separator()
        imgui.spacing()

        # Tab definitions with icons and descriptions
        tabs = [
            ("AIM", "Targeting & FOV"),
            ("SENSITIVITY", "Mouse Settings"),
            ("RECOIL", "Recoil Control"),
            ("CONTROLS", "Key Bindings"),
            ("TOGGLES", "Feature Toggles"),
            ("COLORS", "Visual Settings"),
            ("RESET", "Reset Settings"),
            ("ABOUT", "Information"),
        ]

        # Custom tab styling
        imgui.push_style_var(imgui.STYLE_SELECTABLE_TEXT_ALIGN, (0.0, 0.5))
        imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (0, 2))
        slider_width = (w - 160 - 10) / 2

        def create_centered_content_with_vertical_separator():
            # Create two columns in the right content area
            imgui.columns(2, "content_columns", True)  # True = show border (vertical separator)
            imgui.set_column_width(0, 90)  # Left column width
            imgui.set_column_width(1, w - 90)  # Right column width
        
        for tab_name, description in tabs:
            # Highlight active tab
            if self.active_tab == tab_name:
                imgui.push_style_color(imgui.COLOR_HEADER, *self.purple)
                imgui.push_style_color(imgui.COLOR_HEADER_HOVERED, *self.purple_hovered)
                imgui.push_style_color(imgui.COLOR_HEADER_ACTIVE, *self.purple_active)
            else:
                imgui.push_style_color(imgui.COLOR_HEADER, 0.2, 0.2, 0.2, 0.8)
                imgui.push_style_color(imgui.COLOR_HEADER_HOVERED, 0.3, 0.3, 0.3, 0.8)
                imgui.push_style_color(imgui.COLOR_HEADER_ACTIVE, 0.4, 0.4, 0.4, 0.8)
            create_centered_content_with_vertical_separator()
            # Create selectable with icon and name
            clicked, _ = imgui.selectable(f"{tab_name}", self.active_tab == tab_name)
            imgui.spacing()
            imgui.spacing()
            if clicked:
                self.active_tab = tab_name
            
            # Show description on hover
            if imgui.is_item_hovered():
                imgui.set_tooltip(description)
            
            imgui.pop_style_color(3)
        
        imgui.pop_style_var(2)
        imgui.next_column()
        # --- Right-side content ---
        imgui.push_style_color(imgui.COLOR_TEXT, 1, 1, 1, 0.9)

        # Callback system for handling changes
        def on_value_changed(attr_name, old_value, new_value, value_type="auto"):
            """Callback for when a slider value changes"""
            try:
                # Set the new value
                setattr(self.hk_self, attr_name, new_value) 
                self.hk_self.settings_manager.update(self.active_tab , attr_name, new_value)
                if(attr_name == 'INGAME_SENSITIVITY'):
                    ingame_sens = float(new_value)
                    movespeed = round(0.55 * (ingame_sens / 3.0), 3)
                    setattr(self.hk_self, 'MOVESPEED', movespeed)
                    self.hk_self.refresh_init()
                if(attr_name == 'XFOV' or attr_name == 'YFOV'):
                    self.hk_self.screen_capture.refresh_init()
                if(attr_name == 'SMOOTHNESS'):
                    self.hk_self.arduinomouse.refresh_init()
                    
                
                
            except Exception as e:
                pass
                # print(f"Error updating {attr_name}: {e}")
        
        def on_button_clicked(button_name, attr_name=None, new_value=None):
            """Callback for when a button is clicked"""
            try:
                if button_name == "keybind":
                    self.waiting_for_key = attr_name
                    # print(f"Waiting for key input for: {attr_name}")
                elif button_name == "FOV_TOGGLE":
                    # old_value = self.hk_self.FOV_TOGGLE
                    self.hk_self.FOV_TOGGLE = new_value
                    setattr(self.hk_self, attr_name, new_value)
                    self.hk_self.settings_manager.update(self.active_tab , attr_name, new_value)
                    # print(f"FOV Toggle: {old_value} -> {self.hk_self.FOV_TOGGLE}")
                elif button_name == "checkbox":
                    # Handle checkbox toggles
                    old_value = getattr(self.hk_self, attr_name, False)
                    new_value = not old_value
                    setattr(self.hk_self, attr_name, new_value)
                    self.hk_self.settings_manager.update(self.active_tab , attr_name, new_value)
                    # print(f"Checkbox {attr_name}: {old_value} -> {new_value}")
                elif button_name == "dropdown":
                    # Handle dropdown selections
                    old_value = getattr(self.hk_self, attr_name, "")
                    setattr(self.hk_self, attr_name, new_value) 
                    self.hk_self.settings_manager.update(self.active_tab , attr_name, new_value)
                    if(attr_name == 'ANIME_COLOR'):
                        self.hk_self.screen_capture.refresh_init()
                    # print(f"Dropdown {attr_name}: {old_value} -> {new_value}")
                    
            except Exception as e:
                pass
                # print(f"Error handling button click {button_name}: {e}")
        
        # Helper function for dropdown with callbacks
        def draw_dropdown(label, attr, options, current_value=None):
            if current_value is None:
                current_value = getattr(self.hk_self, attr, options[0] if options else "")
            
            imgui.text(f"{label}:")
            if imgui.begin_combo(f"##{attr}", current_value):
                for option in options:
                    selected, _ = imgui.selectable(option, current_value == option)
                    if selected:
                        on_button_clicked("dropdown", attr, option)
                imgui.end_combo()

        # Helper function for drawing sliders with callbacks
        def draw_slider_row(left_label, left_attr, left_min, left_max, is_float_left=False,
                            right_label=None, right_attr=None, right_min=None, right_max=None, is_float_right=False):
            imgui.begin_group()
            
            # Left slider
            imgui.begin_group()
            imgui.dummy(0, 7)
            imgui.text(left_label)
            imgui.push_item_width(slider_width)
            if is_float_left:
                current_value = float(getattr(self.hk_self, left_attr, 0.0))
                changed, value = imgui.slider_float(f"##{left_attr}", current_value, left_min, left_max, "%.2f")
                if changed:
                    value = round(float(value), 2)
                    on_value_changed(left_attr, current_value, value, "float")
            else:
                current_value = int(getattr(self.hk_self, left_attr, 0))
                changed, value = imgui.slider_int(f"##{left_attr}", current_value, left_min, left_max)
                if changed:
                    on_value_changed(left_attr, current_value, value, "int")
            imgui.pop_item_width()
            imgui.end_group()
            
            # Right slider
            if right_label and right_attr:
                imgui.same_line(spacing=10)
                imgui.begin_group()
                imgui.text(right_label)
                imgui.push_item_width(slider_width)
                if is_float_right:
                    current_value = float(getattr(self.hk_self, right_attr, 0.0))
                    changed, value = imgui.slider_float(f"##{right_attr}", current_value, right_min, right_max, "%.2f")
                    if changed:
                        value = round(float(value), 2)
                        on_value_changed(right_attr, current_value, value, "float")
                else:
                    current_value = int(getattr(self.hk_self, right_attr, 0))
                    changed, value = imgui.slider_int(f"##{right_attr}", current_value, right_min, right_max)
                    if changed:
                        on_value_changed(right_attr, current_value, value, "int")
                imgui.pop_item_width()
                imgui.end_group()
            
            imgui.end_group()

        # Helper function for keybind buttons with callbacks
        def draw_keybind_button(label, attr, width=120, height=35):
            current = getattr(self.hk_self, attr)
            cap_hint = "  [press any key]" if self.waiting_for_key == attr else ""
            if imgui.button(f"{label}: {self.desc(current)}{cap_hint}", width, height):
                on_button_clicked("keybind", attr)
        
        # Helper function for checkboxes with callbacks
        def draw_checkbox(label, attr):
            current_value = getattr(self.hk_self, attr, False)
            changed, value = imgui.checkbox(label, current_value)
            if changed:
                on_button_clicked("checkbox", attr)
            return changed, value

        def custom_separator():
            imgui.push_style_color(imgui.COLOR_SEPARATOR, 0.5, 0.5, 0.5, 1.0)
            imgui.dummy(0, 2)  # Small spacing
            draw_list = imgui.get_window_draw_list()
            pos = imgui.get_cursor_screen_pos()
            content_width = imgui.get_content_region_available_width()
            draw_list.add_line(pos[0], pos[1], pos[0] + content_width, pos[1], imgui.get_color_u32_rgba(0.5, 0.5, 0.5, 1.0), 1.0)
            imgui.pop_style_color()
            


        if self.active_tab == "AIM":
            imgui.spacing()
            imgui.text("Aim Settings") 
            custom_separator()
            imgui.spacing()
            
            draw_slider_row("XFOV", "XFOV", 30, 300, False,
                           "YFOV", "YFOV", 30, 300, False)
            draw_slider_row("Smoothness", "SMOOTHNESS", 1, 20, False,
                           "Head Offset", "HEAD_OFFSET", 0.0, 1.0, True)
            draw_slider_row("Aim Smoothing", "AIM_SMOOTHING_FACTOR", 0.01, 1.0, True)
            
            
        elif self.active_tab == "SENSITIVITY":
            imgui.spacing()
            imgui.text("Sensitivity Settings")
            custom_separator()
            imgui.spacing()
            
            draw_slider_row("Ingame Sensitivity", "INGAME_SENSITIVITY", 0.1, 10, True,
                           "Move Speed", "MOVESPEED", 0.1, 2.0, True)
            draw_slider_row("Y Speed Multiplier", "Y_SPEED_MULTIPLIER", 0.1, 3.0, True)
            
        elif self.active_tab == "RECOIL":
            imgui.spacing()
            imgui.text("Recoil Settings")
            custom_separator()
            imgui.spacing()
            
            # Recoil mode dropdown using callback system
            draw_dropdown("Recoil Mode", "RECOIL_MODE", ['offset', 'move'])
            
            draw_slider_row("Recoil X", "RECOIL_X", -50, 50, False,
                           "Recoil Y", "RECOIL_Y", -50, 50, False)
            draw_slider_row("Max Offset", "MAX_OFFSET", 10, 500, False,
                           "Recoil Recover", "RECOIL_RECOVER", 0, 100, False)
            
        elif self.active_tab == "CONTROLS":
            imgui.spacing()
            imgui.text("Control Settings")
            custom_separator()
            imgui.spacing()
            
            btn_width = slider_width
            
            draw_keybind_button("Aim Assist", "AIM_ASSIST_KEY", btn_width)
            imgui.same_line(spacing=10)
            draw_keybind_button("Flick Key", "FLICK_KEY", btn_width)
            
        elif self.active_tab == "TOGGLES":
            imgui.spacing()
            imgui.text("Toggle Settings")
            custom_separator()
            imgui.spacing()
            
            btn_width = slider_width
            
            draw_keybind_button("Cheat Toggle", "CHEAT_TOGGLE_KEY", btn_width)
            imgui.same_line(spacing=10)
            draw_keybind_button("UI Toggle", "IMGUI_TOGGLE_KEY", btn_width)
            
            draw_keybind_button("Trigger Key", "TRIGGER_KEY", btn_width)
            
            imgui.spacing()
            imgui.begin_group()
            draw_checkbox("FOV Toggle", "FOV_TOGGLE")
            imgui.same_line(spacing=10)
            draw_checkbox("FPS Toggle", "FPS_TOGGLE")
            imgui.end_group()
             
                
        elif self.active_tab == "COLORS":
            imgui.spacing()
            imgui.text("Color & Visual Settings")
            custom_separator()
            imgui.spacing()
            
            # Color selection using callback system
            draw_dropdown("Anime Color", "ANIME_COLOR", ['strinova_blackish_purple', 'strinova_red', 'strinova_purple'])
            
            imgui.spacing()
            
            # Visual toggles using callback system
            imgui.begin_group()
            draw_dropdown("Box Color", "BOX_COLOR", self.color_list)
            imgui.same_line(spacing=10)
            draw_checkbox("Box Enabled", "BOX_ENABLED")
            imgui.end_group()

            imgui.begin_group()
            draw_dropdown("Head Color", "HEAD_COLOR", self.color_list)
            imgui.same_line(spacing=10)
            draw_checkbox("Head Enabled", "HEAD_ENABLED")
            imgui.end_group()

            imgui.begin_group()
            draw_dropdown("Line Color", "LINE_COLOR", self.color_list)
            imgui.same_line(spacing=10)
            draw_checkbox("Line Enabled", "LINE_ENABLED")
            imgui.end_group()

 
        elif self.active_tab == "RESET":
            imgui.spacing()
            imgui.text("Reset Settings")
            custom_separator()
            imgui.spacing()
            
            if imgui.button("Reset to Default"):
                self.show_reset_confirmation = True
                
        elif self.active_tab == "ABOUT":
            imgui.spacing()
            imgui.text("About Singularity")
            custom_separator()
            imgui.spacing()
            
            imgui.text(f"Version: {STRENOVA}")
            imgui.text("Developer: Nobita") 
            
            imgui.spacing()
            
            custom_separator()
            imgui.spacing()
            
            # Commercial Use Warning
            imgui.push_style_color(imgui.COLOR_TEXT, 1.0, 0.8, 0.0, 1.0)  # Orange color
            imgui.text("COMMERCIAL USE NOTICE:")
            imgui.pop_style_color()
            
            imgui.text_wrapped("This software is for personal use only. Commercial use,")
            imgui.text_wrapped("resale, redistribution, or any form of monetization")
            imgui.text_wrapped("without explicit written permission from the developer")
            imgui.text_wrapped("is strictly prohibited and may result in legal action.")
            imgui.text_wrapped("For commercial licensing inquiries, contact the developer.")
            
            imgui.spacing()
            imgui.text("Discord:")
            imgui.same_line()
            if imgui.small_button(DISCORD):
                webbrowser.open(DISCORD)
        
        # Handle key capture for all tabs
        if self.waiting_for_key:
            vk_code = self.detect_winapi_key()
            if vk_code is not None:
                try:
                    hex_code = f"0x{vk_code:02X}"
                    old_value = getattr(self.hk_self, self.waiting_for_key, "")
                    setattr(self.hk_self, self.waiting_for_key, hex_code)
                    # print(f"Key captured for {self.waiting_for_key}: {old_value} -> {hex_code}") 
                    self.hk_self.settings_manager.update(self.active_tab , self.waiting_for_key, hex_code)
                    
                    # You can also trigger the callback system here if needed
                    # on_value_changed(self.waiting_for_key, old_value, hex_code, "key")
                    
                except Exception as e:
                    pass
                    # print(f"Error capturing key for {self.waiting_for_key}: {e}")
                finally:
                    self.waiting_for_key = None
        
        # Visual hint when capturing any keybind
        if self.waiting_for_key:
            imgui.spacing()
            imgui.text_colored("Listening... press any key to bind", 1.0, 1.0, 0.4, 1.0)

        imgui.pop_style_color()  # pop COLOR_TEXT
        imgui.columns(1)
        
        # Reset confirmation dialog
        if self.show_reset_confirmation:
            imgui.open_popup("Reset Confirmation")
            
        if imgui.begin_popup_modal("Reset Confirmation", True)[0]:
            imgui.text("Are you sure you want to reset all settings to default?")
            imgui.text("This action cannot be undone.")
            imgui.spacing()
            
            if imgui.button("Yes, Reset", 100, 30):
                self.hk_self.settings_manager.reset_to_defaults(confirm=True)
                self.show_reset_confirmation = False
                imgui.close_current_popup()
                self.loop =False
                
            imgui.same_line()
            if imgui.button("Cancel", 100, 30):
                self.show_reset_confirmation = False
                imgui.close_current_popup()
                
            imgui.end_popup()
        
        imgui.end()
        imgui.pop_style_color()  # pop COLOR_WINDOW_BACKGROUND
        imgui.pop_style_var(3)

    def detect_winapi_key(self):
        # Skip certain keys that shouldn't be captured
        skip_keys = [0x01, 0x02, 0x04, 0x05, 0x06]  # Mouse buttons that might interfere
        
        for vk_code in range(0x01, 0xFE):  # Valid virtual key codes
            # if vk_code in skip_keys:
            #     continue
                
            # Check if key is currently pressed (high-order bit set)
            if GetAsyncKeyState(vk_code) & 0x8000:
                # Add small delay to prevent multiple captures
                import time
                time.sleep(0.1)
                return vk_code
        return None

    def get_virtual_key_info_by_code(self, key_code: int): 
        hex_code = f"0x{key_code:02X}"  # Convert int to hex string like '0xFB'
        for item in virtual_keys:
            if item["Value"].upper() == hex_code.upper():
                return item  # or return (item["Constant"], item["Description"])
        return None


# Example usage (in your project):
# from ImGuI.overlay import ImGuiOverlay
# overlay = ImGuiOverlay()
# overlay.init_window()
# overlay.Hide_from_taskbar()
# overlay.render_loop()
