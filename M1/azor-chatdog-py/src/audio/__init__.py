"""
Audio module for text-to-speech generation and playback.
"""

from audio.audio_generator import generate_audio_async, generate_audio_sync, get_tts_instance
from audio.audio_player import play_audio, play_audio_async

__all__ = [
    'generate_audio_async',
    'generate_audio_sync',
    'get_tts_instance',
    'play_audio',
    'play_audio_async',
]

