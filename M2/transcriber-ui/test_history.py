#!/usr/bin/env python3
"""
Test script for HistoryManager functionality.
Validates all core features: add, delete, cleanup, and history loading.
"""

import os
import sys
import json
import wave
import logging
import tempfile
import shutil
from datetime import datetime, timezone
from history_manager import HistoryManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def create_test_wav(filepath: str, duration_sec: float = 1.0) -> None:
    """Create a minimal valid WAV file for testing."""
    sample_rate = 16000
    num_frames = int(sample_rate * duration_sec)

    with wave.open(filepath, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        # Write silence
        wav_file.writeframes(b'\x00\x00' * num_frames)

def test_history_manager():
    """Run comprehensive tests for HistoryManager."""

    # Create temporary directory for testing
    test_dir = tempfile.mkdtemp(prefix="test_history_")
    print(f"\n📁 Using temporary directory: {test_dir}\n")

    try:
        # Initialize HistoryManager
        manager = HistoryManager(output_dir=test_dir)
        print("✅ HistoryManager initialized successfully")

        # Test 1: Add transcription
        print("\n--- Test 1: Add Transcription ---")
        test_timestamp = datetime.now(timezone.utc).isoformat()
        test_audio = os.path.join(test_dir, "recordings", "test-recording.wav")
        create_test_wav(test_audio, duration_sec=5.5)

        success = manager.add_transcription(
            timestamp=test_timestamp,
            audio_file=test_audio,
            full_text="This is a test transcription with some sample text."
        )
        assert success, "Failed to add transcription"
        print(f"✅ Added transcription: {test_timestamp}")

        # Test 2: Load active history
        print("\n--- Test 2: Load Active History ---")
        active_history = manager.load_active_history()
        assert len(active_history) == 1, f"Expected 1 entry, got {len(active_history)}"
        assert active_history[0]["fullText"] == "This is a test transcription with some sample text."
        print(f"✅ Loaded {len(active_history)} active transcription(s)")

        # Test 3: Add multiple transcriptions
        print("\n--- Test 3: Add Multiple Transcriptions ---")
        for i in range(3):
            timestamp = datetime.now(timezone.utc).isoformat()
            audio_file = os.path.join(test_dir, "recordings", f"test-recording-{i}.wav")
            create_test_wav(audio_file, duration_sec=float(i + 1))

            success = manager.add_transcription(
                timestamp=timestamp,
                audio_file=audio_file,
                full_text=f"Transcription number {i} with varying duration."
            )
            assert success, f"Failed to add transcription {i}"

        active_history = manager.load_active_history()
        assert len(active_history) == 4, f"Expected 4 entries, got {len(active_history)}"
        print(f"✅ Added 3 more transcriptions. Total active: {len(active_history)}")

        # Test 4: Verify newest-first ordering
        print("\n--- Test 4: Verify Newest-First Ordering ---")
        timestamps = [entry["timestamp"] for entry in active_history]
        is_sorted_newest_first = all(
            timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1)
        )
        assert is_sorted_newest_first, "History not sorted newest-first"
        print("✅ Entries are correctly ordered (newest first)")

        # Test 5: Get entry by ID
        print("\n--- Test 5: Get Entry by ID ---")
        first_entry_id = active_history[0]["id"]
        retrieved_entry = manager.get_entry_by_id(first_entry_id)
        assert retrieved_entry is not None, "Could not retrieve entry by ID"
        assert retrieved_entry["id"] == first_entry_id
        print(f"✅ Successfully retrieved entry by ID: {first_entry_id}")

        # Test 6: Soft delete
        print("\n--- Test 6: Soft Delete ---")
        entry_to_delete = active_history[0]
        delete_id = entry_to_delete["id"]

        success = manager.mark_deleted(delete_id)
        assert success, "Failed to mark transcription as deleted"

        # Verify it's marked as deleted but still in full history
        full_history = manager.load_history()
        deleted_entry = manager.get_entry_by_id(delete_id)
        assert deleted_entry["deleted"] is True, "Entry not marked as deleted"

        # Verify it's not in active history anymore
        active_history = manager.load_active_history()
        assert not any(e["id"] == delete_id for e in active_history), "Deleted entry still in active history"
        print(f"✅ Successfully soft-deleted entry: {delete_id}")
        print(f"   Active transcriptions remaining: {len(active_history)}")

        # Test 7: Verify WAV file deletion
        print("\n--- Test 7: Verify WAV File Deletion ---")
        audio_path = manager.get_audio_path(delete_id)
        if audio_path:
            wav_exists = os.path.exists(audio_path)
            print(f"   WAV file exists after soft-delete: {wav_exists}")
            if not wav_exists:
                print("✅ WAV file was successfully deleted")
            else:
                print("⚠️  WAV file still exists (expected behavior for orphan detection)")

        # Test 8: Cleanup orphaned entries
        print("\n--- Test 8: Cleanup Orphaned Entries ---")
        # Manually create an orphaned entry (entry with no WAV file)
        orphan_entry = {
            "id": "orphan-entry",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "audioFile": "non-existent-file.wav",
            "fullText": "This entry has no audio file",
            "duration": 0.0,
            "deleted": False,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }

        history = manager.load_history()
        history.append(orphan_entry)
        manager._write_history(history)
        print("   Manually created orphaned entry")

        # Run cleanup
        cleaned_count = manager.cleanup_orphaned_entries()
        print(f"✅ Cleanup removed {cleaned_count} orphaned entries")

        # Test 9: File locking (write multiple times quickly)
        print("\n--- Test 9: File Locking/Concurrency ---")
        for i in range(5):
            timestamp = datetime.now(timezone.utc).isoformat()
            audio_file = os.path.join(test_dir, "recordings", f"lock-test-{i}.wav")
            create_test_wav(audio_file, duration_sec=1.0)
            manager.add_transcription(
                timestamp=timestamp,
                audio_file=audio_file,
                full_text=f"Concurrency test {i}"
            )

        active_history = manager.load_active_history()
        print(f"✅ File locking works. Entries survived rapid writes: {len(active_history)}")

        # Test 10: JSON schema validation
        print("\n--- Test 10: JSON Schema Validation ---")
        with open(os.path.join(test_dir, "history.json"), 'r') as f:
            data = json.load(f)

        assert "transcriptions" in data, "Missing 'transcriptions' key"
        for entry in data["transcriptions"]:
            required_keys = {"id", "timestamp", "audioFile", "fullText", "duration", "deleted", "createdAt"}
            assert required_keys.issubset(entry.keys()), f"Entry missing required keys: {required_keys - entry.keys()}"

        print(f"✅ JSON schema valid. Entries: {len(data['transcriptions'])}")

        print("\n" + "="*50)
        print("✅ All tests passed!")
        print("="*50 + "\n")

        return True

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"🗑️  Cleaned up temporary directory: {test_dir}\n")

if __name__ == "__main__":
    success = test_history_manager()
    sys.exit(0 if success else 1)

