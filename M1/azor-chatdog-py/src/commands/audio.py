"""
Audio command handler - converts last assistant message to speech and plays it.
"""

import os
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
            last_assistant_message = extract_message_text(item)
            break

    if not last_assistant_message:
        console.print_error("Błąd: Brak poprzedniej odpowiedzi asystenta do odtworzenia.")
        return

    # Setup paths
    speaker_wav_path = get_voice_path("model")
    if not speaker_wav_path:
        console.print_error("Błąd: Nie znaleziono pliku z nagraniem głosu (voice_model.wav).")
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


def get_voice_path(voice_type: str) -> str | None:
    """
    Finds the voice WAV file for a given type ('user' or 'model').
    Searches in multiple locations.

    Args:
        voice_type: Either "user" or "model".

    Returns:
        str: Absolute path to the voice WAV file, or None if not found.
    """
    if voice_type not in ["user", "model"]:
        return None

    filename = f"voice_{voice_type}.wav"

    possible_paths = [
        filename,  # Current directory
        os.path.join(os.path.dirname(__file__), "..", "audio", filename),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return os.path.abspath(path)

    return None


def extract_message_text(item: any) -> str | None:
    """
    Parses a message item from history and extracts the text.
    Handles both 'parts' format and direct 'text' format.
    """
    if 'role' not in item:
        return None

    if 'parts' in item and item['parts'] and 'text' in item['parts'][0]:
        return item['parts'][0]['text']
    elif 'text' in item:
        return item['text']

    return None
