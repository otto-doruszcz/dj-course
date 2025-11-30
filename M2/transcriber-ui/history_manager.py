"""
HistoryManager - Handles persistent storage of transcription history with file locking and soft deletes.
"""

import json
import os
import logging
import fcntl
import wave
from datetime import datetime, timezone
from typing import List, Dict, Optional


class HistoryManager:
    """
    Manages transcription history with persistent JSON storage.

    Features:
    - File locking for thread-safe writes
    - WAV file verification before JSON updates
    - Soft deletes (mark as deleted, keep audit trail)
    - Cleanup of orphaned entries on startup
    - Newest entries first (reverse chronological)
    """

    def __init__(self, output_dir: str = "output"):
        """
        Initialize the HistoryManager.

        Args:
            output_dir: Base output directory for recordings and history.json
        """
        self.output_dir = output_dir
        self.recordings_dir = os.path.join(output_dir, "recordings")
        self.history_file = os.path.join(output_dir, "history.json")

        # Create directories if they don't exist
        os.makedirs(self.recordings_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Initialize history file if it doesn't exist
        if not os.path.exists(self.history_file):
            self._write_history([])

        # Cleanup orphaned entries on startup
        self.cleanup_orphaned_entries()
        logging.info(f"HistoryManager initialized. History file: {self.history_file}")

    def _lock_and_read(self) -> List[Dict]:
        """
        Read history.json with file locking.

        Returns:
            List of transcription entries
        """
        try:
            with open(self.history_file, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    return data.get("transcriptions", [])
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (json.JSONDecodeError, FileNotFoundError):
            logging.warning("History file is empty or corrupted, returning empty list")
            return []

    def _write_history(self, transcriptions: List[Dict]) -> None:
        """
        Write history to JSON file with file locking.

        Args:
            transcriptions: List of transcription entries to write
        """
        try:
            # Write to temporary file first for atomicity
            temp_file = self.history_file + ".tmp"
            with open(temp_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump({"transcriptions": transcriptions}, f, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Replace original with temp file
            os.replace(temp_file, self.history_file)
            logging.debug(f"History written successfully ({len(transcriptions)} entries)")
        except Exception as e:
            logging.error(f"Error writing history file: {e}", exc_info=True)
            raise

    def _verify_wav_file(self, audio_path: str) -> bool:
        """
        Verify that a WAV file exists and has content.

        Args:
            audio_path: Path to the WAV file

        Returns:
            True if file exists and has valid content, False otherwise
        """
        try:
            if not os.path.exists(audio_path):
                logging.warning(f"WAV file not found: {audio_path}")
                return False

            if os.path.getsize(audio_path) == 0:
                logging.warning(f"WAV file is empty: {audio_path}")
                return False

            # Attempt to open as WAV to verify integrity
            try:
                with wave.open(audio_path, 'rb') as wav_file:
                    wav_file.readframes(1)  # Try to read one frame
                return True
            except wave.Error as e:
                logging.warning(f"WAV file is invalid: {audio_path} - {e}")
                return False

        except Exception as e:
            logging.error(f"Error verifying WAV file: {e}", exc_info=True)
            return False

    def _get_wav_duration(self, audio_path: str) -> float:
        """
        Calculate the duration of a WAV file in seconds.

        Args:
            audio_path: Path to the WAV file

        Returns:
            Duration in seconds, or 0.0 if unable to determine
        """
        try:
            with wave.open(audio_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration = frames / float(rate)
                return round(duration, 2)
        except Exception as e:
            logging.error(f"Error calculating WAV duration for {audio_path}: {e}")
            return 0.0

    def add_transcription(
        self,
        timestamp: str,
        audio_file: str,
        full_text: str,
        duration: Optional[float] = None
    ) -> bool:
        """
        Add a new transcription entry to history (after WAV verification).

        Write-order atomicity:
        1. Verify WAV file exists and is valid
        2. Calculate duration if not provided
        3. Create entry
        4. Prepend to history (newest first)
        5. Write to JSON

        Args:
            timestamp: ISO 8601 timestamp (e.g., "2025-01-15T14:30:00Z")
            audio_file: Path to the WAV file
            full_text: Complete transcription text
            duration: Duration in seconds (auto-calculated if None)

        Returns:
            True if successfully added, False otherwise
        """
        # Step 1: Verify WAV file
        if not self._verify_wav_file(audio_file):
            logging.error(f"Cannot add transcription: WAV file invalid at {audio_file}")
            return False

        # Step 2: Calculate duration if not provided
        if duration is None:
            duration = self._get_wav_duration(audio_file)

        try:
            # Step 3: Create entry
            entry = {
                "id": timestamp,  # Use timestamp as unique ID
                "timestamp": timestamp,
                "audioFile": os.path.basename(audio_file),  # Store relative path
                "fullText": full_text,
                "duration": duration,
                "deleted": False,
                "createdAt": datetime.now(timezone.utc).isoformat()
            }

            # Step 4: Load current history and prepend new entry
            history = self._lock_and_read()
            history.insert(0, entry)  # Newest first

            # Step 5: Write to JSON
            self._write_history(history)

            logging.info(f"Transcription added: {entry['id']} ({duration}s, {len(full_text)} chars)")
            return True

        except Exception as e:
            logging.error(f"Error adding transcription: {e}", exc_info=True)
            return False

    def mark_deleted(self, transcription_id: str) -> bool:
        """
        Soft-delete a transcription entry (mark as deleted, keep audit trail).
        Also deletes the associated WAV file.

        Args:
            transcription_id: Timestamp-based ID of the entry to delete

        Returns:
            True if successfully marked as deleted, False otherwise
        """
        try:
            history = self._lock_and_read()

            # Find and mark the entry as deleted
            entry_found = False
            for entry in history:
                if entry["id"] == transcription_id:
                    entry["deleted"] = True
                    entry["deletedAt"] = datetime.now(timezone.utc).isoformat()
                    entry_found = True

                    # Delete the associated WAV file
                    audio_file = os.path.join(self.recordings_dir, entry["audioFile"])
                    if os.path.exists(audio_file):
                        try:
                            os.remove(audio_file)
                            logging.info(f"WAV file deleted: {audio_file}")
                        except Exception as e:
                            logging.error(f"Error deleting WAV file {audio_file}: {e}")

                    break

            if not entry_found:
                logging.warning(f"Transcription not found for deletion: {transcription_id}")
                return False

            # Write updated history
            self._write_history(history)
            logging.info(f"Transcription marked as deleted: {transcription_id}")
            return True

        except Exception as e:
            logging.error(f"Error marking transcription as deleted: {e}", exc_info=True)
            return False

    def load_history(self) -> List[Dict]:
        """
        Load all history entries (including deleted ones, for audit purposes).

        Returns:
            List of all transcription entries (newest first)
        """
        return self._lock_and_read()

    def load_active_history(self) -> List[Dict]:
        """
        Load only active (non-deleted) transcription entries.

        Returns:
            List of active transcription entries (newest first)
        """
        history = self._lock_and_read()
        return [entry for entry in history if not entry.get("deleted", False)]

    def cleanup_orphaned_entries(self) -> int:
        """
        Remove JSON entries that have missing WAV files (soft-delete orphans).
        This maintains consistency between JSON and disk state.

        Returns:
            Number of orphaned entries cleaned up
        """
        try:
            history = self._lock_and_read()
            original_count = len(history)

            # Filter out entries where WAV file is missing or deleted entry without WAV
            cleaned_history = []
            for entry in history:
                if entry.get("deleted", False):
                    # For deleted entries, verify WAV file was actually removed
                    audio_file = os.path.join(self.recordings_dir, entry["audioFile"])
                    if os.path.exists(audio_file):
                        # WAV still exists for deleted entry, keep it in history
                        cleaned_history.append(entry)
                    # else: deleted entry with no WAV, skip it
                else:
                    # For active entries, verify WAV exists
                    audio_file = os.path.join(self.recordings_dir, entry["audioFile"])
                    if os.path.exists(audio_file):
                        cleaned_history.append(entry)
                    else:
                        logging.warning(f"Removing orphaned entry (missing WAV): {entry['id']}")

            cleaned_count = original_count - len(cleaned_history)
            if cleaned_count > 0:
                self._write_history(cleaned_history)
                logging.info(f"Cleanup complete: removed {cleaned_count} orphaned entries")

            return cleaned_count

        except Exception as e:
            logging.error(f"Error during cleanup: {e}", exc_info=True)
            return 0

    def get_entry_by_id(self, transcription_id: str) -> Optional[Dict]:
        """
        Retrieve a specific transcription entry by ID.

        Args:
            transcription_id: Timestamp-based ID

        Returns:
            Entry dict or None if not found
        """
        history = self._lock_and_read()
        for entry in history:
            if entry["id"] == transcription_id:
                return entry
        return None

    def get_audio_path(self, transcription_id: str) -> Optional[str]:
        """
        Get the full path to the audio file for a transcription entry.

        Args:
            transcription_id: Timestamp-based ID

        Returns:
            Full path to audio file or None if entry not found
        """
        entry = self.get_entry_by_id(transcription_id)
        if entry:
            return os.path.join(self.recordings_dir, entry["audioFile"])
        return None


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.DEBUG)
    manager = HistoryManager()
    print(f"Active transcriptions: {len(manager.load_active_history())}")

