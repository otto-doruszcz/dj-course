# Azor the Chatdog - AI Agent Instructions

## Project Overview
**Azor the Chatdog** is a terminal-based interactive chat application written in Python that provides persistent conversational sessions with multiple LLM providers. It features session management, audio generation, PDF export, and a rich command interface for managing chat history.

## Architecture & Core Concepts

### Tech Stack
- **Language**: Python 3.12+
- **LLM Providers**: Google Gemini, OpenAI, Anthropic Claude, Local LLaMA (llama-cpp-python)
- **UI**: prompt-toolkit (interactive CLI), colorama (colored output)
- **Audio**: coqui-tts (text-to-speech), pydub (audio processing)
- **Persistence**: JSON file-based storage in `~/.azor/`
- **Configuration**: python-dotenv for environment variables

### Domain Model (5 Core Components)

#### 1. **ChatSession** (`session/chat_session.py`)
Represents a single chat conversation with:
- Unique session ID (UUID)
- Conversation history (universal format)
- LLM client instance
- Assistant configuration
- Token counting and context management

#### 2. **SessionManager** (`session/session_manager.py`)
Orchestrates session lifecycle:
- Creates new sessions
- Switches between sessions
- Handles session persistence
- Manages current active session

#### 3. **SessionRepository** (`session/repository.py` + `persistence/filesystem_repository.py`)
Protocol-based persistence layer:
- Loads/saves session history
- Lists available sessions
- Manages WAL (Write-Ahead Log)
- Session removal

#### 4. **LLM Clients** (`llm/` directory)
Provider-agnostic LLM interface:
- `base_client.py` - Abstract base class
- `gemini_client.py` - Google Gemini implementation
- `openai_client.py` - OpenAI implementation
- `anthropic_client.py` - Anthropic Claude implementation
- `llama_client.py` - Local LLaMA implementation
- `factory.py` - Client creation and provider registration

#### 5. **Commands** (`commands/` directory)
Slash command implementations (one file per command):
- `welcome.py` - ASCII art welcome screen
- `session_list.py` - List all sessions
- `session_display.py` - Full session history
- `session_summary.py` - Abbreviated history
- `session_remove.py` - Delete sessions
- `session_to_pdf.py` - Export to PDF
- `session_to_audio.py` - Generate session audio
- `audio.py` - Audio playback controls

## Data Flow & Execution Pattern

### Application Startup
1. **Entry Point**: `src/run.py` → `chat.py::init_chat()`
2. **Environment Check**: Validate `.env` configuration (ENGINE, API keys, model paths)
3. **Welcome Screen**: Display ASCII art (`commands/welcome.py`)
4. **Session Initialization**: 
   - Check for `--session-id` CLI argument
   - Load existing session OR create new UUID-based session
5. **Register Cleanup**: `atexit.register()` ensures final save on exit

### Main Chat Loop
```
User Input → Command Detection → Handler Selection
                                     ↓
                        ┌────────────┴────────────┐
                        ↓                         ↓
                  Slash Command            Regular Message
                  (command_handler.py)     (ChatSession.send_message)
                        ↓                         ↓
                  Execute Command           LLM Client → Response
                        ↓                         ↓
                  Display Result            Save to WAL + History
                                                  ↓
                                            Display Response + Tokens
```

### Persistence Strategy
- **Session History**: `~/.azor/<session-id>-log.json` (saved after every message)
- **WAL (Write-Ahead Log)**: `~/.azor/azor-wal.json` (all transactions logged immediately)
- **Audio Files**: `<session-id>/audio/` subdirectories
- **Save Conditions**: Only save sessions with ≥2 messages (one complete turn)

## Key Implementation Patterns

### 1. Virtual Environment Requirement
⚠️ **ALWAYS activate venv before running Python code**:
```bash
prepenv
```

### 2. Colorama Usage Convention
- **ONLY** import `colorama` in `cli/console.py`
- All other files use `console.print_*()` functions
- Available functions:
  - `print_error()` - Red text for errors
  - `print_assistant()` - Cyan text for AI responses
  - `print_user()` - Blue text for user messages
  - `print_info()` - Yellow text for info messages
  - `print_help()` - Help/documentation messages

### 3. Command Architecture
Each slash command follows this pattern:

**File Naming**: Use underscores (`session_list.py`), NOT hyphens (invalid Python modules)

