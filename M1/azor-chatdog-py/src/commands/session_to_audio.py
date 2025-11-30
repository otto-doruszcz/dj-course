"""
Session audio converter - converts entire chat session to a single audio file.
Generates audio for each message and concatenates them with silence gaps.
"""

import os
from pathlib import Path
from typing import Optional, List
from pydub import AudioSegment
from session import get_session_manager
from cli import console
from audio.audio_generator import generate_audio_sync
from audio.audio_player import play_audio
from commands.audio import extract_message_text, get_voice_path


def generate_full_session_audio(silence_ms: int = 1000) -> None:
    """
    Converts entire chat session to a single audio file.
    Generates individual WAV files for each message, concatenates them with silence gaps,
    and plays the final combined audio.

    Args:
        silence_ms: Duration of silence between messages in milliseconds (default: 1000)

    Raises:
        RuntimeError: If any message audio generation fails
        FileNotFoundError: If required voice files are not found
    """
    manager = get_session_manager()
    current_session = manager.get_current_session()

    # Get conversation history
    history = current_session.get_history()

    if not history:
        console.print_error("Błąd: Historia rozmowy jest pusta.")
        return

    # Create output directory for audio files
    session_audio_dir = Path(current_session.session_id) / "audio"
    session_audio_dir.mkdir(parents=True, exist_ok=True)

    # Verify voice files exist
    user_voice_path = get_voice_path("user")
    model_voice_path = get_voice_path("model")

    if not user_voice_path:
        console.print_error("Błąd: Nie znaleziono pliku voice_user.wav.")
        return

    if not model_voice_path:
        console.print_error("Błąd: Nie znaleziono pliku voice_model.wav.")
        return

    console.print_info(f"🎙️  Generowanie audio dla całej sesji ({len(history)} wiadomości)...")

    # Generate individual WAV files for each message
    wav_files = []
    try:
        for idx, item in enumerate(history, 1):
            role = item.get('role')
            message_text = extract_message_text(item)

            if not message_text or not message_text.strip():
                continue

            # Determine which voice to use
            voice_path = user_voice_path if role == 'user' else model_voice_path
            role_name = "User" if role == 'user' else "Asystent"

            # Generate unique filename
            wav_filename = f"message_{idx:03d}_{role}.wav"
            wav_path = str(session_audio_dir / wav_filename)

            console.print_info(f"  [{idx}/{len(history)}] Generowanie audio dla {role_name}...")

            try:
                output_path = generate_audio_sync(
                    text=message_text,
                    output_path=wav_path,
                    speaker_wav_path=voice_path,
                    language="pl"
                )
                wav_files.append(output_path)
            except Exception as e:
                # Clean up partial files before failing
                for file_path in wav_files:
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
                raise RuntimeError(f"Błąd generowania audio dla wiadomości {idx}: {str(e)}")

        if not wav_files:
            console.print_error("Błąd: Nie udało się wygenerować żadnych plików audio.")
            return

        # Concatenate all WAV files with silence gaps
        console.print_info("🔗 Łączenie plików audio...")
        final_audio_path = str(session_audio_dir / "full_session_audio.wav")

        try:
            concatenate_wav_files(wav_files, silence_ms, final_audio_path)
            console.print_info(f"✅ Audio sesji wygenerowane: {final_audio_path}")

            # Clean up intermediate files
            console.print_info("🧹 Czyszczenie tymczasowych plików...")
            for wav_file in wav_files:
                try:
                    os.remove(wav_file)
                except OSError as e:
                    console.print_warning(f"Nie udało się usunąć: {wav_file}")

            # Play the final audio
            console.print_info("▶️  Odtwarzanie audio sesji...")
            play_audio(final_audio_path, blocking=False)

        except Exception as e:
            # Clean up on concatenation failure
            for wav_file in wav_files:
                try:
                    os.remove(wav_file)
                except OSError:
                    pass
            console.print_error(f"Błąd łączenia plików audio: {str(e)}")

    except RuntimeError as e:
        console.print_error(str(e))
    except Exception as e:
        console.print_error(f"Nieoczekiwany błąd: {str(e)}")


def concatenate_wav_files(
    wav_paths: List[str],
    silence_ms: int,
    output_path: str
) -> None:
    """
    Concatenates multiple WAV files with silence gaps between them.

    Args:
        wav_paths: List of paths to WAV files to concatenate
        silence_ms: Duration of silence between files in milliseconds
        output_path: Path where concatenated WAV file will be saved

    Raises:
        ValueError: If wav_paths is empty
        FileNotFoundError: If any WAV file doesn't exist
        Exception: If concatenation fails
    """
    if not wav_paths:
        raise ValueError("No WAV files to concatenate")

    # Verify all files exist
    for wav_path in wav_paths:
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"WAV file not found: {wav_path}")

    # Load and concatenate files
    combined = None

    for wav_path in wav_paths:
        audio_segment = AudioSegment.from_wav(wav_path)

        if combined is None:
            combined = audio_segment
        else:
            # Add silence gap
            if silence_ms > 0:
                silence = AudioSegment.silent(duration=silence_ms)
                combined += silence
            # Add the next audio segment
            combined += audio_segment

    # Export the concatenated audio
    combined.export(output_path, format="wav")


def all_audio_command() -> None:
    """
    Command handler for /all-audio command.
    Converts entire session to audio and plays it.
    """
    generate_full_session_audio()

