"""
Notion API Client for Work Time Tracker
"""

import os
from typing import List, Dict, Optional
from notion_client import Client
from notion_client.errors import APIResponseError
import logging
from .file_uploader import FileUploader
import yaml

class NotionClient:
    """Client for interacting with Notion API"""
    
    def __init__(self):
        """Initialize Notion client with credentials"""
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)

        self.token = config['notion']['api']
        self.database_id = config['notion']['database_id']
        self.column_mappings = config.get('database', {})
        
        if not self.token or not self.database_id:
            raise ValueError("Notion API token and database ID must be set in config.yaml")
        
        self.client = Client(auth=self.token)
        self.logger = logging.getLogger(__name__)
        self.file_uploader = FileUploader(self.token)
    
    def get_tasks(self) -> List[Dict]:
        """Fetch tasks from Notion database"""
        try:
            # Get all tasks from database (no filter for now)
            response = self.client.databases.query(
                database_id=self.database_id
            )
            
            tasks = []
            for page in response['results']:
                task = self._parse_task_page(page)
                if task:
                    tasks.append(task)
            print(tasks)
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
                'time_spent': self._get_number_value(properties.get(self.column_mappings.get('time_spent', '工作时间（分钟）'), {})),
                'screenshots': self._get_files_value(properties.get(self.column_mappings.get('screenshots', '截屏'), {})),
                'due_date': self._get_date_value(properties.get(self.column_mappings.get('due_date', '截止日期'), {})),
                'salary': self._get_number_value(properties.get(self.column_mappings.get('salary', '工资'), {})),
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
    
    def _get_select_value(self, select_prop: Dict) -> str:
        """Extract value from select property"""
        if select_prop.get('select'):
            return select_prop['select']['name']
        return ""
    
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
            file_names = [file.get('name', '') for file in files_prop['files']]
            return ', '.join(file_names)
        return ""
    
    def _get_date_value(self, date_prop: Dict) -> str:
        """Extract value from date property"""
        if date_prop.get('date') and date_prop['date'].get('start'):
            return date_prop['date']['start'][:10]  # Return YYYY-MM-DD format
        return ""
    
    def update_task_time(self, task_id: str, time_spent: int, screenshots: List[str]):
        """Update task with time spent and screenshot paths"""
        try:
            # Prepare properties to update
            properties = {}
            
            # Update time spent (convert seconds to minutes)
            time_column = self.column_mappings.get('time_spent', '时间')
            time_minutes = round(time_spent / 60, 2)  # Convert seconds to minutes with 2 decimal places
            properties[time_column] = {
                "number": time_minutes
            }
            
            # Update screenshots (Files type)
            if screenshots:
                screenshot_column = self.column_mappings.get('screenshots', '截屏')
                try:
                    # Upload screenshots to Notion
                    uploaded_urls = self.file_uploader.upload_screenshots(screenshots, self.database_id)
                    
                    if uploaded_urls:
                        # Update the Files property with uploaded file URLs
                        properties[screenshot_column] = {
                            "files": [
                                {
                                    "name": os.path.basename(screenshot_path),
                                    "type": "external",
                                    "external": {
                                        "url": url
                                    }
                                }
                                for screenshot_path, url in zip(screenshots, uploaded_urls)
                            ]
                        }
                        self.logger.info(f"Uploaded {len(uploaded_urls)} screenshots to Notion")
                    else:
                        self.logger.warning("Failed to upload screenshots to Notion")
                        
                except Exception as e:
                    self.logger.error(f"Error uploading screenshots: {e}")
                    # Fallback: just log the screenshot paths
                    self.logger.info(f"Screenshots taken: {screenshots}")
            
            # Update the page
            self.client.pages.update(
                page_id=task_id,
                properties=properties
            )
            
            self.logger.info(f"Updated task {task_id} with {time_minutes} minutes ({time_spent} seconds)")
            
        except APIResponseError as e:
            self.logger.error(f"Notion API error updating task: {e}")
        except Exception as e:
            self.logger.error(f"Error updating task: {e}")
    
    def test_connection(self) -> bool:
        """Test connection to Notion API"""
        try:
            self.client.databases.retrieve(database_id=self.database_id)
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False 