**Command File Structure**:
```python
from session.repository import SessionRepository
from cli import console

def command_name_command(repository: SessionRepository):
    """
    Command description.
    
    Args:
        repository: SessionRepository instance
    """
    # Implementation using repository methods
    # Use console.print_*() for output
```

**Registration** in `command_handler.py`:
```python
from commands.session_list import list_sessions_command

# In handle_command() or handle_session_subcommand():
if subcommand == 'list':
    list_sessions_command(get_repository())
```

### 4. LLM Client Pattern
All clients implement `BaseLLMClient` interface:
- `start_chat(system_prompt, history)` - Initialize chat session
- `send_message(text)` - Send message and get response
- `count_history_tokens(history)` - Token counting
- Validation methods for required config

**Factory Usage**:
```python
from llm.factory import create_llm_client
from llm.config import GenerationConfig

config = GenerationConfig.balanced()
client = create_llm_client("gemini", api_key="...", model_name="gemini-2.0-flash", generation_config=config)
```

### 5. Repository Protocol
Uses Python protocols (structural subtyping) for dependency injection:
```python
from session.repository import SessionRepository

class FileSystemSessionRepository(SessionRepository):
    def load_history(self, session_id) -> Tuple[List[Dict], str | None]:
        # Implementation
    
    def save_history(self, session_id, history, system_prompt, model_name) -> Tuple[bool, str | None]:
        # Implementation
```

## Configuration Management

### Environment Variables (`.env`)

**Required Variables by Provider**:

**Gemini**:
```bash
ENGINE=GEMINI
GEMINI_API_KEY=your_api_key_here
MODEL_NAME=gemini-2.0-flash
```

**OpenAI**:
```bash
ENGINE=OPENAI
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=gpt-4o-mini
```

**Anthropic**:
```bash
ENGINE=ANTHROPIC
ANTHROPIC_API_KEY=your_api_key_here
MODEL_NAME=claude-3-5-sonnet-20241022
```

**Local LLaMA**:
```bash
ENGINE=LLAMA_CPP
MODEL_NAME=llama-3.1-8b-instruct
LLAMA_MODEL_PATH=/path/to/model.gguf
LLAMA_GPU_LAYERS=1
LLAMA_CONTEXT_SIZE=2048
```

### Universal History Format
All clients use standardized history structure:
```python
history = [
    {
        "role": "user",  # or "model"/"assistant"
        "parts": [{"text": "message content"}]
    }
]
```

## Development Workflows

### Running the Application
```bash
# Activate venv
source .venv/bin/activate

# Run normally
python src/run.py

# Continue existing session
python src/run.py --session-id=<UUID>
```

### Adding New Slash Commands
1. Create `commands/new_command.py` with function `new_command_command(repository)`
2. Import in `command_handler.py`
3. Add to `VALID_SLASH_COMMANDS` list
4. Route in `handle_command()` or `handle_session_subcommand()`
5. Use `console.print_*()` for all output

### Adding New LLM Providers
1. Create `llm/provider_client.py` inheriting from `BaseLLMClient`
2. Implement required methods (start_chat, send_message, token counting)
3. Add validation class if needed (e.g., `provider_validation.py`)
4. Register in `llm/factory.py`:
   ```python
   from llm.provider_client import ProviderClient
   register_provider("provider", ProviderClient)
   ```
5. Update `.env` example in documentation

### Modifying Session Persistence
- Core logic in `persistence/filesystem_repository.py`
- Follow `SessionRepository` protocol
- Always return tuples: `(data, error_message_or_none)`
- Handle JSON encoding/decoding errors gracefully
- Validate history format before saving

## File Structure Conventions

```
src/
├── run.py                    # Entry point
├── chat.py                   # Main loop logic
├── command_handler.py        # Command routing
├── cli/                      # User interface utilities
│   ├── console.py           # ⚠️ ONLY place for colorama imports
│   ├── prompt.py            # Input handling
│   └── args.py              # CLI argument parsing
├── commands/                 # ⚠️ One file per command, use underscores
│   ├── welcome.py
│   ├── session_list.py
│   ├── session_display.py
│   └── ...
├── session/                  # Session management
│   ├── chat_session.py      # Session class
│   ├── session_manager.py   # Lifecycle orchestration
│   └── repository.py        # Protocol definition
├── persistence/              # Storage implementations
│   └── filesystem_repository.py
├── llm/                      # LLM client abstractions
│   ├── base_client.py       # Abstract base
│   ├── factory.py           # Provider factory
│   ├── config.py            # Generation configs
│   ├── gemini_client.py
│   ├── openai_client.py
│   ├── anthropic_client.py
│   └── llama_client.py
├── assistant/                # Assistant definitions
│   ├── assistent.py         # Base class
│   └── azor.py              # Azor personality
├── audio/                    # Audio generation
│   ├── audio_generator.py
│   └── audio_player.py
└── files/                    # File utilities
    ├── config.py            # Path constants
    └── pdf/                 # PDF generation
```

