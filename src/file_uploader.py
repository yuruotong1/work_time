"""
File Uploader for Work Time Tracker
Handles uploading screenshots to Notion
"""

import os
import base64
import requests
from typing import List, Optional
import logging

class FileUploader:
    """Handles file uploads to Notion"""
    
    def __init__(self, notion_token: str):
        """Initialize file uploader"""
        self.notion_token = notion_token
        self.logger = logging.getLogger(__name__)
    
    def upload_file_to_notion(self, file_path: str) -> Optional[str]:
        """Upload a file to Notion and return the file URL"""
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return None
            
            # Read file content
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            # Encode file content
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            
            # Prepare upload data
            upload_data = {
                "parent": {
                    "type": "database_id",
                    "database_id": "your_database_id"  # This will be set dynamically
                },
                "properties": {
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": os.path.basename(file_path)
                                }
                            }
                        ]
                    }
                },
                "children": [
                    {
                        "object": "block",
                        "type": "file",
                        "file": {
                            "type": "file",
                            "file": {
                                "url": f"data:image/png;base64,{encoded_content}",
                                "expiry_time": "2025-12-31T23:59:59.000Z"
                            }
                        }
                    }
                ]
            }
            
            # Upload to Notion
            headers = {
                "Authorization": f"Bearer {self.notion_token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json=upload_data
            )
            
            if response.status_code == 200:
                result = response.json()
                file_url = result.get('url')
                self.logger.info(f"File uploaded successfully: {file_url}")
                return file_url
            else:
                self.logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error uploading file: {e}")
            return None
    
    def upload_screenshots(self, screenshot_paths: List[str], database_id: str) -> List[str]:
        """Upload multiple screenshots and return their URLs"""
        uploaded_urls = []
        
        for screenshot_path in screenshot_paths:
            # Update database_id for this upload
            self.database_id = database_id
            
            file_url = self.upload_file_to_notion(screenshot_path)
            if file_url:
                uploaded_urls.append(file_url)
        
        return uploaded_urls 