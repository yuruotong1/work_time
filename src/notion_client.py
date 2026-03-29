"""
Notion API Client for Work Time Tracker
"""

import os
import sys
import time
from typing import List, Dict, Optional
from notion_client import Client
from notion_client.errors import APIResponseError
import logging
from .file_uploader import FileUploader
import yaml
from datetime import datetime

MAX_RETRY = 3
BASE_DELAY = 1.0


def _retry(func, max_attempts=MAX_RETRY, base_delay=BASE_DELAY):
    """Retry a callable with exponential backoff."""
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            last_exc = e
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logging.getLogger(__name__).warning(
                    f"Notion API call failed (attempt {attempt + 1}/{max_attempts}): {e}. Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
    raise last_exc

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class NotionClient:
    """Client for interacting with Notion API"""
    
    def __init__(self):
        """Initialize Notion client with credentials"""
        with open(resource_path('config.yaml'), 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)

        self.token = config['notion']['api']
        self.database_id = config['notion']['database_id']
        self.column_mappings = config.get('database', {})
        
        if not self.token or not self.database_id:
            raise ValueError("Notion API token and database ID must be set in config.yaml")
        
        self.client = Client(auth=self.token)
        self.logger = logging.getLogger(__name__)
        self.file_uploader = FileUploader(self.token, self.database_id)
    
    def get_tasks(self) -> List[Dict]:
        """Fetch tasks from Notion database"""
        try:
            # Filter for tasks with status "未开始" (Not Started) or "进行中" (In Progress)
            status_column = self.column_mappings.get('status', '状态')
            filter_conditions = {
                "or": [
                    {
                        "property": status_column,
                        "status": {
                            "equals": "未开始"
                        }
                    },
                    {
                        "property": status_column,
                        "status": {
                            "equals": "进行中"
                        }
                    }
                ]
            }
            
            response = _retry(lambda: self.client.databases.query(
                database_id=self.database_id,
                filter=filter_conditions
            ))
            
            tasks = []
            for page in response['results']:
                task = self._parse_task_page(page)
                if task:
                    tasks.append(task)
            return tasks
            
        except APIResponseError as e:
            self.logger.error(f"Notion API error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error fetching tasks: {e}")
            return []
    
    def _parse_task_page(self, page: Dict) -> Optional[Dict]:
        """Parse a Notion page into a task dictionary"""
        try:
            properties = page['properties']
            
            # Extract task properties based on your database structure
            task = {
                'id': page['id'],
                'title': self._get_title(properties.get(self.column_mappings.get('task_name', '任务名称'), {})),
                'assignee': self._get_select_value(properties.get(self.column_mappings.get('assignee', '负责人'), {})),
                'status': self._get_status_value(properties.get(self.column_mappings.get('status', '状态'), {})),
                'time_spent': self._get_number_value(properties.get(self.column_mappings.get('time_spent', '工作时间（分钟）'), {})),
                'screenshots': self._get_files_value(properties.get(self.column_mappings.get('screenshots', '截屏'), {})),
                'due_date': self._get_date_value(properties.get(self.column_mappings.get('due_date', '截止日期'), {})),
                'created_time': page['created_time'],
                'last_edited_time': page['last_edited_time']
            }
            
            return task
            
        except Exception as e:
            self.logger.error(f"Error parsing task page: {e}")
            return None
    
    def _get_title(self, title_prop: Dict) -> str:
        """Extract title from title property"""
        if title_prop.get('title'):
            return title_prop['title'][0]['plain_text']
        return "Untitled"
    
    def _get_status_value(self, status_prop: Dict) -> str:
        """Extract value from status property"""
        return status_prop.get('status', {}).get("name", "")
    
    def _get_select_value(self, select_prop: Dict) -> str:
        """Extract value from select property"""
        return select_prop.get('select', {}).get("name", "")
    
    def _get_number_value(self, number_prop: Dict) -> int:
        """Extract value from number property"""
        if number_prop.get('number') is not None:
            return number_prop['number']
        return 0
    
    def _get_rich_text_value(self, rich_text_prop: Dict) -> str:
        """Extract value from rich text property"""
        if rich_text_prop.get('rich_text'):
            texts = [text.get('plain_text', '') for text in rich_text_prop['rich_text']]
            return ' '.join(texts)
        return ""
    
    def _get_files_value(self, files_prop: Dict) -> str:
        """Extract value from files property"""
        if files_prop.get('files'):
            file_names = []
            for file in files_prop['files']:
                if file.get('type') == 'file_upload' and file.get('file_upload'):
                    file_names.append(file.get('name', ''))
                elif file.get('type') == 'external' and file.get('external'):
                    file_names.append(file.get('name', ''))
            return ', '.join(file_names)
        return ""
    
    def _get_date_value(self, date_prop: Dict) -> str:
        """Extract value from date property"""
        if date_prop.get('date') and date_prop['date'].get('start'):
            return date_prop['date']['start'][:10]  # Return YYYY-MM-DD format
        return ""
    
    def update_task_time(self, task_id: str, time_spent: int, screenshots: List[str]):
        """Update task with time spent and screenshot collage (with retry)"""
        try:
            properties = {}

            # Retrieve current task data (with retry)
            current_task = None
            response = None
            try:
                response = _retry(lambda: self.client.pages.retrieve(page_id=task_id))
                current_task = self._parse_task_page(response)
            except Exception as e:
                self.logger.warning(f"Could not retrieve current task data: {e}")

            # Calculate total time
            current_time_minutes = current_task.get('time_spent', 0) if current_task else 0
            new_session_minutes = round(time_spent / 60, 2)
            total_time_minutes = current_time_minutes + new_session_minutes

            time_column = self.column_mappings.get('time_spent', '时间')
            properties[time_column] = {"number": total_time_minutes}

            # Handle screenshots
            screenshot_column = self.column_mappings.get('screenshots', '截屏')

            existing_files = []
            if response is not None:
                screenshot_prop = response['properties'].get(screenshot_column, {})
                if screenshot_prop.get('files'):
                    existing_files = screenshot_prop['files']

            # Upload: creates one collage image per session, returns [(path, id)]
            uploaded = self.file_uploader.upload_screenshots(screenshots)

            all_files = existing_files.copy()
            for path, file_id in uploaded:
                all_files.append({
                    "type": "file_upload",
                    "file_upload": {"id": file_id},
                    "name": os.path.basename(path),
                })

            # Keep only the most recent 20 collages to avoid Notion slowdown
            max_files = 20
            if len(all_files) > max_files:
                sorted_files = self._sort_files_by_time(all_files)
                all_files = sorted_files[-max_files:]
                self.logger.info(f"Trimmed to {max_files} most recent collages")

            properties[screenshot_column] = {"type": "files", "files": all_files}

            # Push update to Notion (with retry)
            _retry(lambda: self.client.pages.update(page_id=task_id, properties=properties))

            self.logger.info(
                f"Updated task {task_id}: total={total_time_minutes:.2f}min "
                f"(+{new_session_minutes:.2f}min), collages in Notion: {len(all_files)}"
            )

        except APIResponseError as e:
            self.logger.error(f"Notion API error updating task: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error updating task: {e}")
            raise
    
    def _sort_files_by_time(self, files: List[Dict]) -> List[Dict]:
        """Sort files by creation time (oldest first)"""
        try:
            # For files with timestamps in filename (e.g., 20231201_143022.png)
            def get_file_timestamp(file_obj):
                try:
                    file_name = file_obj.get('name', '')
                    if '_' in file_name:
                        # Extract timestamp from filename like "20231201_143022.png"
                        timestamp_part = file_name.split('.')[0]  # Remove extension
                        if len(timestamp_part) == 15 and '_' in timestamp_part:  # Format: YYYYMMDD_HHMMSS
                            return timestamp_part
                    
                    # If no timestamp in name, use file upload creation time if available
                    if file_obj.get('type') == 'file_upload':
                        # Return current time as fallback (newest)
                        return datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    return "19700101_000000"  # Very old timestamp as fallback
                    
                except Exception:
                    return "19700101_000000"  # Very old timestamp as fallback
            
            # Sort files by timestamp (oldest first)
            sorted_files = sorted(files, key=get_file_timestamp)
            return sorted_files
            
        except Exception as e:
            self.logger.warning(f"Error sorting files by time: {e}")
            return files  # Return original order if sorting fails

    def test_connection(self) -> bool:
        """Test connection to Notion API"""
        try:
            _retry(lambda: self.client.databases.retrieve(database_id=self.database_id))
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False 