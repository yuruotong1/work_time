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
from .upload_queue import UploadQueue
from .background_uploader import BackgroundUploader

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

            # Local queue + background uploader (infinite retry)
            self.upload_queue = UploadQueue()
            self.background_uploader = BackgroundUploader(self.notion_client, self.upload_queue)
            self.background_uploader.time_synced.connect(self.on_time_synced)
            self.background_uploader.screenshots_synced.connect(self.on_screenshots_synced)
            self.background_uploader.time_failed.connect(self.on_time_failed)
            self.background_uploader.screenshots_failed.connect(self.on_screenshots_failed)
            self.background_uploader.start()

            # Warn if Notion unreachable, but don't block startup
            if not self.notion_client.test_connection():
                QMessageBox.warning(self, "连接提示",
                                    "Notion 暂时无法连接，任务列表可能为空。\n"
                                    "本次及历史工作记录会在网络恢复后自动同步。")

            # Retry any sessions left over from previous app runs
            if self.upload_queue.has_pending():
                self.log_message("检测到未上传的历史记录，后台重试中...")
                self.background_uploader.trigger()

        except Exception as e:
            QMessageBox.critical(self, "初始化错误",
                                 f"应用启动失败: {str(e)}")
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
            self.current_task_label.setText(task['title'][:20] + "...")
            
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
        self.time_tracker.stop_tracking()
        self.screenshot_manager.stop_capture()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.task_list.setEnabled(True)

        if self.selected_task:
            total_minutes = self.selected_task.get('time_spent', 0)
            self.time_label.setText(self._format_time(total_minutes * 60))

        self.status_label.setText("正在同步到 Notion...")
        self.log_message("已停止计时，准备同步...")
    
    def update_time_display(self, time_str: str):
        """Update time display with total time (previous + current session)"""
        # time_str from TimeTracker already includes previous time + current session
        self.time_label.setText(time_str)
    
    def on_session_completed(self, seconds: int, screenshots: List[str]):
        """Handle session completion - save locally first, then sync in background."""
        if self.selected_task:
            new_session_minutes = round(seconds / 60, 2)
            self.selected_task['time_spent'] = self.selected_task.get('time_spent', 0) + new_session_minutes
            for i in range(self.task_list.count()):
                item = self.task_list.item(i)
                task = item.data(Qt.ItemDataRole.UserRole)
                if task and task.get('id') == self.selected_task.get('id'):
                    task['time_spent'] = self.selected_task['time_spent']
                    item.setData(Qt.ItemDataRole.UserRole, task)
                    break
            self.time_label.setText(self._format_time(self.selected_task['time_spent'] * 60))

            # 1. 先存本地队列（断网/崩溃也不会丢失）
            self.upload_queue.add(
                self.selected_task['id'],
                self.selected_task['title'],
                seconds,
                screenshots,
            )
            time_display = self._format_time_for_display(new_session_minutes)
            self.log_message(f"已保存本地 - 本次时间: {time_display}，截图: {len(screenshots)} 张")

            # 2. 立即触发后台上传（失败会自动每2分钟重试）
            self.background_uploader.trigger()
            self.status_label.setText("正在后台同步时间到 Notion...")
    
    def on_screenshot_taken(self, screenshot_path: str):
        """Handle screenshot taken"""
        self.time_tracker.add_screenshot(screenshot_path)
        self.log_message(f"Screenshot saved: {screenshot_path}")
    
    def on_time_synced(self, task_title: str):
        """Called when time is successfully uploaded to Notion."""
        self.status_label.setText("时间已同步 ✓")
        self.log_message(f"✓ 时间已同步到 Notion：{task_title}")
        if self.selected_task:
            info_text = f"任务名称: {self.selected_task['title']}\n"
            info_text += f"负责人: {self.selected_task['assignee']}\n"
            info_text += f"已用时间: {self._format_time_for_display(self.selected_task['time_spent'])}\n"
            info_text += f"截止日期: {self.selected_task['due_date']}\n"
            self.task_info.setText(info_text)

    def on_screenshots_synced(self, task_title: str):
        """Called when screenshots are successfully uploaded."""
        self.status_label.setText("同步完成 ✓")
        self.log_message(f"✓ 截图已上传：{task_title}")

    def on_time_failed(self, task_title: str, error: str):
        """Called when time upload fails (will be retried automatically)."""
        self.status_label.setText("时间同步失败，后台重试中...")
        self.log_message(f"⚠ 时间同步失败，后台每2分钟自动重试：{task_title}")
        self.logger.error(f"Time sync failed for '{task_title}': {error}")

    def on_screenshots_failed(self, task_title: str):
        """Called when screenshot upload fails (will be retried automatically)."""
        self.status_label.setText("时间已同步 ✓，截图后台重试中...")
        self.log_message(f"⚠ 截图上传失败，后台自动重试（时间已同步）：{task_title}")
    
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
                self, "确认退出",
                "计时正在进行中，确定要退出吗？\n（未完成的时间记录会保存到本地，下次启动后自动同步）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_tracking()
            else:
                event.ignore()
                return

        # Stop background uploader gracefully
        if hasattr(self, 'background_uploader'):
            self.background_uploader.stop()
            self.background_uploader.wait(3000)

        if self.upload_queue.has_pending():
            QMessageBox.information(
                self, "同步提示",
                "还有未完成的同步任务，下次启动应用时会自动继续上传。"
            )
        event.accept() 