"""
Time Tracker for Work Time Tracker
"""

import time
from datetime import datetime, timedelta
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import logging

class TimeTracker(QObject):
    """Manages time tracking for tasks"""
    
    time_updated = pyqtSignal(str)  # Signal emitted when time updates
    session_completed = pyqtSignal(int, list)  # Signal emitted when session ends (seconds, screenshots)
    
    def __init__(self):
        """Initialize time tracker"""
        super().__init__()
        self.start_time: Optional[datetime] = None
        self.current_task_id: Optional[str] = None
        self.current_task_title: Optional[str] = None
        self.is_tracking = False
        self.total_seconds = 0
        self.previous_time_minutes = 0  # Previous time spent on task in minutes
        self.screenshots = []
        
        # Timer for updating display
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.setInterval(1000)  # Update every second
        
        self.logger = logging.getLogger(__name__)
    
    def start_tracking(self, task_id: str, task_title: str, previous_time_minutes: int = 0):
        """Start tracking time for a task"""
        if self.is_tracking:
            self.stop_tracking()
        
        self.start_time = datetime.now()
        self.current_task_id = task_id
        self.current_task_title = task_title
        self.is_tracking = True
        self.total_seconds = 0
        self.previous_time_minutes = previous_time_minutes
        self.screenshots.clear()
        
        self.update_timer.start()
        
        self.logger.info(f"Started tracking task: {task_title} (ID: {task_id}) with previous time: {previous_time_minutes} minutes")
    
    def stop_tracking(self):
        """Stop tracking time"""
        if not self.is_tracking:
            return
        
        self.is_tracking = False
        self.update_timer.stop()
        
        # Calculate final time
        if self.start_time:
            end_time = datetime.now()
            duration = end_time - self.start_time
            self.total_seconds = int(duration.total_seconds())
        
        # Emit completion signal
        self.session_completed.emit(self.total_seconds, self.screenshots.copy())
        
        self.logger.info(f"Stopped tracking task: {self.current_task_title}")
        self.logger.info(f"Total time: {self._format_time(self.total_seconds)}")
        
        # Reset state
        self.start_time = None
        self.current_task_id = None
        self.current_task_title = None
    
    def add_screenshot(self, screenshot_path: str):
        """Add screenshot to current session"""
        if self.is_tracking:
            self.screenshots.append(screenshot_path)
    
    def _update_display(self):
        """Update time display"""
        if not self.is_tracking or not self.start_time:
            return
        
        current_time = datetime.now()
        duration = current_time - self.start_time
        current_session_seconds = int(duration.total_seconds())
        
        # Calculate total time: previous time + current session time
        total_seconds = (self.previous_time_minutes * 60) + current_session_seconds
        
        # Emit time update signal
        formatted_time = self._format_time(total_seconds)
        self.time_updated.emit(formatted_time)
    
    def _format_time(self, seconds: int) -> str:
        """Format seconds into HH:MM:SS"""
        hours = int(seconds // 3600)    
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def get_current_task(self) -> Optional[dict]:
        """Get current task information"""
        if not self.is_tracking:
            return None
        
        return {
            'id': self.current_task_id,
            'title': self.current_task_title,
            'start_time': self.start_time,
            'elapsed_seconds': self.total_seconds if not self.start_time else int((datetime.now() - self.start_time).total_seconds())
        }
    
    def is_active(self) -> bool:
        """Check if tracking is active"""
        return self.is_tracking
    
    def get_elapsed_time(self) -> int:
        """Get elapsed time in seconds"""
        if not self.is_tracking or not self.start_time:
            return 0
        
        duration = datetime.now() - self.start_time
        current_session_seconds = int(duration.total_seconds())
        
        # Return total time: previous time + current session time
        return (self.previous_time_minutes * 60) + current_session_seconds 