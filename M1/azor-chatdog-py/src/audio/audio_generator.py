"""
Audio generation module using XTTS (Coqui TTS).
Provides async text-to-speech conversion to WAV format.
"""

import os
import threading
from pathlib import Path
from typing import Optional, Callable
from TTS.api import TTS
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# Global TTS instance (cached to avoid reloading model)
_tts_instance: Optional[TTS] = None
_tts_lock = threading.Lock()


def get_tts_instance() -> TTS:
    """
    Gets or creates a cached TTS instance.
    Thread-safe singleton pattern.

    Returns:
        TTS: Loaded XTTS v2 model instance
    """
    global _tts_instance

    if _tts_instance is not None:
        return _tts_instance

    with _tts_lock:
        if _tts_instance is None:
            _tts_instance = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cpu")

    return _tts_instance


def generate_audio_async(
    text: str,
    output_path: str,
    speaker_wav_path: str,
    language: str = "pl",
    on_complete: Optional[Callable] = None,
    on_error: Optional[Callable] = None
) -> threading.Thread:
    """
    Generates audio asynchronously from text using XTTS.

    Args:
        text: Text to convert to speech
        output_path: Path where WAV file will be saved
        speaker_wav_path: Path to speaker reference WAV file
        language: Language code (default: "pl" for Polish)
        on_complete: Callback function when generation is complete
        on_error: Callback function if generation fails

    Returns:
        threading.Thread: The started thread object

    Raises:
        FileNotFoundError: If speaker_wav_path doesn't exist
        ValueError: If text is empty
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    if not os.path.exists(speaker_wav_path):
        raise FileNotFoundError(f"Speaker WAV file not found: {speaker_wav_path}")

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    def _generate():
        try:
            tts = get_tts_instance()
            tts.tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=speaker_wav_path,
                language=language
            )
            if on_complete:
                on_complete(output_path)
        except Exception as e:
            if on_error:
                on_error(str(e))
            else:
                raise

    thread = threading.Thread(target=_generate, daemon=False)
    thread.start()
    return thread


def generate_audio_sync(
    text: str,
    output_path: str,
    speaker_wav_path: str,
    language: str = "pl"
) -> str:
    """
    Generates audio synchronously (blocking) from text using XTTS.

    Args:
        text: Text to convert to speech
        output_path: Path where WAV file will be saved
        speaker_wav_path: Path to speaker reference WAV file
        language: Language code (default: "pl" for Polish)

    Returns:
        str: Path to generated WAV file

    Raises:
        FileNotFoundError: If speaker_wav_path doesn't exist
        ValueError: If text is empty
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    if not os.path.exists(speaker_wav_path):
        raise FileNotFoundError(f"Speaker WAV file not found: {speaker_wav_path}")

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    tts = get_tts_instance()
    tts.tts_to_file(
        text=text,
        file_path=output_path,
        speaker_wav=speaker_wav_path,
        language=language
    )

    return output_path

