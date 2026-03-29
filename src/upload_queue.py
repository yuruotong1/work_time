"""
Local upload queue - persists pending sessions to disk so they survive app restarts.
"""

import json
import os
import uuid
import logging
from datetime import datetime
from typing import List, Dict

QUEUE_FILE = "pending_uploads.json"


class UploadQueue:
    """Thread-safe local JSON queue for pending Notion uploads."""

    def __init__(self, queue_file: str = QUEUE_FILE):
        self.queue_file = queue_file
        self.logger = logging.getLogger(__name__)

    def _load(self) -> List[Dict]:
        if not os.path.exists(self.queue_file):
            return []
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load queue: {e}")
            return []

    def _save(self, sessions: List[Dict]):
        try:
            with open(self.queue_file, "w", encoding="utf-8") as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save queue: {e}")

    def add(self, task_id: str, task_title: str, time_seconds: int,
            screenshot_paths: List[str]) -> str:
        """Add a work session to the queue. Returns the session ID."""
        sessions = self._load()
        session_id = str(uuid.uuid4())
        sessions.append({
            "id": session_id,
            "task_id": task_id,
            "task_title": task_title,
            "time_seconds": time_seconds,
            "screenshot_paths": [p for p in screenshot_paths if os.path.exists(p)],
            "created_at": datetime.now().isoformat(),
            "time_uploaded": False,
            "screenshots_uploaded": False,
        })
        self._save(sessions)
        self.logger.info(f"Queued session {session_id} for task '{task_title}' "
                         f"({time_seconds}s, {len(screenshot_paths)} screenshots)")
        return session_id

    def mark_time_done(self, session_id: str):
        sessions = self._load()
        for s in sessions:
            if s["id"] == session_id:
                s["time_uploaded"] = True
                break
        self._save(sessions)

    def mark_screenshots_done(self, session_id: str):
        sessions = self._load()
        for s in sessions:
            if s["id"] == session_id:
                s["screenshots_uploaded"] = True
                break
        self._save(sessions)

    def remove_completed(self):
        """Remove sessions where both time and screenshots are uploaded."""
        sessions = self._load()
        remaining = [s for s in sessions
                     if not (s["time_uploaded"] and s["screenshots_uploaded"])]
        if len(remaining) < len(sessions):
            self._save(remaining)
            self.logger.info(f"Removed {len(sessions) - len(remaining)} completed sessions from queue")

    def get_pending(self) -> List[Dict]:
        """Return all sessions that still have pending work."""
        return [s for s in self._load()
                if not (s["time_uploaded"] and s["screenshots_uploaded"])]

    def has_pending(self) -> bool:
        return bool(self.get_pending())
