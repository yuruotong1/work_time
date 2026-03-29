"""
Background uploader - retries pending uploads indefinitely until they succeed.
"""

import logging
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition

RETRY_INTERVAL_MS = 2 * 60 * 1000  # 2 minutes


class BackgroundUploader(QThread):
    """
    Runs in background, processes the upload queue every 2 minutes.
    Call trigger() to wake it up immediately (e.g., right after a session ends).
    """

    time_synced = pyqtSignal(str)          # task_title
    screenshots_synced = pyqtSignal(str)   # task_title
    time_failed = pyqtSignal(str, str)     # task_title, error_msg
    screenshots_failed = pyqtSignal(str)   # task_title

    def __init__(self, notion_client, upload_queue):
        super().__init__()
        self.notion_client = notion_client
        self.upload_queue = upload_queue
        self.logger = logging.getLogger(__name__)
        self._stop = False
        self._mutex = QMutex()
        self._wake = QWaitCondition()

    def trigger(self):
        """Wake up the thread to process the queue immediately."""
        self._wake.wakeAll()

    def stop(self):
        self._stop = True
        self._wake.wakeAll()

    def run(self):
        while not self._stop:
            self._process_all()
            self._mutex.lock()
            self._wake.wait(self._mutex, RETRY_INTERVAL_MS)
            self._mutex.unlock()

    def _process_all(self):
        pending = self.upload_queue.get_pending()
        if pending:
            self.logger.info(f"Processing {len(pending)} pending session(s)...")
        for session in pending:
            if self._stop:
                break
            self._process_session(session)
        self.upload_queue.remove_completed()

    def _process_session(self, session: dict):
        task_title = session.get("task_title", session["task_id"])

        # --- Step 1: Upload time (highest priority) ---
        if not session["time_uploaded"]:
            try:
                self.notion_client.update_time_only(
                    session["task_id"],
                    session["time_seconds"],
                )
                self.upload_queue.mark_time_done(session["id"])
                session["time_uploaded"] = True
                self.time_synced.emit(task_title)
                self.logger.info(f"Time synced for '{task_title}'")
            except Exception as e:
                self.logger.error(f"Time sync failed for '{task_title}': {e}")
                self.time_failed.emit(task_title, str(e))
                return  # Don't attempt screenshots until time succeeds

        # --- Step 2: Upload screenshots (lower priority) ---
        if not session["screenshots_uploaded"]:
            paths = [p for p in session.get("screenshot_paths", []) if __import__("os").path.exists(p)]
            if not paths:
                self.upload_queue.mark_screenshots_done(session["id"])
                return
            try:
                self.notion_client.append_screenshots(session["task_id"], paths)
                self.upload_queue.mark_screenshots_done(session["id"])
                self.screenshots_synced.emit(task_title)
                self.logger.info(f"Screenshots synced for '{task_title}'")
            except Exception as e:
                self.logger.error(f"Screenshot sync failed for '{task_title}': {e}")
                self.screenshots_failed.emit(task_title)
