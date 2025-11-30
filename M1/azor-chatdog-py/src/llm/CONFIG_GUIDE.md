# LLM Configuration Guide

## Overview

The LLM module provides a flexible and extensible configuration system for controlling text generation parameters across different LLM providers (Gemini, LLaMA, OpenAI, etc.).

## Key Features

- **Unified Configuration**: `GenerationConfig` class works across all LLM clients
- **Validation**: Automatic parameter validation using Pydantic
- **Environment Variables**: Easy configuration via .env files
- **Presets**: Built-in presets for common use cases (creative, precise, balanced)
- **Type Safety**: Full type hints and runtime validation

## Configuration Classes

### GenerationConfig

Controls text generation behavior:

```python
from llm import GenerationConfig

# Create with default values
config = GenerationConfig.default()

# Create with custom values
config = GenerationConfig(
    temperature=0.8,
    top_p=0.95,
    top_k=40,
    max_tokens=2048
)

# Use presets
creative_config = GenerationConfig.creative()    # High creativity
precise_config = GenerationConfig.precise()      # Low temperature, focused
balanced_config = GenerationConfig.balanced()    # Balanced approach
```

### Parameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `temperature` | float | 0.0-2.0 | 0.7 | Controls randomness (0.0 = deterministic, 2.0 = very random) |
| `top_p` | float | 0.0-1.0 | 0.95 | Nucleus sampling threshold (cumulative probability) |
| `top_k` | int | ≥1 | 40 | Limits to top k tokens |
| `max_tokens` | int | ≥1 | 2048 | Maximum tokens to generate |
| `stop_sequences` | list[str] | - | None | Sequences that stop generation |

## Usage Examples

### Basic Usage

```python
from llm import GeminiLLMClient, LlamaClient, GenerationConfig

# Create client with custom config
config = GenerationConfig(temperature=0.9, top_p=0.95, max_tokens=1024)
client = GeminiLLMClient.from_environment()

# Create chat session with custom config
session = client.create_chat_session(
    system_instruction="You are a helpful assistant",
    generation_config=config
)

# Send message
response = session.send_message("Hello!")
print(response.text)
```

### Using Environment Variables

Add to your `.env` file:

```bash
# Gemini Configuration
GEMINI_API_KEY=your_api_key
MODEL_NAME=gemini-2.5-flash
GEMINI_TEMPERATURE=0.8
GEMINI_TOP_P=0.95
GEMINI_TOP_K=40
GEMINI_MAX_TOKENS=2048

# LLaMA Configuration
LLAMA_MODEL_PATH=/path/to/model.gguf
LLAMA_MODEL_NAME=llama-3.1-8b-instruct
LLAMA_GPU_LAYERS=1
LLAMA_CONTEXT_SIZE=2048
LLAMA_TEMPERATURE=0.7
LLAMA_TOP_P=0.95
LLAMA_TOP_K=40
LLAMA_MAX_TOKENS=2048
```

Then use in code:

```python
# Client will automatically load config from environment
client = GeminiLLMClient.from_environment()

# Config is loaded with GEMINI_ prefix
# temperature=0.8, top_p=0.95, etc.
```

### Per-Session Configuration

```python
# Client has default config from environment
client = LlamaClient.from_environment()

# Override config for specific session
creative_session = client.create_chat_session(
    system_instruction="Be creative!",
    generation_config=GenerationConfig.creative()
)

precise_session = client.create_chat_session(
    system_instruction="Be precise!",
    generation_config=GenerationConfig.precise()
)
```

### Advanced: Dynamic Configuration

```python
def get_config_for_task(task_type: str) -> GenerationConfig:
    """Return appropriate config based on task type."""
    if task_type == "creative_writing":
        return GenerationConfig(
            temperature=1.0,
            top_p=0.95,
            top_k=50,
            max_tokens=4096
        )
    elif task_type == "code_generation":
        return GenerationConfig(
            temperature=0.2,
            top_p=0.9,
            top_k=20,
            max_tokens=2048
        )
    elif task_type == "data_analysis":
        return GenerationConfig.precise()
    else:
        return GenerationConfig.default()

# Use dynamic config
task = "creative_writing"
config = get_config_for_task(task)
session = client.create_chat_session(
    system_instruction="Write creatively",
    generation_config=config
)
```

