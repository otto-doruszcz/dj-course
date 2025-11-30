# Implementation Summary: Full Session Audio Converter

## Overview
Successfully implemented the complete feature to convert entire chat sessions into single audio files with parametrizable silence duration. The implementation includes:

1. **Refactored `audio.py`** - Extracted reusable helper functions
2. **New `session_to_audio.py`** - Session-wide audio generation module
3. **Updated `command_handler.py`** - Integrated `/all-audio` command
4. **Updated `console.py`** - Added help text for new command
5. **Updated `requirements.txt`** - Added pydub dependency

---

## Changes Made

### 1. `src/commands/audio.py` (Refactored)
**Extracted two public helper functions for reuse:**

- `extract_message_text(item: Any) -> Optional[str]`
  - Parses message items from history
  - Handles both 'parts' format and direct 'text' format
  - Returns text or None

- `get_voice_path(voice_type: str) -> Optional[str]`
  - Locates voice WAV files by type ("user" or "model")
  - Searches multiple locations including `src/audio/`
  - Returns absolute path or None

- `audio_command()` - Unchanged behavior
  - Converts last assistant message to audio
  - Uses refactored helper functions

**Removed:**
- Old `_get_speaker_wav_path()` function (superseded by `get_voice_path()`)
- Unused `threading` import

---

### 2. `src/commands/session_to_audio.py` (New File)
**Main entry point:**
- `all_audio_command() -> None`
  - CLI command handler for `/all-audio`
  - Calls `generate_full_session_audio()`

**Core functionality:**

- `generate_full_session_audio(silence_ms: int = 1000) -> None`
  - Iterates through entire conversation history
  - Generates individual WAV for each message (user or model)
  - Uses appropriate voice file per role:
    - User messages → `voice_user.wav`
    - Model messages → `voice_model.wav`
  - Error handling: Fail-fast on any generation error
  - Auto-cleanup: Removes intermediate files after successful concatenation
  - Plays final audio: `{session_id}/audio/full_session_audio.wav`
  - Supports parametrized silence duration (default: 1000ms)

- `concatenate_wav_files(wav_paths: List[str], silence_ms: int, output_path: str) -> None`
  - Uses pydub library for WAV concatenation
  - Adds configurable silence gaps between messages
  - Exports final combined WAV file
  - Validates all input files exist

---

### 3. `src/command_handler.py` (Updated)
**Changes:**
- Added import: `from commands.session_to_audio import all_audio_command`
- Added command: `/all-audio` to `VALID_SLASH_COMMANDS`
- Added handler:
  ```python
  elif command == '/all-audio':
      all_audio_command()
  ```

---

### 4. `src/cli/console.py` (Updated)
**Help text updated to include:**
```
/all-audio        - Konwertuje całą sesję do jednego pliku audio i go odtwarza.
```

---

### 5. `requirements.txt` (Updated)
**Added dependency:**
```
pydub
```

---

## Feature Details

### Audio Generation Pipeline
1. **History parsing**: Extract all messages from current session
2. **Voice file validation**: Verify `voice_user.wav` and `voice_model.wav` exist
3. **Individual generation**: For each message:
   - Generate WAV with appropriate speaker voice
   - Save as `message_NNN_role.wav` (sequentially numbered)
4. **Concatenation**: Combine all WAV files with silence gaps
5. **Output**: Save as `{session_id}/audio/full_session_audio.wav`
6. **Cleanup**: Remove intermediate files
7. **Playback**: Automatically play final audio

### Error Handling
- **Fail-fast**: If any message generation fails, entire process stops
- **Cleanup**: Partial files removed before failing
- **User feedback**: Detailed error messages in Polish
- **File validation**: Checks voice files exist before starting

### Performance
- Sequential processing (not parallel)
- Reuses cached TTS model instance
- Intermediate files cleaned up immediately
- Suitable for multi-minute audio sessions

---

## Usage

### From command line (in chat):
```
/all-audio
```

### Programmatic usage:
```python
from commands.session_to_audio import generate_full_session_audio

# With default 1000ms silence
generate_full_session_audio()

# With custom silence duration
generate_full_session_audio(silence_ms=500)
```

---

## File Locations

| File | Location | Type |
|------|----------|------|
| Refactored helpers | `src/commands/audio.py` | Modified |
| New module | `src/commands/session_to_audio.py` | Created |
| Command handler | `src/command_handler.py` | Modified |
| Help text | `src/cli/console.py` | Modified |
| Dependencies | `requirements.txt` | Modified |

---

## Output Structure

```
{session_id}/audio/
├── full_session_audio.wav       (final combined audio)
├── last_response.wav             (from /audio command)
└── [intermediate files deleted]
```

---

## Testing Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Verify voice files exist: `voice_user.wav` and `voice_model.wav`
- [ ] Test `/all-audio` command in chat
- [ ] Verify output file created at `{session_id}/audio/full_session_audio.wav`
- [ ] Check audio plays correctly
- [ ] Verify intermediate files are cleaned up
- [ ] Test error handling (missing voice file, empty history)

---

## Notes

- **Silence duration**: Parametrizable (default 1000ms = 1 second between messages)
- **Message filtering**: All user + model messages included
- **Language**: Polish messages in UI; audio generation uses Polish TTS
- **Platform support**: Works on macOS with afplay; cross-platform via audio_player module
- **Memory**: TTS model cached in memory; separate audio files prevent RAM overload

---

## Dependencies Added

- **pydub** - WAV file concatenation and manipulation
  - Requires: ffmpeg installed on system (macOS: `brew install ffmpeg`)

