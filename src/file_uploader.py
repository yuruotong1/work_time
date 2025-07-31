import os
import json
import requests
from typing import List, Optional, Dict
import logging

class FileUploader:
    """Handles file uploads to Notion using the file upload API"""
    
    def __init__(self, notion_token: str, database_id: str = None):
        """Initialize file uploader"""
        self.notion_token = notion_token
        self.database_id = database_id
        self.logger = logging.getLogger(__name__)
        self.headers = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28"
        }
    
    def create_file_upload(self) -> Optional[str]:
        """Create a file upload session and return the upload ID"""
        url = "https://api.notion.com/v1/file_uploads"
        headers = self.headers | {"Content-Type": "application/json"}
        payload = {}
        response = requests.post(url, headers=headers, json=payload)
        data: Dict = response.json()
        return data["upload_url"]


    def send_file_upload(self, upload_url: str, file_path: str) -> bool:
        """Send file to the created upload session"""
        headers = self.headers
        # Open file in binary mode
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, "image/png")
            }
            response = requests.post(upload_url, headers=headers, files=files)
            print("send file upload response", response.json())
        return response.json()

    def upload_file_via_url(self, file_url: str, filename: str) -> Optional[Dict]:
        """Import external file via URL"""
        url = "https://api.notion.com/v1/file_uploads"
        headers = self.headers | {"Content-Type": "application/json"}
        payload = {
            "mode": "external_url",
            "external_url": file_url,
            "filename": filename
        }

        response = requests.post(url, headers=headers, json=payload)

        self.logger.info(f"Upload file via URL status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                self.logger.info("File uploaded via URL successfully")
                return result
            except ValueError:
                self.logger.error("Invalid JSON response")
                return None
        else:
            self.logger.error(f"Failed to upload file via URL: {response.status_code} - {response.text}")
            return None


    def upload_file_to_notion(self, file_path: str) -> Optional[str]:
        """Upload a file to Notion using the file upload API and return the file URL"""
        upload_url = self.create_file_upload()
        res = self.send_file_upload(upload_url, file_path)
        return res["id"]

    def upload_screenshots(self, screenshot_paths: List[str]) -> List[str]:
        """Upload multiple screenshots and return their URLs"""
        file_ids = []
        for screenshot_path in screenshot_paths:
            file_id = self.upload_file_to_notion(screenshot_path)
            file_ids.append(file_id)
        return file_ids 