## Supported Slash Commands

```
/exit, /quit           - Exit application (saves current session)
/help                  - Display help and current session info
/switch <SESSION-ID>   - Switch to different session
/session list          - List all available sessions
/session display       - Show full current session history
/session new           - Create new session
/session clear         - Clear current session history
/session pop           - Remove last message exchange
/session remove <ID>   - Delete a session permanently
/pdf                   - Export current session to PDF
/audio                 - Play last assistant response audio
/all-audio             - Generate audio for entire session
```

## Testing & Debugging

### Token Monitoring
After each message, display shows:
- Total tokens used
- Remaining tokens (max: 32,768)
- Color-coded warnings at 75%/90% capacity

### Session Validation
- Sessions require ≥2 messages to be saved (one complete exchange)
- Corrupted session files return error messages but don't crash
- WAL logs every transaction for debugging

### Error Handling Patterns
- Always return tuples with error state: `(data, error_or_none)`
- Use `console.print_error()` for user-facing errors
- Validate environment variables before client initialization
- Graceful degradation (e.g., missing session files create new sessions)

## External Dependencies

Core dependencies (see `requirements.txt`):
- `google-genai` - Gemini client
- `openai>=1.0.0` - OpenAI client  
- `anthropic>=0.34.0` - Claude client
- `llama-cpp-python` - Local LLaMA support
- `prompt_toolkit` - Interactive CLI
- `colorama` - Terminal colors
- `pydantic>=2.0.0` - Data validation
- `fpdf2` - PDF generation
- `coqui-tts` - Text-to-speech
- `pydub` - Audio processing
- `python-dotenv` - Environment config
- `markdown` - Markdown processing

## API Documentation

### BaseLLMClient Interface
All LLM client implementations must implement these methods:

```python
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Tuple

class BaseLLMClient(ABC):
    """Base class for all LLM client implementations."""
    
    @abstractmethod
    def start_chat(self, system_prompt: str, history: List[Dict] | None = None) -> Any:
        """
        Initialize a chat session with system prompt and optional history.
        
        Args:
            system_prompt: System instructions for the assistant
            history: Optional conversation history in universal format
            
        Returns:
            Chat session object (provider-specific)
        """
        pass
    
    @abstractmethod
    def send_message(self, text: str) -> Any:
        """
        Send a message and receive response.
        
        Args:
            text: User message content
            
        Returns:
            Response object with .text attribute
        """
        pass
    
    @abstractmethod
    def count_history_tokens(self, history: List[Dict]) -> int:
        """
        Count tokens in conversation history.
        
        Args:
            history: Conversation history in universal format
            
        Returns:
            Total token count
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> Tuple[bool, str | None]:
        """
        Validate client configuration.
        
        Returns:
            tuple: (is_valid, error_message_or_none)
        """
        pass
```

### SessionRepository Protocol
Persistence implementations must provide these methods:

```python
from typing import Protocol, List, Dict, Tuple

class SessionRepository(Protocol):
    """Protocol for session persistence implementations."""
    
    def load_history(self, session_id: str) -> Tuple[List[Dict], str | None]:
        """
        Load session history from storage.
        
        Returns:
            tuple: (history_list, error_message_or_none)
        """
        ...
    
    def save_history(
        self, 
        session_id: str, 
        history: List[Dict], 
        system_prompt: str, 
        model_name: str
    ) -> Tuple[bool, str | None]:
        """
        Save session history to storage.
        
        Returns:
            tuple: (success, error_message_or_none)
        """
        ...
    
    def list_sessions(self) -> List[str]:
        """Return list of all session IDs."""
        ...
    
    def remove_session(self, session_id: str) -> Tuple[bool, str | None]:
        """
        Remove a session and its files.
        
        Returns:
            tuple: (success, error_message_or_none)
        """
        ...
    
    def log_to_wal(self, prompt: str, response: str, tokens: int, model: str) -> None:
        """Log transaction to Write-Ahead Log."""
        ...
```

### GenerationConfig Options
Available configuration presets in `llm/config.py`:

