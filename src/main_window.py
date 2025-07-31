"""
Main Window for Work Time Tracker
"""

import sys
import logging
from typing import List, Dict
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QListWidget, QListWidgetItem, QLabel,
    QTextEdit, QMessageBox, QProgressBar, QFrame,
    QSplitter, QGroupBox, QGridLayout, QComboBox,
    QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

from .notion_client import NotionClient
from .time_tracker import TimeTracker
from .screenshot_manager import ScreenshotManager

class LoadingDialog(QDialog):
    """Dialog for showing loading/uploading status"""
    def __init__(self, parent=None, message="Loading..."):
        super().__init__(parent)
        self.setWindowTitle("Status")
        self.setFixedSize(300, 100)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        layout = QVBoxLayout(self)
        
        # Message label
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333333;")
        layout.addWidget(self.message_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)
        
        # Center the dialog on parent
        if parent:
            self.move(parent.geometry().center() - self.rect().center())
    
    def set_message(self, message: str):
        """Update the message text"""
        self.message_label.setText(message)

class TaskLoaderThread(QThread):
    """Thread for loading tasks from Notion"""
    tasks_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, notion_client: NotionClient):
        super().__init__()
        self.notion_client = notion_client
    
    def run(self):
        try:
            tasks = self.notion_client.get_tasks()
            self.tasks_loaded.emit(tasks)
        except Exception as e:
            self.error_occurred.emit(str(e))

