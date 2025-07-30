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
    QSplitter, QGroupBox, QGridLayout, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

from .notion_client import NotionClient
from .time_tracker import TimeTracker
from .screenshot_manager import ScreenshotManager

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
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
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
        self.status_label.setText("Loading tasks...")
        self.refresh_btn.setEnabled(False)
        
        # Create and start loader thread
        self.loader_thread = TaskLoaderThread(self.notion_client)
        self.loader_thread.tasks_loaded.connect(self.on_tasks_loaded)
        self.loader_thread.error_occurred.connect(self.on_tasks_error)
        self.loader_thread.start()
    
    def on_tasks_loaded(self, tasks: List[Dict]):
        """Handle loaded tasks"""
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
        self.log_message(f"Loaded {len(tasks)} tasks from Notion")
    
    def on_tasks_error(self, error: str):
        """Handle task loading error"""
        self.status_label.setText("Error loading tasks")
        self.refresh_btn.setEnabled(True)
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
            info_text += f"已用时间: {task['time_spent']} 分钟\n"
            info_text += f"截止日期: {task['due_date']}\n"
            info_text += f"工资: {task['salary']} 元\n"
            self.task_info.setText(info_text)
            # Enable start button
            self.start_btn.setEnabled(True)
            self.current_task_label.setText(task['title'])
        else:
            self.selected_task = None
            self.start_btn.setEnabled(False)
            self.current_task_label.setText("No task selected")
            self.task_info.clear()
    
    def start_tracking(self):
        """Start time tracking"""
        if not self.selected_task:
            return
        
        # Start time tracking
        self.time_tracker.start_tracking(
            self.selected_task['id'], 
            self.selected_task['title']
        )
        
        # Start screenshot capture with default 5-minute interval
        self.screenshot_manager.set_interval(self.screenshot_interval)
        self.screenshot_manager.start_capture()
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.task_list.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
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
        
        # Update UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.task_list.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.status_label.setText("Ready")
        self.log_message("Stopped tracking")
    
    def update_time_display(self, time_str: str):
        """Update time display"""
        self.time_label.setText(time_str)
    
    def on_session_completed(self, seconds: int, screenshots: List[str]):
        """Handle session completion"""
        # Update Notion with time spent
        if self.selected_task:
            self.notion_client.update_task_time(
                self.selected_task['id'], 
                seconds, 
                screenshots
            )
        
        # Show completion message
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        total_minutes = round(seconds / 60, 2)
        
        message = f"Session completed!\n"
        message += f"Time spent: {hours}h {minutes}m ({total_minutes} minutes)\n"
        message += f"Screenshots taken: {len(screenshots)}"
        
        QMessageBox.information(self, "Session Complete", message)
        self.log_message(f"Session completed: {hours}h {minutes}m ({total_minutes} minutes), {len(screenshots)} screenshots")
    
    def on_screenshot_taken(self, screenshot_path: str):
        """Handle screenshot taken"""
        self.time_tracker.add_screenshot(screenshot_path)
        self.log_message(f"Screenshot saved: {screenshot_path}")
    

    
    def log_message(self, message: str):
        """Add message to log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
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