```python
from llm.config import GenerationConfig

# Presets
config = GenerationConfig.creative()      # High temperature, diverse outputs
config = GenerationConfig.balanced()      # Default settings
config = GenerationConfig.precise()       # Low temperature, focused outputs

# Custom configuration
config = GenerationConfig(
    temperature=0.7,
    top_p=0.9,
    top_k=40,
    max_output_tokens=8192
)
```

## Testing Strategy

### Test Structure
Tests are located in `tests/` directory:
- `test_clients_basic.py` - LLM client initialization and validation
- `test_config.py` - Configuration object tests
- `test_factory.py` - Factory pattern tests

### Running Tests
```bash
# Activate venv first
prepenv

# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_factory.py

# Run with verbose output
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src
```

### Mock Pattern for LLM Clients
When testing commands or session management without API calls:

```python
from unittest.mock import Mock, MagicMock
from session.chat_session import ChatSession

def test_command():
    # Mock LLM client
    mock_client = Mock()
    mock_response = MagicMock()
    mock_response.text = "Mocked response"
    mock_client.send_message.return_value = mock_response
    
    # Mock repository
    mock_repo = Mock()
    mock_repo.load_history.return_value = ([], None)
    
    # Test your command
    session = ChatSession(assistant, mock_repo)
    session._llm_client = mock_client
    response = session.send_message("test")
    
    assert response.text == "Mocked response"
    mock_client.send_message.assert_called_once()
```

### Testing New Commands
1. Create command implementation in `commands/`
2. Test in isolation with mocked repository
3. Test integration with real SessionManager
4. Verify console output using captured stdout
5. Test error cases (invalid input, missing sessions, etc.)

## Performance Considerations

### Session Size Limits
- **Max context tokens**: 32,768 (configurable per client)
- **Recommended session size**: < 500 messages (~15-20k tokens)
- **Warning thresholds**:
  - 75% capacity: Yellow warning
  - 90% capacity: Red warning
  - 95% capacity: Consider starting new session

### WAL File Management
- **Growth rate**: ~200 bytes per message exchange
- **Recommended cleanup**: Archive WAL when > 10MB
- **Future**: Automatic WAL rotation (planned)

**Manual WAL cleanup**:
```bash
# Backup current WAL
cp ~/.azor/azor-wal.json ~/.azor/azor-wal-backup-$(date +%Y%m%d).json

# Start fresh WAL (app will recreate)
rm ~/.azor/azor-wal.json
```

### Large Session Handling
For sessions with > 1000 messages:
- Use `/session clear` to start fresh while preserving session ID
- Export to PDF before clearing: `/pdf` then `/session clear`
- Consider archiving old session files manually

### Memory Optimization
- History is kept in memory during active session
- Switch sessions frequently if processing many long conversations
- Use `/session pop` to remove recent mistakes without clearing all history

### Disk I/O
- Session saves occur after **every** message (small overhead)
- WAL appends are atomic writes (minimal blocking)
- Audio generation is disk-intensive (use `/all-audio` sparingly)

## Troubleshooting Guide

### Common Error Messages

#### "Session log file does not exist"
**Cause**: Trying to load a non-existent session ID
**Solution**: 
- Use `/session list` to see available sessions
- Let the app create a new session (automatic)
- Check session ID for typos

#### "Cannot decode log file"
**Cause**: Corrupted JSON in session file
**Solution**:
1. Backup the corrupted file: `cp ~/.azor/<id>-log.json ~/.azor/<id>-log.json.backup`
2. Try manual JSON repair or delete the file
3. App will start fresh session with same ID

#### "No API key found for <provider>"
**Cause**: Missing environment variable in `.env`
**Solution**:
- For Gemini: Add `GEMINI_API_KEY=...`
- For OpenAI: Add `OPENAI_API_KEY=...`
- For Anthropic: Add `ANTHROPIC_API_KEY=...`
- Restart application after updating `.env`

#### "Model not found" or "Invalid model name"
**Cause**: Model name doesn't exist or typo in `.env`
**Solution**:
- Check provider documentation for valid model names
- Common valid names:
  - Gemini: `gemini-2.0-flash`, `gemini-1.5-pro`
  - OpenAI: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`
  - Anthropic: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`

#### "Context length exceeded"
**Cause**: Session history exceeded token limit
**Solution**:
- Use `/session pop` to remove recent messages
- Use `/session clear` to start fresh
- Use `/session new` to create a new session
- Export important conversations with `/pdf` first