class TaskUpdateThread(QThread):
    """Thread for updating task time in Notion"""
    update_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, notion_client: NotionClient, task_id: str, time_spent: int, screenshots: List[str]):
        super().__init__()
        self.notion_client = notion_client
        self.task_id = task_id
        self.time_spent = time_spent
        self.screenshots = screenshots
    
    def run(self):
        try:
            self.notion_client.update_task_time(self.task_id, self.time_spent, self.screenshots)
            self.update_completed.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setup_logging()
        self.init_ui()
        self.init_components()
        self.setup_connections()
        self.load_tasks()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('work_tracker.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Work Time Tracker")
        self.setGeometry(100, 100, 1000, 700)
        
        # Set modern style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QListWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eeeeee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
        """)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Task list
        self.create_task_panel(splitter)
        
        # Right panel - Timer and controls
        self.create_timer_panel(splitter)
        
        # Set splitter proportions
        splitter.setSizes([400, 600])
    
    def create_task_panel(self, parent):
        """Create task list panel"""
        task_group = QGroupBox("Tasks from Notion")
        parent.addWidget(task_group)
        
        layout = QVBoxLayout(task_group)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Tasks")
        self.refresh_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_BrowserReload))
        refresh_layout.addWidget(self.refresh_btn)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # Task list
        self.task_list = QListWidget()
        self.task_list.setMinimumHeight(300)
        layout.addWidget(self.task_list)
        
        # Task info
        self.task_info = QTextEdit()
        self.task_info.setMaximumHeight(100)
        self.task_info.setReadOnly(True)
        layout.addWidget(self.task_info)
    
    def create_timer_panel(self, parent):
        """Create timer and control panel"""
        timer_group = QGroupBox("Time Tracking")
        parent.addWidget(timer_group)
        
        layout = QVBoxLayout(timer_group)
        
        # Current task display
        current_task_layout = QGridLayout()
        
        current_task_layout.addWidget(QLabel("Current Task:"), 0, 0)
        self.current_task_label = QLabel("No task selected")
        self.current_task_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        current_task_layout.addWidget(self.current_task_label, 0, 1)
        
        current_task_layout.addWidget(QLabel("Elapsed Time:"), 1, 0)
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333333;")
        current_task_layout.addWidget(self.time_label, 1, 1)
        
        layout.addLayout(current_task_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Work")
        self.start_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay))
        self.start_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Work")
        self.stop_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaStop))
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        layout.addLayout(button_layout)
        
        # Screenshot info (hidden from user)
        self.screenshot_interval = 5  # Default 5 minutes
        
        # Status and log
        status_group = QGroupBox("Status & Log")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666666;")
        status_layout.addWidget(self.status_label)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        status_layout.addWidget(self.log_text)
        
        layout.addWidget(status_group)
        
        layout.addStretch()
    
    def init_components(self):
        """Initialize application components"""
        try:
            self.notion_client = NotionClient()
            self.time_tracker = TimeTracker()
            self.screenshot_manager = ScreenshotManager()
            
            # Test connection
            if not self.notion_client.test_connection():
                QMessageBox.warning(self, "Connection Error", 
                                  "Failed to connect to Notion. Please check your credentials.")
            
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", 
                               f"Failed to initialize application: {str(e)}")
            self.logger.error(f"Initialization error: {e}")
    
    def setup_connections(self):
        """Setup signal connections"""
        # Button connections
        self.refresh_btn.clicked.connect(self.load_tasks)
        self.start_btn.clicked.connect(self.start_tracking)
        self.stop_btn.clicked.connect(self.stop_tracking)
        
        # Task list connections
        self.task_list.itemSelectionChanged.connect(self.on_task_selected)
        
        # Timer connections
        self.time_tracker.time_updated.connect(self.update_time_display)
        self.time_tracker.session_completed.connect(self.on_session_completed)
        
        # Screenshot connections
        self.screenshot_manager.screenshot_taken.connect(self.on_screenshot_taken)
    
    def load_tasks(self):
        """Load tasks from Notion"""
        self.status_label.setText("Loading tasks from Notion...")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Loading...")
        
        # Show loading dialog
        self.loading_dialog = LoadingDialog(self, "Loading tasks from Notion...")
        self.loading_dialog.show()
        
        # Create and start loader thread
        self.loader_thread = TaskLoaderThread(self.notion_client)
        self.loader_thread.tasks_loaded.connect(self.on_tasks_loaded)
        self.loader_thread.error_occurred.connect(self.on_tasks_error)
        self.loader_thread.start()
    
    def on_tasks_loaded(self, tasks: List[Dict]):
        """Handle loaded tasks"""
        # Close loading dialog
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.close()
            self.loading_dialog = None
        
        self.task_list.clear()
        self.tasks = tasks
        
        for task in tasks:
            item = QListWidgetItem()
            assignee_text = f" - {task['assignee']}" if task['assignee'] else ""
            item.setText(f"{task['title']}{assignee_text}")
            item.setData(Qt.ItemDataRole.UserRole, task)
            self.task_list.addItem(item)
        
        self.status_label.setText(f"Loaded {len(tasks)} tasks")
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh Tasks")
        self.log_message(f"Loaded {len(tasks)} tasks from Notion")
    
    def on_tasks_error(self, error: str):
        """Handle task loading error"""
        # Close loading dialog
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.close()
            self.loading_dialog = None
        
        self.status_label.setText("Error loading tasks")
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh Tasks")
        QMessageBox.warning(self, "Error", f"Failed to load tasks: {error}")
        self.log_message(f"Error loading tasks: {error}")
    
    def on_task_selected(self):
        """Handle task selection"""
        current_item = self.task_list.currentItem()
        if current_item:
            task = current_item.data(Qt.ItemDataRole.UserRole)
            self.selected_task = task
            info_text = f"任务名称: {task['title']}\n"
            info_text += f"负责人: {task['assignee']}\n"
            info_text += f"已用时间: {self._format_time_for_display(task['time_spent'])}\n"
            info_text += f"截止日期: {task['due_date']}\n"
            self.task_info.setText(info_text)
            # Enable start button
            self.start_btn.setEnabled(True)
            self.current_task_label.setText(task['title'])
            
            # Display total time spent on this task as elapsed time
            # This ensures Elapsed Time matches the "已用时间" when selecting a task
            total_minutes = task.get('time_spent', 0)
            total_seconds = total_minutes * 60
            formatted_time = self._format_time(total_seconds)
            self.time_label.setText(formatted_time)
        else:
            self.selected_task = None
            self.start_btn.setEnabled(False)
            self.current_task_label.setText("No task selected")
            self.task_info.clear()
            self.time_label.setText("00:00:00")
    
    def start_tracking(self):
        """Start time tracking"""
        if not self.selected_task:
            return
        
        # Get previous time spent on this task (in minutes)
        previous_time_minutes = self.selected_task.get('time_spent', 0)
        
        # Start time tracking with previous time
        self.time_tracker.start_tracking(
            self.selected_task['id'], 
            self.selected_task['title'],
            previous_time_minutes
        )
        
        # Start screenshot capture with default 5-minute interval
        self.screenshot_manager.set_interval(self.screenshot_interval)
        self.screenshot_manager.start_capture()
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.task_list.setEnabled(False)
        
        # Display initial total time (previous time + 0 seconds current session)
        # This ensures Elapsed Time matches the "已用时间" when starting
        total_seconds = previous_time_minutes * 60
        self.time_label.setText(self._format_time(total_seconds))
        
        self.status_label.setText("Tracking active")
        self.log_message(f"Started tracking: {self.selected_task['title']}")
        
        # Minimize the main window
        self.showMinimized()
    
    def stop_tracking(self):
        """Stop time tracking"""
        # Stop time tracking
        self.time_tracker.stop_tracking()
        
        # Stop screenshot capture
        self.screenshot_manager.stop_capture()
        
        # Update UI immediately
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.task_list.setEnabled(True)
        
        # Show uploading dialog
        self.uploading_dialog = LoadingDialog(self, "Uploading to Notion...")
        self.uploading_dialog.show()
        
        self.status_label.setText("Updating task in Notion...")
        
        # Update time display to show final total time
        if self.selected_task:
            # Get updated time from the task (it should have been updated by the time tracker)
            # This ensures Elapsed Time shows the updated total time after stopping
            total_minutes = self.selected_task.get('time_spent', 0)
            total_seconds = total_minutes * 60
            self.time_label.setText(self._format_time(total_seconds))
        
        self.log_message("Stopped tracking")
    
    def update_time_display(self, time_str: str):
        """Update time display with total time (previous + current session)"""
        # time_str from TimeTracker already includes previous time + current session
        self.time_label.setText(time_str)
    
    def on_session_completed(self, seconds: int, screenshots: List[str]):
        """Handle session completion"""
        # Update the selected task's time_spent to reflect the new total
        if self.selected_task:
            previous_time_minutes = self.selected_task.get('time_spent', 0)
            new_session_minutes = round(seconds / 60, 2)
            self.selected_task['time_spent'] = previous_time_minutes + new_session_minutes
             # Update the task_list to reflect the new time_spent for the selected task
            for i in range(self.task_list.count()):
                item = self.task_list.item(i)
                task = item.data(Qt.ItemDataRole.UserRole)
                if task and task.get('id') == self.selected_task.get('id'):
                    task['time_spent'] = self.selected_task['time_spent']
                    item.setData(Qt.ItemDataRole.UserRole, task)
                    break
            # Update the time display to show the new total time
            total_seconds = self.selected_task['time_spent'] * 60
            self.time_label.setText(self._format_time(total_seconds))
            
                    # Start background thread to update Notion
        self.update_thread = TaskUpdateThread(
            self.notion_client,
            self.selected_task['id'],
            seconds,
            screenshots
        )
        self.update_thread.update_completed.connect(self.on_update_completed)
        self.update_thread.error_occurred.connect(self.on_update_error)
        self.update_thread.start()
        
        # Log completion message
        total_minutes = round(seconds / 60, 2)
        
        # Format time for display
        if total_minutes < 1:
            time_display = f"{seconds} 秒"
        else:
            total_minutes_int = int(total_minutes)
            remaining_seconds = int((total_minutes - total_minutes_int) * 60)
            
            if total_minutes_int < 60:
                if remaining_seconds == 0:
                    time_display = f"{total_minutes_int} 分钟"
                else:
                    time_display = f"{total_minutes_int} 分钟 {remaining_seconds} 秒"
            else:
                hours = total_minutes_int // 60
                remaining_minutes = total_minutes_int % 60
                if remaining_minutes == 0 and remaining_seconds == 0:
                    time_display = f"{hours} 小时"
                elif remaining_seconds == 0:
                    time_display = f"{hours} 小时 {remaining_minutes} 分钟"
                else:
                    time_display = f"{hours} 小时 {remaining_minutes} 分钟 {remaining_seconds} 秒"
        
        self.log_message(f"Session completed: {time_display}, {len(screenshots)} screenshots")
    
    def on_screenshot_taken(self, screenshot_path: str):
        """Handle screenshot taken"""
        self.time_tracker.add_screenshot(screenshot_path)
        self.log_message(f"Screenshot saved: {screenshot_path}")
    
    def on_update_completed(self):
        """Handle task update completion"""
        # Close uploading dialog
        if hasattr(self, 'uploading_dialog'):
            self.uploading_dialog.close()
            self.uploading_dialog = None
        
        self.status_label.setText("Ready")
        self.log_message("Task updated successfully in Notion")
        
        # Update the task info display to show the new total time
        if self.selected_task:
            info_text = f"任务名称: {self.selected_task['title']}\n"
            info_text += f"负责人: {self.selected_task['assignee']}\n"
            info_text += f"已用时间: {self._format_time_for_display(self.selected_task['time_spent'])}\n"
            info_text += f"截止日期: {self.selected_task['due_date']}\n"
            self.task_info.setText(info_text)
    
    def on_update_error(self, error: str):
        """Handle task update error"""
        # Close uploading dialog
        if hasattr(self, 'uploading_dialog'):
            self.uploading_dialog.close()
            self.uploading_dialog = None
        
        self.status_label.setText("Error updating task")
        QMessageBox.warning(self, "Upload Error", f"Failed to update task in Notion: {error}")
        self.log_message(f"Error updating task: {error}")
    
    def log_message(self, message: str):
        """Add message to log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _format_time(self, seconds: int) -> str:
        """Format seconds into HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _format_time_for_display(self, minutes: float) -> str:
        """Format time for display - show minutes and seconds without decimals"""
        if minutes < 1:
            seconds = int(minutes * 60)
            return f"{seconds} 秒"
        else:
            total_minutes = int(minutes)
            remaining_seconds = int((minutes - total_minutes) * 60)
            
            if total_minutes < 60:
                if remaining_seconds == 0:
                    return f"{total_minutes} 分钟"
                else:
                    return f"{total_minutes} 分钟 {remaining_seconds} 秒"
            else:
                hours = total_minutes // 60
                remaining_minutes = total_minutes % 60
                if remaining_minutes == 0 and remaining_seconds == 0:
                    return f"{hours} 小时"
                elif remaining_seconds == 0:
                    return f"{hours} 小时 {remaining_minutes} 分钟"
                else:
                    return f"{hours} 小时 {remaining_minutes} 分钟 {remaining_seconds} 秒"
    
    def closeEvent(self, event):
        """Handle application close event"""
        if self.time_tracker.is_active():
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Time tracking is active. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_tracking()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept() 