## Understanding Parameters

### Temperature

Controls randomness in token selection:

- **0.0**: Deterministic (always picks highest probability token)
- **0.3-0.5**: Focused, consistent responses
- **0.7-0.9**: Balanced creativity and coherence
- **1.0-2.0**: More random, creative, unpredictable

**Use cases:**
- Low (0.2-0.4): Code generation, factual Q&A, data extraction
- Medium (0.6-0.8): General conversation, balanced responses
- High (0.9-1.5): Creative writing, brainstorming, storytelling

### Top-P (Nucleus Sampling)

Selects from smallest set of tokens whose cumulative probability ≥ top_p:

- **0.9**: More focused, less diversity
- **0.95**: Balanced (recommended default)
- **1.0**: Consider all tokens

**Best practices:**
- Use with temperature for fine control
- Lower for factual tasks (0.9)
- Higher for creative tasks (0.95-1.0)

### Top-K

Limits consideration to top K most likely tokens:

- **10-20**: Very focused
- **40**: Balanced default
- **50-100**: More diversity

**Note:** Often used with top_p for best results

### Max Tokens

Maximum output length:

- Consider model's context window
- Include input + output in total
- Set based on expected response length

## Extending the System

### Adding a New LLM Client

1. Inherit from `BaseLLMClient`:

```python
from llm.base_client import BaseLLMClient
from llm.config import GenerationConfig

class MyLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, default_generation_config: Optional[GenerationConfig] = None):
        self.api_key = api_key
        self.default_generation_config = default_generation_config or GenerationConfig.default()
        self._client = self._initialize_client()
    
    @classmethod
    def from_environment(cls):
        load_dotenv()
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

2. Add environment variable support in `config.py` if needed

3. Export from `__init__.py`

### Adding New Parameters

To add a new parameter (e.g., `frequency_penalty`):

```python
# In config.py, add to GenerationConfig:
class GenerationConfig(BaseModel):
    # ...existing fields...
    
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
            raise ValueError("frequency_penalty must be between 0.0 and 2.0")
        return v
```

## Best Practices

1. **Use Environment Variables**: Keep sensitive data and configs in `.env`
2. **Use Presets**: Start with built-in presets, then customize
3. **Validate Configuration**: Pydantic ensures valid parameters
4. **Per-Session Configs**: Override defaults when needed
5. **Document Choices**: Comment why you chose specific parameters
6. **Test Different Configs**: Experiment to find optimal settings

## Troubleshooting

### Config Not Loading from Environment

```python
# Ensure .env is loaded
from dotenv import load_dotenv
load_dotenv()

# Check if variables are set
import os
print(os.getenv('LLAMA_TEMPERATURE'))  # Should print value
```

### Validation Errors

```python
try:
    config = GenerationConfig(temperature=3.0)  # Invalid!
except ValueError as e:
    print(f"Validation error: {e}")
```

### Parameter Not Taking Effect

- Check if client properly passes config to generation
- Verify model supports the parameter
- Check if parameter is actually used in API call

## Migration Guide

If you have existing code without configuration:

**Before:**
```python
client = LlamaClient.from_environment()
session = client.create_chat_session("Be helpful")
```

**After (with config):**
```python
client = LlamaClient.from_environment()  # Loads default config from env
session = client.create_chat_session(
    "Be helpful",
    generation_config=GenerationConfig.creative()  # Optional override
)
```

No breaking changes - defaults work out of the box!

## References

- [OpenAI API Parameters](https://platform.openai.com/docs/api-reference/chat/create)
- [Google Gemini Parameters](https://ai.google.dev/docs/concepts#model-parameters)
- [Temperature and Top-P Explained](https://docs.cohere.com/docs/temperature)

