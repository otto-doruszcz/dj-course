## Plan: Convert Full Session to Single Audio File

Create a new reusable audio module file to handle full session audio generation with parametrizable silence duration. Refactor `audio.py` to expose reusable helper functions while keeping the existing `audio_command()` unchanged.

### Steps

1. **Refactor `audio.py`**:
   - Extract message text parsing into `extract_message_text(item)` public helper
   - Rename `_get_speaker_wav_path()` to `get_voice_path(voice_type)` accepting `"user"` or `"model"` parameters
   - Modify voice file lookup to handle both `voice_user.wav` and `voice_model.wav` in `src/audio/` directory
   - Keep `audio_command()` unchanged

2. **Add `pydub` to `requirements.txt`** for WAV file concatenation.

3. **Create `session_to_audio.py`** in `src/commands/` with:
   - `generate_full_session_audio(silence_ms=1000)` function to iterate entire history and generate individual WAV files per message
   - `concatenate_wav_files(wav_paths, silence_ms, output_path)` function using pydub to merge files with silence gaps
   - Fail-fast error handling: stop immediately on first generation error
   - Auto-cleanup of intermediate WAV files after successful concatenation
   - Play final `full_session_audio.wav` on completion

4. **Output location**: Save final audio to `{session_id}/audio/full_session_audio.wav`

5. **Wire into command system** : Add CLI /all-audio command integration

### Implementation Details

- **Message filtering**: Include all user and model messages from history
- **Speaker assignment**: Use `voice_user.wav` for user role, `voice_model.wav` for model role
- **Silence duration**: Parametrized with 1000ms default between consecutive messages
- **Intermediate files**: Generated in session audio directory, deleted after concatenation succeeds

