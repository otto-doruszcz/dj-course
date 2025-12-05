"""
Audio playback module for macOS and cross-platform WAV file playback.
"""

import os
import subprocess
import platform
from typing import Optional
import threading


def play_audio(file_path: str, blocking: bool = False) -> Optional[int]:
    """
    Plays a WAV audio file using the system's default audio player.
    On macOS: uses 'afplay'
    On Linux: uses 'aplay' or 'paplay'
    On Windows: uses 'powershell' with Start-Process

    Args:
        file_path: Path to WAV file to play
        blocking: If True, waits for playback to complete. If False, plays in background.

    Returns:
        int: Process return code if blocking=True, None if blocking=False

    Raises:
        FileNotFoundError: If audio file doesn't exist
        RuntimeError: If unable to find suitable audio player
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            if blocking:
                return subprocess.run(["afplay", file_path], check=True).returncode
            else:
                subprocess.Popen(["afplay", file_path])
                return None

        elif system == "Linux":
            # Try aplay first, then paplay
            player = "aplay" if subprocess.run(["which", "aplay"], capture_output=True).returncode == 0 else "paplay"
            if blocking:
                return subprocess.run([player, file_path], check=True).returncode
            else:
                subprocess.Popen([player, file_path])
                return None

        elif system == "Windows":
            if blocking:
                return subprocess.run(["powershell", "-Command", f"Start-Process '{file_path}'"], check=True).returncode
            else:
                subprocess.Popen(["powershell", "-Command", f"Start-Process '{file_path}'"])
                return None

        else:
            raise RuntimeError(f"Unsupported operating system: {system}")

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to play audio: {e}")
    except FileNotFoundError as e:
        raise RuntimeError(f"Audio player not found on this system: {e}")


def play_audio_async(file_path: str, on_complete: Optional[callable] = None) -> threading.Thread:
    """
    Plays audio asynchronously in a background thread.

    Args:
        file_path: Path to WAV file to play
        on_complete: Optional callback function when playback finishes

    Returns:
        threading.Thread: The started thread object
    """
    def _play():
        try:
            play_audio(file_path, blocking=True)
            if on_complete:
                on_complete()
        except Exception as e:
            if on_complete:
                on_complete(error=str(e))

    thread = threading.Thread(target=_play, daemon=False)
    thread.start()
    return thread

