"""Basic tests for new OpenAI and Anthropic client wrappers.
These are structural tests that do not hit real APIs; they mock underlying SDKs.
"""
from typing import List, Dict
import pytest
from unittest.mock import MagicMock, patch

from llm.config import GenerationConfig
from llm.openai_client import OpenAILLMClient
from llm.anthropic_client import AnthropicLLMClient


@pytest.fixture
def sample_history() -> List[Dict]:
    return [
        {"role": "user", "parts": [{"text": "Hello"}]},
        {"role": "model", "parts": [{"text": "Hi there"}]},
        {"role": "user", "parts": [{"text": "Tell me a joke"}]},
    ]


def test_openai_client_token_count(sample_history):
    with patch("llm.openai_client.OpenAI") as mock_sdk:
        mock_sdk.return_value = MagicMock()
        client = OpenAILLMClient(model_name="gpt-4o-mini", api_key="sk-test")
        tokens = client.count_history_tokens(sample_history)
        assert tokens > 0


def test_openai_chat_session_send_message(sample_history):
    with patch("llm.openai_client.OpenAI") as mock_sdk:
        mock_instance = MagicMock()
        # Mock response structure
        mock_instance.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="Test response"))])
        mock_sdk.return_value = mock_instance
        client = OpenAILLMClient(model_name="gpt-4o-mini", api_key="sk-test")
        session = client.create_chat_session("System role", history=sample_history, generation_config=GenerationConfig.precise())
        resp = session.send_message("Ping")
        assert hasattr(resp, "text")
        assert "Test response" in resp.text


def test_anthropic_client_token_count(sample_history):
    with patch("llm.anthropic_client.anthropic") as mock_sdk:
        mock_sdk.Anthropic.return_value = MagicMock()
        client = AnthropicLLMClient(model_name="claude-3-5-sonnet-latest", api_key="ak-test")
        tokens = client.count_history_tokens(sample_history)
        assert tokens > 0


def test_anthropic_chat_session_send_message(sample_history):
    with patch("llm.anthropic_client.anthropic") as mock_sdk:
        mock_instance = MagicMock()
        # Mock response content blocks
        block = MagicMock()
        block.text = "Claude mówi: odpowiedź"
        mock_instance.messages.create.return_value = MagicMock(content=[block])
        mock_sdk.Anthropic.return_value = mock_instance
        client = AnthropicLLMClient(model_name="claude-3-5-sonnet-latest", api_key="ak-test")
        session = client.create_chat_session("System role", history=sample_history, generation_config=GenerationConfig.creative())
        resp = session.send_message("Ping")
        assert hasattr(resp, "text")
        assert "Claude" in resp.text


def test_set_default_generation_config_runtime():
    with patch("llm.openai_client.OpenAI") as mock_sdk:
        mock_sdk.return_value = MagicMock()
        client = OpenAILLMClient(model_name="gpt-4o-mini", api_key="sk-test")
        old_temp = client.default_generation_config.temperature
        new_conf = GenerationConfig(temperature=1.2, top_p=0.9, max_tokens=512)
        client.set_default_generation_config(new_conf)
        assert client.default_generation_config.temperature == 1.2
        assert client.default_generation_config.temperature != old_temp