#### "LLAMA_MODEL_PATH not set"
**Cause**: Local LLaMA selected but path not configured
**Solution**:
- Download a GGUF model file
- Add to `.env`: `LLAMA_MODEL_PATH=/full/path/to/model.gguf`
- Ensure file exists and is readable

#### "Failed to initialize audio"
**Cause**: coqui-tts or pydub issues
**Solution**:
- Check microphone/speaker permissions
- Reinstall audio dependencies: `pip install --upgrade coqui-tts pydub`
- On macOS: Install ffmpeg: `brew install ffmpeg`

### Debug Mode
Enable detailed logging:
```bash
# Set environment variable
export DEBUG=1
python src/run.py
```

### Checking Session Files
```bash
# List all sessions
ls -lh ~/.azor/*-log.json

# View session content
cat ~/.azor/<session-id>-log.json | jq .

# Check WAL size
ls -lh ~/.azor/azor-wal.json

# Count sessions
ls ~/.azor/*-log.json | wc -l
```

### Provider Connection Issues
Test provider connectivity:
```bash
# Test Gemini
python -c "from google import genai; client = genai.Client(api_key='YOUR_KEY'); print('OK')"

# Test OpenAI
python -c "from openai import OpenAI; client = OpenAI(api_key='YOUR_KEY'); print('OK')"

# Test Anthropic
python -c "from anthropic import Anthropic; client = Anthropic(api_key='YOUR_KEY'); print('OK')"
```

## Migration & Upgrade Paths

### History Format Changes
If the universal history format changes in future versions:

1. **Backup all sessions**:
   ```bash
   cp -r ~/.azor ~/.azor-backup-$(date +%Y%m%d)
   ```

2. **Use migration script** (future feature):
   ```bash
   python tools/migrate_history.py --from v1 --to v2
   ```

3. **Manual migration pattern**:
   ```python
   # Read old format
   with open('session-log.json') as f:
       old_data = json.load(f)
   
   # Convert to new format
   new_history = [
       {"role": msg["role"], "parts": [{"text": msg["text"]}]}
       for msg in old_data["history"]
   ]
   
   # Save new format
   new_data = {"history": new_history, ...}
   with open('session-log.json', 'w') as f:
       json.dump(new_data, f)
   ```

### Backwards Compatibility
- **Session files**: Major version changes may break compatibility
- **WAL format**: Append-only, older entries remain readable
- **Always backup** before upgrading to new major versions

### Provider Migration
Switching from one LLM provider to another:

1. Export important sessions: `/pdf` for each
2. Update `.env` with new provider credentials
3. Restart application
4. Old sessions will use new provider (history preserved)
5. **Note**: Different models may interpret history differently

## Important Notes & Gotchas

1. **Virtual Environment**: Always activate before running (`prepenv`)
2. **Colorama Isolation**: NEVER import colorama outside `cli/console.py`
3. **Command Naming**: Use underscores in filenames (`session_list.py` not `session-list.py`)
4. **Repository Injection**: Always pass repository to command functions (dependency injection)
5. **History Format**: Use universal format (role + parts) for cross-provider compatibility
6. **Session IDs**: Always UUID v4 format
7. **WAL Logging**: Every send_message() call logs to WAL immediately
8. **Cleanup**: `atexit` ensures session saves even on unexpected exit
9. **Polish Language**: UI messages are in Polish (app's original language)
10. **Protocol-Based Design**: Use protocols for testability and flexibility
11. **Token Limits**: Monitor token usage, different providers have different limits
12. **Audio Generation**: Resource-intensive, expect 2-5 seconds per message
13. **PDF Export**: Uses fpdf2, supports Polish characters via Unicode
14. **Session Switching**: Current session auto-saves before switching
15. **Error Tuples**: All repository methods return `(data, error_or_none)` for consistency

## Future Extensions

### Planned Features
- Voice input support (speech-to-text integration)
- Multi-modal message support (images, files via provider APIs)
- Session search and filtering by date/content
- Export to multiple formats (Markdown, HTML, plain text)
- Session sharing and collaboration (export/import)
- Custom assistant personalities beyond Azor
- Automatic WAL rotation and archiving
- Session analytics (token usage over time, most active sessions)
- Streaming responses for real-time output
- Plugin system for custom commands

### Contribution Guidelines
When adding features:
1. Follow existing architectural patterns
2. Add tests for new functionality
3. Update this documentation
4. Use type hints consistently
5. Keep commands modular and testable
6. Respect the protocol-based design
7. Maintain backwards compatibility when possible

