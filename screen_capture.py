"""
Screen capture and processing module for Colorbot
Based on Unibot's approach - simplified and direct
"""

import time
import cv2
import numpy as np
import bettercam
import threading
from pyautogui import size
from util.setting import get_color_bounds

class ScreenCapture:
    def __init__(self,NeoRant, settings, debug_enabled=False):
        # Processing variables
        self.thresh = None
        self.target = None
        self.trigger = False
        self.head_box = None
        self.target_diff = None
        self.head_position = None
        self.closest_contour = None

        self.NeoRant = NeoRant 
        self.cam = bettercam.create(output_color="BGR")

        # Screen setup 
        screen_size = size()
        self.screen = (screen_size.width, screen_size.height)
        self.screen_center = (self.screen[0] // 2, self.screen[1] // 2)
        
        # FOV setup from config 
        self.refresh_init()

        # Setup debug display 
        self.debug_enabled = debug_enabled  # Use parameter from main class
        self.display_mode = 'game'  # 'game' or 'mask'
        self.window_name = 'Colorbot'
        self.window_resolution = (
            self.screen[0] // 2,
            self.screen[1] // 2
        ) 
        if self.debug_enabled: cv2.namedWindow(self.window_name)

        # FPS tracking (lightweight)
        self._fps_last_time = time.time()
        self._fps_frames = 0
        self._fps_interval = 0.5  # seconds
        self.fps = 0.0
        self.lock = threading.Lock()
        threading.Thread(target=self.get_target, daemon=True).start()
  

    def refresh_init(self):
        self.LOWER_COLOR, self.UPPER_COLOR = get_color_bounds(self.NeoRant.ANIME_COLOR) 
        self.fov = (self.NeoRant.XFOV, self.NeoRant.YFOV)
        self.fov_center = (self.fov[0] // 2, self.fov[1] // 2)
        self.fov_region = (
            self.screen_center[0] - self.fov_center[0],
            self.screen_center[1] - self.fov_center[1],
            self.screen_center[0] + self.fov_center[0],
            self.screen_center[1] + self.fov_center[1]
        )
        self.img = np.zeros((self.fov[1], self.fov[0], 3), np.uint8)
        
    def find_head_position(self, rect_x, rect_y, rect_w, rect_h, image):
        """Find head position by dividing target into 3 vertical parts and scanning horizontally"""
        try:
            # Divide target vertically into 3 parts: head (top 1/3), body (middle 1/3), leg (bottom 1/3)
            head_height = rect_h // 3
            head_y_start = rect_y
            head_y_end = rect_y + head_height
            
            # Divide head area horizontally into 3 parts: left, center, right
            head_section_width = rect_w // 3
            scan_positions = [
                rect_x + head_section_width // 2,                    # Left section center
                rect_x + head_section_width + head_section_width // 2,  # Center section center
                rect_x + 2 * head_section_width + head_section_width // 2  # Right section center
            ]
            
            best_head_x = None
            best_head_y = None
            max_color_pixels = 0
            
            # Check each horizontal position in head area
            for scan_x in scan_positions:
                if scan_x >= image.shape[1]:
                    continue
                    
                # Create detection box at this position (like crosshair detection)
                box_size = 12
                half_box = box_size // 2
                
                start_x = max(0, scan_x - half_box)
                start_y = max(0, head_y_start)
                end_x = min(scan_x + half_box, image.shape[1])
                end_y = min(head_y_end, image.shape[0])
                
                # Extract the box area
                cropped_image = image[start_y:end_y, start_x:end_x]
                if cropped_image is None or cropped_image.size == 0:
                    continue
                    
                # Convert to HSV and check for target color (like crosshair detection)
                screen_2 = np.array(cropped_image)
                hsvx = cv2.cvtColor(screen_2, cv2.COLOR_BGR2HSV)
                maskx = cv2.inRange(hsvx, np.array(self.LOWER_COLOR), np.array(self.UPPER_COLOR))
                color_pixels = cv2.countNonZero(maskx)
                
                # If we found color pixels, this might be the head
                if color_pixels > max_color_pixels and color_pixels > 3:
                    max_color_pixels = color_pixels
                    
                    # Find center of mass of the color pixels
                    moments = cv2.moments(maskx)
                    if moments["m00"] != 0:
                        local_cx = int(moments["m10"] / moments["m00"])
                        local_cy = int(moments["m01"] / moments["m00"])
                        
                        # Convert back to full image coordinates
                        best_head_x = start_x + local_cx
                        best_head_y = start_y + local_cy
                    else:
                        # Fallback to box center
                        best_head_x = scan_x
                        best_head_y = (start_y + end_y) // 2
                    
                    # Store head bounding box for drawing
                    head_box_size = max(8, min(rect_w // 4, head_height // 2))
                    self.head_box = (
                        best_head_x - head_box_size // 2,
                        best_head_y - head_box_size // 2,
                        head_box_size,
                        head_box_size
                    )
            
            return best_head_x, best_head_y
            
        except Exception as e:
            return None, None
     
    def get_target(self):
        """Capture fresh image and calculate target in one call"""
        while True:
            with self.lock: 
                # Get fresh image
                image = self.cam.grab((
                    self.fov_region[0],
                    self.fov_region[1] - int(self.NeoRant.recoil_offset),
                    self.fov_region[2],
                    self.fov_region[3] - int(self.NeoRant.recoil_offset)
                ))
                if image  is None:
                    continue

                self.img = np.array(image)  
                # Reset variables
                self.target = None
                self.target_diff = None
                # Don't reset head_position here - let it persist until new head is found
                self.trigger = False
                self.closest_contour = None

                # Convert the screenshot to HSV color space for color detection
                hsv = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)

                # Create a mask to identify pixels within the specified color range
                mask = cv2.inRange(hsv, np.array(self.LOWER_COLOR), np.array(self.UPPER_COLOR))

                # Apply morphological dilation to increase the size of the detected color blobs
                kernel = np.ones((3, 3), np.uint8)  # Using 3x3 kernel like our config
                dilated = cv2.dilate(mask, kernel, iterations=2)  # Reduced from 5 to 2 iterations

                # Apply thresholding to convert the mask into a binary image
                self.thresh = cv2.threshold(dilated, 60, 255, cv2.THRESH_BINARY)[1]

                # Find contours of the detected color blobs
                contours, _ = cv2.findContours(self.thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

                # Identify the closest target contour
                if len(contours) != 0:
                    min_distance = float('inf')
                    for contour in contours:
                        # Filter contours by area to avoid overly large detections
                        contour_area = cv2.contourArea(contour)
                        if contour_area < 50 or contour_area > 5000:  # Skip too small or too large contours
                            continue
                            
                        # Make a bounding rectangle for the target
                        rect_x, rect_y, rect_w, rect_h = cv2.boundingRect(contour)

                        # Calculate center point with aim height adjustment
                        center_x = rect_x + rect_w // 2
                        center_y = rect_y + int(rect_h * self.NeoRant.HEAD_OFFSET)
                        x_diff = center_x - self.fov_center[0]
                        y_diff = center_y - self.fov_center[1]

                        # Calculate distance from FOV center
                        # distance = np.sqrt(center_x**2 + center_y**2)
                        distance = np.sqrt((center_x - self.fov_center[0])**2 +(center_y - self.fov_center[1])**2)

                        if distance < min_distance:
                            min_distance = distance
                            self.closest_contour = contour
                            
                            # Find head position using the new method
                            head_x, head_y = self.find_head_position(rect_x, rect_y, rect_w, rect_h, self.img)
                            
                            # Use head position if found, otherwise use body center
                            if head_x is not None and head_y is not None:
                                # Validate head is in top part of target (not below center)
                                body_center_y = rect_y + rect_h // 2
                                if head_y < body_center_y:  # Head must be above body center
                                    self.target = ((center_x - self.fov_center[0]), (center_y - self.fov_center[1]))
                                    self.head_position = (head_x- self.fov_center[0], head_y- self.fov_center[1])
                                    self.target_diff = (x_diff, y_diff)
                                else:
                                    # Head detected below center, use body center instead
                                    self.target = ((center_x - self.fov_center[0]), (center_y - self.fov_center[1]))
                                    self.target_diff = (x_diff, y_diff)
                                    self.head_position = None
                                    self.head_box = None
                            else:
                                # No head found, use body center
                                self.target = ((center_x - self.fov_center[0]), (center_y - self.fov_center[1]))
                                self.target_diff = (x_diff, y_diff)
                                self.head_position = None
                                self.head_box = None
                    # Additional color detection check at crosshair position (like VALORANT version)
                    def check_color_at_crosshair():
                        # Create a small box around crosshair to check for color
                        
                        height, width = image.shape[:2]
                        center_x, center_y = width // 2, height // 2
                        box_size = 6
                        half_box = box_size // 2
                        start_x = max(0, center_x - half_box)
                        start_y = max(0, center_y - half_box)
                        end_x = min(center_x + half_box, width)
                        end_y = min(center_y + half_box, height)
                        cropped_image = image[start_y:end_y, start_x:end_x]
                        if cropped_image is None or cropped_image.size == 0:
                            print("Error: Received an empty image.")
                            return
                        screen_2 = np.array(cropped_image)
                        hsvx = cv2.cvtColor(screen_2, cv2.COLOR_RGB2HSV)
                        maskx = cv2.inRange(
                            hsvx, np.array(self.LOWER_COLOR), np.array(self.UPPER_COLOR)
                        )   
                        return cv2.countNonZero(maskx) > 0
                    
                    if (
                        self.closest_contour is not None and
                        # Check if crosshair is inside the closest target
                        (cv2.pointPolygonTest(
                            self.closest_contour, (self.fov_center[0], self.fov_center[1]), False) >= 0 and 
                        # Eliminate a lot of false positives by also checking pixels near the crosshair.
                        cv2.pointPolygonTest(
                            self.closest_contour, (self.fov_center[0] + 5, self.fov_center[1]), False) >= 0 and
                        cv2.pointPolygonTest(
                            self.closest_contour, (self.fov_center[0] - 5, self.fov_center[1]), False) >= 0 and
                        cv2.pointPolygonTest(
                            self.closest_contour, (self.fov_center[0], self.fov_center[1] + 5), False) >= 0 and
                        cv2.pointPolygonTest(
                            self.closest_contour, (self.fov_center[0], self.fov_center[1] - 5), False) >= 0 ) or
                         
                        check_color_at_crosshair()
                    ):
                        self.trigger = True
                else:
                    # No contours found, reset head position
                    self.head_position = None
                
                 
                # Show debug window if enabled
                if self.debug_enabled:
                    self.run_debug_window()
                
                # Update FPS counters (very low overhead)
                self._fps_frames += 1
                now = time.time()
                elapsed = now - self._fps_last_time
                if elapsed >= self._fps_interval:
                    self.fps = self._fps_frames / elapsed
                    self._fps_frames = 0
                    self._fps_last_time = now
                    # try:
                    #     cv2.setWindowTitle(self.window_name, f"Colorbot  |  FPS: {self.fps:.1f}")
                    # except Exception:
                    #     pass
            
            # Small delay to prevent excessive CPU usage and reduce race conditions
            time.sleep(0.001)  # 1ms delay

    def run_debug_window(self):
        """Run debug window - simplified like Unibot"""
        if self.display_mode == 'game':
            debug_img = self.img
        else:
            debug_img = self.thresh
            debug_img = cv2.cvtColor(debug_img, cv2.COLOR_GRAY2BGR)

        # Draw line to target
        if self.target is not None:
            debug_img = cv2.line(debug_img, self.fov_center, 
                               (self.target[0] + self.fov_center[0], self.target[1] + self.fov_center[1]), 
                               (0, 255, 0), 2)

        # Draw rectangle around target
        if self.closest_contour is not None:
            x, y, w, h = cv2.boundingRect(self.closest_contour)
            debug_img = cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 2)

        # Draw FOV border
        debug_img = cv2.rectangle(debug_img, (0, 0), (self.fov[0], self.fov[1]), (0, 255, 0), 2)

        # Draw FPS overlay text (top-left)
        # try:
        #     cv2.putText(
        #         debug_img,
        #         f"FPS: {self.fps:.1f}",
        #         (8, 20),
        #         cv2.FONT_HERSHEY_SIMPLEX,
        #         0.6,
        #         (255, 255, 255),
        #         1,
        #         cv2.LINE_AA,
        #     )
        # except Exception:
        #     pass

        cv2.imshow(self.window_name, debug_img)
        cv2.waitKey(1)
        
    def get_current_frame(self):
        """Get current captured frame"""
        return self.img
        
    def get_current_mask(self):
        """Get current color mask"""
        return self.thresh