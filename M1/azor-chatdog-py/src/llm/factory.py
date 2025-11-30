"""
Provider Factory for LLM Clients

Gives a unified way to create LLM clients by provider string, with optional
manual overrides and dynamic provider registration.

Usage Examples:

from llm.factory import create_llm_client, list_providers
from llm import GenerationConfig

client = create_llm_client("openai", api_key="sk-xxx", model_name="gpt-4o-mini")
creative = GenerationConfig.creative()
client2 = create_llm_client("llama", model_path="/models/llama.gguf", model_name="llama-3.1-8b", generation_config=creative)

# List available provider aliases
print(list_providers())

# Register a custom provider
class MyCustomClient:  # Must implement BaseLLMClient interface
    pass
# register_provider("mycustom", MyCustomClient)

Design Goals:
- Extensible: new providers can be registered dynamically.
- Safe: manual construction validates required arguments.
- Uniform: consistent interface across all providers.
"""

from __future__ import annotations

from typing import Dict, Type, Optional, List, Any
from .base_client import BaseLLMClient
from .config import GenerationConfig
from . import (
    GeminiLLMClient,
    LlamaClient,
    OpenAILLMClient,
    AnthropicLLMClient
)

# Internal mapping from normalized provider key to client class
_PROVIDER_CLASS_MAP: Dict[str, Type[BaseLLMClient]] = {
    "gemini": GeminiLLMClient,
    "google": GeminiLLMClient,
    "llama": LlamaClient,
    "openai": OpenAILLMClient,
    "anthropic": AnthropicLLMClient,
    "claude": AnthropicLLMClient,
}

# Required constructor arguments per provider when not using from_environment()
_REQUIRED_ARGS: Dict[str, List[str]] = {
    "gemini": ["api_key"],
    "google": ["api_key"],
    "openai": ["api_key"],
    "anthropic": ["api_key"],
    "claude": ["api_key"],
    "llama": ["model_path"],
}

# Model name defaults (if user provides api_key / model_path but omits model_name)
_DEFAULT_MODEL_NAMES: Dict[str, str] = {
    "gemini": "gemini-2.5-flash",
    "google": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-latest",
    "claude": "claude-3-5-sonnet-latest",
    "llama": "llama-3.1-8b-instruct",
}


def normalize_provider(provider: str) -> str:
    """Normalize provider string to canonical lower-case key."""
    return provider.strip().lower().replace("_", "-")


def list_providers() -> List[str]:
    """Return list of all provider aliases currently supported."""
    return sorted(set(_PROVIDER_CLASS_MAP.keys()))


def register_provider(name: str, cls: Type[BaseLLMClient]) -> None:
    """
    Register a new provider/client class at runtime.

    Args:
        name: Alias used in factory calls
        cls: Class implementing BaseLLMClient interface
    """
    key = normalize_provider(name)
    _PROVIDER_CLASS_MAP[key] = cls


def create_llm_client(
    provider: str,
    *,
    generation_config: Optional[GenerationConfig] = None,
    use_environment: bool = True,
    **kwargs: Any
) -> BaseLLMClient:
    """
    Create an LLM client for the given provider name.

    Args:
        provider: Provider alias (e.g. 'openai', 'gemini', 'llama', 'anthropic')
        generation_config: Optional GenerationConfig to override default
        use_environment: If True and no overriding kwargs for required fields, use .from_environment()
        **kwargs: Manual constructor overrides (api_key, model_name, model_path, n_gpu_layers, n_ctx, etc.)

    Returns:
        Instance of a class implementing BaseLLMClient

    Raises:
        ValueError: If provider unknown or required arguments missing

    Behavior:
        - If use_environment=True and not all required manual args provided, .from_environment() is used.
        - Otherwise manual construction occurs with validation of required args.
        - Provided generation_config becomes client's default_generation_config.
    """
    key = normalize_provider(provider)
    if key not in _PROVIDER_CLASS_MAP:
        raise ValueError(f"Unknown provider '{provider}'. Available: {', '.join(list_providers())}")

    client_cls = _PROVIDER_CLASS_MAP[key]

    # Determine canonical base key (e.g., 'claude' maps to 'anthropic' requirements)
    requirement_key = key if key in _REQUIRED_ARGS else {
        "google": "gemini",
        "claude": "anthropic",
    }.get(key, key)

    required = _REQUIRED_ARGS.get(requirement_key, [])

    # If manual overrides include all required params, build manually
    has_all_required = all(arg in kwargs and kwargs[arg] for arg in required)

    if use_environment and not has_all_required:
        client: BaseLLMClient = client_cls.from_environment()  # type: ignore
        # Runtime override of generation config if passed
        if generation_config is not None:
            client.set_default_generation_config(generation_config)
        return client

    # Manual construction path
    # Provide default model_name if missing and one is available
    if "model_name" not in kwargs or not kwargs.get("model_name"):
        kwargs["model_name"] = _DEFAULT_MODEL_NAMES.get(requirement_key)

    # Validate required args
    missing = [arg for arg in required if arg not in kwargs or not kwargs.get(arg)]
    if missing:
        raise ValueError(f"Missing required arguments for provider '{provider}': {missing}")

    # Provider-specific parameter adaptation
    ctor_kwargs = {}
    if requirement_key in ("gemini", "google"):
        ctor_kwargs = {
            "model_name": kwargs["model_name"],
            "api_key": kwargs["api_key"],
            "default_generation_config": generation_config,
        }
    elif requirement_key == "openai":
        ctor_kwargs = {
            "model_name": kwargs["model_name"],
            "api_key": kwargs["api_key"],
            "default_generation_config": generation_config,
        }
    elif requirement_key in ("anthropic", "claude"):
        ctor_kwargs = {
            "model_name": kwargs["model_name"],
            "api_key": kwargs["api_key"],
            "default_generation_config": generation_config,
        }
    elif requirement_key == "llama":
        ctor_kwargs = {
            "model_name": kwargs["model_name"],
            "model_path": kwargs["model_path"],
            "n_gpu_layers": kwargs.get("n_gpu_layers", 1),
            "n_ctx": kwargs.get("n_ctx", 2048),
            "default_generation_config": generation_config,
        }

    client = client_cls(**ctor_kwargs)  # type: ignore[arg-type]
    return client

__all__ = [
    "create_llm_client",
    "register_provider",
    "list_providers",
    "normalize_provider",
]

