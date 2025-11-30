"""Tests for LLM provider factory helpers."""
import pytest
from unittest.mock import patch, MagicMock

from llm.factory import create_llm_client, list_providers, register_provider
from llm.config import GenerationConfig
from llm.base_client import BaseLLMClient


def test_list_providers_contains_expected():
    providers = list_providers()
    for expected in ["openai", "gemini", "llama", "anthropic", "google", "claude"]:
        assert expected in providers


def test_factory_manual_llama():
    with patch("llm.llama_client.Llama") as mock_llama:
        mock_llama.return_value = MagicMock()
        client = create_llm_client(
            "llama",
            model_path="/tmp/model.gguf",
            model_name="llama-3.1-8b-instruct",
            generation_config=GenerationConfig.precise(),
            use_environment=False
        )
        assert client.get_model_name().startswith("llama")


def test_factory_environment_fallback_openai():
    with patch("llm.openai_client.OpenAI") as mock_sdk, patch("dotenv.load_dotenv"):
        mock_sdk.return_value = MagicMock()
        # Missing api_key triggers from_environment path; patch env
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env", "OPENAI_MODEL_NAME": "gpt-4o-mini"}):
            client = create_llm_client("openai")
            assert client.is_available()


def test_factory_manual_openai():
    with patch("llm.openai_client.OpenAI") as mock_sdk:
        mock_sdk.return_value = MagicMock()
        client = create_llm_client(
            "openai",
            api_key="sk-manual",
            model_name="gpt-4o-mini",
            generation_config=GenerationConfig.creative(),
            use_environment=False
        )
        assert client.default_generation_config.temperature == 0.9


def test_register_custom_provider():
    class DummyClient(BaseLLMClient):
        def __init__(self, default_generation_config=None):
            self.default_generation_config = default_generation_config or GenerationConfig.default()
        @staticmethod
        def preparing_for_use_message(): return "prep"
        @classmethod
        def from_environment(cls): return cls()
        def create_chat_session(self, system_instruction, history=None, thinking_budget=0, generation_config=None): return None
        def count_history_tokens(self, history): return 0
        def get_model_name(self): return "dummy"
        def is_available(self): return True
        def ready_for_use_message(self): return "ready"
        def set_default_generation_config(self, config): self.default_generation_config = config

    register_provider("dummy", DummyClient)
    assert "dummy" in list_providers()
    client = create_llm_client("dummy", use_environment=True)
    assert isinstance(client, DummyClient)


def test_missing_required_args_manual():
    # llama requires model_path when manual
    with pytest.raises(ValueError):
        create_llm_client("llama", use_environment=False)


def test_unknown_provider():
    with pytest.raises(ValueError):
        create_llm_client("unknown-provider")

