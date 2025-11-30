# LLM Module

A flexible, extensible, and well-architected module for interacting with various Large Language Models (LLMs) with unified configuration management.

## Features

✨ **Unified Configuration**: Single `GenerationConfig` class works across all LLM providers  
🔧 **Flexible & Extensible**: Easy to add new LLM providers  
🛡️ **Type-Safe**: Full type hints and Pydantic validation  
🎯 **Presets**: Built-in configurations for common use cases  
🌍 **Environment Support**: Load configurations from `.env` files  
📚 **Well-Documented**: Comprehensive documentation and examples  
🧪 **Tested**: Unit tests for all core functionality  

## Architecture

The module follows SOLID principles and clean architecture patterns:

```
src/llm/
├── base_client.py          # Abstract base classes (interfaces)
├── config.py               # Configuration classes with validation
├── gemini_client.py        # Google Gemini implementation
├── llama_client.py         # LLaMA (llama-cpp-python) implementation
├── gemini_validation.py    # Gemini-specific validation
├── llama_validation.py     # LLaMA-specific validation
└── __init__.py            # Public API exports
```

## Core Components

### 1. GenerationConfig

Central configuration class for controlling LLM generation:

```python
from llm import GenerationConfig

# Use defaults
config = GenerationConfig.default()

# Use presets
creative_config = GenerationConfig.creative()
precise_config = GenerationConfig.precise()

# Custom configuration
config = GenerationConfig(
    temperature=0.8,
    top_p=0.95,
    top_k=40,
    max_tokens=2048
)
```

**Parameters:**
- `temperature` (0.0-2.0): Controls randomness
- `top_p` (0.0-1.0): Nucleus sampling threshold
- `top_k` (≥1): Top-k sampling parameter
- `max_tokens` (≥1): Maximum output length
- `stop_sequences`: List of stop sequences

### 2. BaseLLMClient

Abstract interface that all LLM clients implement:

```python
class BaseLLMClient(ABC):
    @abstractmethod
    def create_chat_session(
        self, 
        system_instruction: str,
        history: Optional[List[Dict]] = None,
        thinking_budget: int = 0,
        generation_config: Optional[GenerationConfig] = None
    ) -> Any:
        pass
    
    @abstractmethod
    def count_history_tokens(self, history: List[Dict]) -> int:
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        pass
```

### 3. LLM Clients

#### GeminiLLMClient

```python
from llm import GeminiLLMClient, GenerationConfig

# Initialize from environment
client = GeminiLLMClient.from_environment()

# Create chat session with custom config
session = client.create_chat_session(
    system_instruction="You are a helpful assistant",
    generation_config=GenerationConfig.creative()
)

response = session.send_message("Hello!")
print(response.text)
```

#### LlamaClient

```python
from llm import LlamaClient, GenerationConfig

# Initialize from environment
client = LlamaClient.from_environment()

# Create chat session
session = client.create_chat_session(
    system_instruction="You are a coding assistant",
    generation_config=GenerationConfig(temperature=0.2)
)

response = session.send_message("Write a Python function")
print(response.text)
```

## Usage Guide

### Quick Start

1. **Set up environment variables:**

```bash
# Copy example and fill in values
cp .env.example .env
```

2. **Basic usage:**

```python
from llm import GeminiLLMClient

# Client loads config from environment automatically
client = GeminiLLMClient.from_environment()

# Create session
session = client.create_chat_session("You are helpful")

# Chat
response = session.send_message("Hello!")
print(response.text)
```

### Using Presets

```python
from llm import GenerationConfig

# For creative writing
creative = GenerationConfig.creative()
# temperature=0.9, top_p=0.95, top_k=50

# For precise, factual responses
precise = GenerationConfig.precise()
# temperature=0.3, top_p=0.9, top_k=20

# Balanced approach
balanced = GenerationConfig.balanced()
# temperature=0.7, top_p=0.95, top_k=40
```

### Environment Configuration

Add to `.env`:

```bash
# Gemini
GEMINI_API_KEY=your_key
GEMINI_TEMPERATURE=0.7
GEMINI_TOP_P=0.95
GEMINI_TOP_K=40
GEMINI_MAX_TOKENS=2048

# LLaMA
LLAMA_MODEL_PATH=/path/to/model.gguf
LLAMA_TEMPERATURE=0.7
LLAMA_TOP_P=0.95
LLAMA_TOP_K=40
LLAMA_MAX_TOKENS=2048
```

Then load automatically:

```python
client = GeminiLLMClient.from_environment()
# Config is loaded automatically from GEMINI_* variables
```

### Per-Session Configuration

```python
# Client has default config
client = LlamaClient.from_environment()

# Override for specific sessions
creative_session = client.create_chat_session(
    "Be creative",
    generation_config=GenerationConfig.creative()
)

precise_session = client.create_chat_session(
    "Be precise",
    generation_config=GenerationConfig.precise()
)
```

## Provider Factory

A unified way to instantiate clients by provider alias.

