"""
Screenshot Manager for Work Time Tracker
"""

import os
import time
from datetime import datetime
from typing import List
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication
from PIL import ImageGrab
import logging

class ScreenshotManager(QThread):
    """Manages automatic screenshot capture"""
    
    screenshot_taken = pyqtSignal(str)  # Signal emitted when screenshot is taken
    
    def __init__(self, interval_minutes: int = 5):
        """Initialize screenshot manager"""
        super().__init__()
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.is_running = False
        self.screenshots_dir = "screenshots"
        self.screenshots = []
        self.logger = logging.getLogger(__name__)
        
        # Create screenshots directory
        os.makedirs(self.screenshots_dir, exist_ok=True)
    
    def start_capture(self):
        """Start automatic screenshot capture"""
        self.is_running = True
        self.start()
        self.logger.info(f"Started screenshot capture every {self.interval_minutes} minutes")
    
    def stop_capture(self):
        """Stop automatic screenshot capture"""
        self.is_running = False
        self.logger.info("Stopped screenshot capture")
    
    def run(self):
        """Main capture loop"""
        while self.is_running:
            try:
                # Take screenshot
                screenshot_path = self._take_screenshot()
                if screenshot_path:
                    self.screenshots.append(screenshot_path)
                    self.screenshot_taken.emit(screenshot_path)
                
                # Wait for next interval
                time.sleep(self.interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in screenshot capture: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _take_screenshot(self) -> str:
        """Take a screenshot and save it"""
        try:
            # Get screen dimensions
            app = QApplication.instance()
            screen = app.primaryScreen()
            geometry = screen.geometry()
            
            # Take screenshot using PIL
            screenshot = ImageGrab.grab()
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            
            # Save screenshot
            screenshot.save(filepath, "PNG")
            
            self.logger.info(f"Screenshot saved: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return ""
    
    def get_screenshots(self) -> List[str]:
        """Get list of screenshot paths"""
        return self.screenshots.copy()
    
    def clear_screenshots(self):
        """Clear screenshot list"""
        self.screenshots.clear()
    
    def set_interval(self, minutes: int):
        """Set screenshot interval in minutes"""
        self.interval_minutes = minutes
        self.interval_seconds = minutes * 60
        self.logger.info(f"Screenshot interval set to {minutes} minutes") 