import os
import time
import math
import requests
from datetime import datetime
from typing import List, Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

MAX_RETRY = 3
BASE_DELAY = 1.0  # seconds


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
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_attempts}): {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
    raise last_exc


class FileUploader:
    """Handles file uploads to Notion using the file upload API"""

    def __init__(self, notion_token: str, database_id: str = None):
        self.notion_token = notion_token
        self.database_id = database_id
        self.logger = logging.getLogger(__name__)
        self.headers = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28"
        }

    def create_file_upload(self) -> str:
        """Create a file upload session and return the upload URL (with retry)."""
        url = "https://api.notion.com/v1/file_uploads"
        headers = self.headers | {"Content-Type": "application/json"}

        def _call():
            response = requests.post(url, headers=headers, json={}, timeout=30)
            response.raise_for_status()
            return response.json()["upload_url"]

        return _retry(_call)

    def send_file_upload(self, upload_url: str, file_path: str) -> Dict:
        """Send file to the upload session (with retry)."""
        headers = self.headers

        def _call():
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "image/png")}
                response = requests.post(upload_url, headers=headers, files=files, timeout=60)
            response.raise_for_status()
            return response.json()

        return _retry(_call)

    def upload_file_to_notion(self, file_path: str) -> str:
        """Upload a single file to Notion and return the file upload ID."""
        upload_url = self.create_file_upload()
        res = self.send_file_upload(upload_url, file_path)
        return res["id"]

    def create_collage(self, screenshot_paths: List[str]) -> Optional[str]:
        """
        Merge multiple screenshots into a single collage image (2-column grid).
        Returns the path of the saved collage, or the single path if only one image.
        """
        from PIL import Image

        if not screenshot_paths:
            return None
        if len(screenshot_paths) == 1:
            return screenshot_paths[0]

        MAX_THUMB_WIDTH = 900
        images = []
        for path in screenshot_paths:
            try:
                img = Image.open(path).convert("RGB")
                if img.width > MAX_THUMB_WIDTH:
                    ratio = MAX_THUMB_WIDTH / img.width
                    img = img.resize((MAX_THUMB_WIDTH, int(img.height * ratio)), Image.LANCZOS)
                images.append(img)
            except Exception as e:
                self.logger.warning(f"Skipping screenshot {path}: {e}")

        if not images:
            return None

        cols = 2
        rows = math.ceil(len(images) / cols)
        cell_w = max(img.width for img in images)
        cell_h = max(img.height for img in images)

        canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), (240, 240, 240))
        for idx, img in enumerate(images):
            x = (idx % cols) * cell_w
            y = (idx // cols) * cell_h
            canvas.paste(img, (x, y))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = os.path.dirname(screenshot_paths[0])
        collage_path = os.path.join(save_dir, f"collage_{timestamp}.png")
        canvas.save(collage_path, "PNG", optimize=True)
        self.logger.info(f"Collage saved: {collage_path} ({len(images)} screenshots)")
        return collage_path

    def upload_screenshots(self, screenshot_paths: List[str]) -> List[Tuple[str, str]]:
        """
        Merge screenshots into one collage, upload it, and return [(collage_path, file_id)].
        Falls back to uploading individually if collage creation fails.
        """
        if not screenshot_paths:
            return []

        try:
            collage_path = self.create_collage(screenshot_paths)
            if collage_path:
                file_id = self.upload_file_to_notion(collage_path)
                return [(collage_path, file_id)]
        except Exception as e:
            self.logger.error(f"Collage upload failed, falling back to individual upload: {e}")

        # Fallback: upload individually
        results = []
        for path in screenshot_paths:
            try:
                file_id = self.upload_file_to_notion(path)
                results.append((path, file_id))
            except Exception as e:
                self.logger.error(f"Failed to upload {path}: {e}")
        return results