```python
from llm.factory import create_llm_client, list_providers
from llm import GenerationConfig

print(list_providers())  # ['anthropic', 'claude', 'gemini', 'google', 'llama', 'openai']

# Environment-based (uses .from_environment())
openai_client = create_llm_client("openai")

# Manual construction (all required args provided -> no env needed)
llama_client = create_llm_client(
    "llama",
    model_path="/models/llama/llama-3.1-8b-instruct.gguf",
    model_name="llama-3.1-8b-instruct",
    generation_config=GenerationConfig.precise()
)

# Override default config at creation
gemini_client = create_llm_client(
    "gemini",
    api_key="gem-key-1234",
    model_name="gemini-2.5-flash",
    generation_config=GenerationConfig.creative()
)

# Register custom provider
from llm.base_client import BaseLLMClient
from llm.factory import register_provider

class MyCustomLLM(BaseLLMClient):
    def __init__(self, default_generation_config=None):
        self.default_generation_config = default_generation_config or GenerationConfig.default()
    @staticmethod
    def preparing_for_use_message(): return "Custom prep"
    @classmethod
    def from_environment(cls): return cls()
    def create_chat_session(self, system_instruction, history=None, thinking_budget=0, generation_config=None): pass
    def count_history_tokens(self, history): return 0
    def get_model_name(self): return "my-custom"
    def is_available(self): return True
    def ready_for_use_message(self): return "Ready"
    def set_default_generation_config(self, config): self.default_generation_config = config

register_provider("mycustom", MyCustomLLM)
print("mycustom" in list_providers())  # True
```

## Design Principles

### 1. **Separation of Concerns**
- Configuration logic separated from client logic
- Validation separated from business logic
- Each client handles its own provider-specific details

### 2. **Open/Closed Principle**
- Easy to extend with new LLM providers
- Configuration system supports new parameters without breaking existing code

### 3. **Dependency Inversion**
- Depend on abstractions (`BaseLLMClient`) not concrete implementations
- Easy to swap LLM providers

### 4. **Single Responsibility**
- `GenerationConfig`: Configuration and validation
- `*Client`: LLM interaction
- `*Validation`: Provider-specific validation

### 5. **DRY (Don't Repeat Yourself)**
- Shared configuration logic in `GenerationConfig`
- Common patterns in base classes
- Reusable presets

## Extensibility

### Adding a New LLM Provider

1. **Create client class:**

```python
from llm.base_client import BaseLLMClient
from llm.config import GenerationConfig

class MyLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, 
                 default_generation_config: Optional[GenerationConfig] = None):
        self.api_key = api_key
        self.default_generation_config = (
            default_generation_config or GenerationConfig.default()
        )
    
    @classmethod
    def from_environment(cls):
        config = GenerationConfig.from_environment("MYLLM")
        return cls(
            api_key=os.getenv('MYLLM_API_KEY'),
            default_generation_config=config
        )
    
    def create_chat_session(self, system_instruction, history=None,
                          thinking_budget=0, generation_config=None):
        config = generation_config or self.default_generation_config
        # Use config.temperature, config.top_p, etc.
        ...
```

2. **Export from `__init__.py`:**

```python
from .my_llm_client import MyLLMClient
__all__ = [..., 'MyLLMClient']
```

### Adding New Configuration Parameters

```python
class GenerationConfig(BaseModel):
    # Existing fields...
    
    frequency_penalty: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Penalize frequent tokens"
    )
    
    @field_validator('frequency_penalty')
    @classmethod
    def validate_frequency_penalty(cls, v):
        if v is not None and not 0.0 <= v <= 2.0:
            raise ValueError("frequency_penalty must be 0.0-2.0")
        return v
```

## Testing

Run tests:

```bash
pytest tests/test_config.py -v
```

Coverage:
- Configuration validation
- Preset configurations
- Environment variable loading
- Edge cases and boundary values

## Documentation

- **[CONFIG_GUIDE.md](CONFIG_GUIDE.md)**: Comprehensive configuration guide
- **[examples/config_usage_examples.py](../examples/config_usage_examples.py)**: Working examples
- **[.env.example](../.env.example)**: Environment variable template

## Best Practices

1. ✅ **Use environment variables** for configuration
2. ✅ **Start with presets**, customize as needed
3. ✅ **Validate configurations** before use (automatic with Pydantic)
4. ✅ **Document parameter choices** in comments
5. ✅ **Test different configurations** for your use case
6. ✅ **Use per-session configs** when you need different behaviors

## Parameter Recommendations

### By Task Type

| Task | Temperature | Top-P | Top-K | Example |
|------|------------|-------|-------|---------|
| Code Generation | 0.2-0.4 | 0.9 | 20 | `GenerationConfig(temperature=0.3)` |
| Factual Q&A | 0.3-0.5 | 0.9 | 20 | `GenerationConfig.precise()` |
| Conversation | 0.6-0.8 | 0.95 | 40 | `GenerationConfig.balanced()` |
| Creative Writing | 0.9-1.2 | 0.95 | 50 | `GenerationConfig.creative()` |
| Brainstorming | 1.0-1.5 | 0.95 | 60 | `GenerationConfig(temperature=1.2)` |

## Troubleshooting

### Configuration not loading from environment

```python
# Ensure .env is loaded
from dotenv import load_dotenv
load_dotenv()

# Check variables
import os
print(os.getenv('GEMINI_TEMPERATURE'))
```

### Validation errors

```python
try:
    config = GenerationConfig(temperature=5.0)  # Invalid!
except ValueError as e:
    print(f"Error: {e}")
```

### Parameters not taking effect

- Verify the LLM provider supports the parameter
- Check that config is passed to `create_chat_session()`
- Ensure client properly applies config in generation

## Contributing

When adding new features:

1. Follow existing patterns and architecture
2. Add type hints and documentation
3. Include validation for new parameters
4. Write unit tests
5. Update documentation and examples

## License

[Your license here]

## Related Resources

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [LLM Parameter Tuning Guide](https://docs.cohere.com/docs/temperature)
- [Google Gemini API](https://ai.google.dev/docs)
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
