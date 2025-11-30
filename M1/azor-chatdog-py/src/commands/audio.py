"""
Audio command handler - converts last assistant message to speech and plays it.
"""

import os
import threading
from pathlib import Path
from session import get_session_manager
from cli import console
from audio.audio_generator import generate_audio_async
from audio.audio_player import play_audio


def audio_command() -> None:
    """
    Converts the last assistant response to audio using XTTS and plays it.
    Uses /audio command in the chat.
    """
    manager = get_session_manager()
    current_session = manager.get_current_session()

    # Get conversation history
    history = current_session.get_history()

    # Find last assistant message
    last_assistant_message = None
    for item in reversed(history):
        if 'role' in item and item.get('role', None) == 'model':
            last_assistant_message = item['parts'][0]['text'] if 'parts' in item else item.get('text')
            break

    if not last_assistant_message:
        console.print_error("Błąd: Brak poprzedniej odpowiedzi asystenta do odtworzenia.")
        return

    # Setup paths
    speaker_wav_path = _get_speaker_wav_path()
    if not speaker_wav_path:
        console.print_error("Błąd: Nie znaleziono pliku z nagraniem głosu (voice_user.wav).")
        return

    output_dir = Path(current_session.session_id) / "audio"
    output_path = str(output_dir / "last_response.wav")

    console.print_info("🎙️  Generowanie pliku audio...")

    def on_complete(file_path: str):
        """Callback when audio generation completes."""
        try:
            console.print_info(f"✅ Plik audio wygenerowany. Odtwarzanie...")
            play_audio(file_path, blocking=False)
        except Exception as e:
            console.print_error(f"Błąd odtwarzania audio: {e}")

    def on_error(error_msg: str):
        """Callback if audio generation fails."""
        console.print_error(f"Błąd generowania audio: {error_msg}")

    try:
        generate_audio_async(
            text=last_assistant_message,
            output_path=output_path,
            speaker_wav_path=speaker_wav_path,
            language="pl",
            on_complete=on_complete,
            on_error=on_error
        )
    except ValueError as e:
        console.print_error(f"Błąd: {e}")
    except FileNotFoundError as e:
        console.print_error(f"Błąd: {e}")


def _get_speaker_wav_path() -> str | None:
    """
    Finds the speaker WAV file reference.
    Searches in multiple locations.

    Returns:
        str: Path to speaker WAV file, or None if not found
    """
    possible_paths = [
        "recorded_voice.wav",  # Current directory
        os.path.join(os.path.dirname(__file__), "..", "..", "M2", "text-to-speach-xtts", "recorded_voice.wav"),
        os.path.join(os.path.dirname(__file__), "..", "audio", "recorded_voice.wav"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return os.path.abspath(path)

    return None

