"""
Anthropic Claude LLM Client Implementation
Unified interface via BaseLLMClient & GenerationConfig.
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from .config import GenerationConfig
from .base_client import BaseLLMClient
from cli import console

try:
    import anthropic  # anthropic>=0.34.0
except Exception:  # pragma: no cover
    anthropic = None


class AnthropicChatSession:
    """Chat session wrapper for Anthropic Claude responses."""

    def __init__(self, client: anthropic.Anthropic, model_name: str, system_instruction: str, history: Optional[List[Dict]] = None, config: GenerationConfig = None):
        self._client = client
        self.model_name = model_name
        self.system_instruction = system_instruction or "You are a helpful assistant."
        self._history: List[Dict] = history or []
        self.config = config or GenerationConfig.default()

    def _build_messages(self) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        # Convert universal history to Anthropic's format
        for item in self._history:
            role = item.get("role")
            if role == "model":
                role = "assistant"
            parts = item.get("parts", [])
            text = parts[0].get("text") if parts else ""
            if text:
                messages.append({"role": role, "content": text})
        return messages

    def send_message(self, text: str) -> Any:
        user_message = {"role": "user", "parts": [{"text": text}]}
        self._history.append(user_message)
        messages = self._build_messages()
        messages.append({"role": "user", "content": text})

        try:
            response = self._client.messages.create(
                model=self.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                system=self.system_instruction,
                messages=messages,
                stop_sequences=self.config.stop_sequences or []
            )
            # Anthropic returns content list
            content_blocks = getattr(response, "content", [])
            response_text = "".join(block.text for block in content_blocks if hasattr(block, "text"))
            self._history.append({"role": "model", "parts": [{"text": response_text}]})
            return AnthropicResponse(response_text)
        except Exception as e:  # pragma: no cover
            console.print_error(f"Błąd Anthropic: {e}")
            error_text = "Wystąpił błąd podczas generowania odpowiedzi Claude."
            self._history.append({"role": "model", "parts": [{"text": error_text}]})
            return AnthropicResponse(error_text)

    def get_history(self) -> List[Dict]:
        return self._history


class AnthropicResponse:
    def __init__(self, text: str):
        self.text = text


class AnthropicLLMClient(BaseLLMClient):
    """
    Anthropic client wrapper with GenerationConfig mapping.

    Environment variables:
        ANTHROPIC_API_KEY
        ANTHROPIC_MODEL_NAME (default: claude-3-5-sonnet-latest)
        Prefixed generation params: ANTHROPIC_TEMPERATURE, ANTHROPIC_TOP_P, ANTHROPIC_MAX_TOKENS, ANTHROPIC_TOP_K(ignored), ANTHROPIC_STOP_SEQUENCES
    """

    def __init__(self, model_name: str, api_key: str, default_generation_config: Optional[GenerationConfig] = None):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY cannot be empty")
        if anthropic is None:
            raise RuntimeError("anthropic package not installed. Add 'anthropic' to requirements.")

        self.model_name = model_name
        self.api_key = api_key
        self.default_generation_config = default_generation_config or GenerationConfig.default()
        self._client = self._initialize_client()

    @staticmethod
    def preparing_for_use_message() -> str:
        return "🧬 Przygotowywanie klienta Anthropic..."

    @classmethod
    def from_environment(cls) -> "AnthropicLLMClient":
        load_dotenv()
        model_name = os.getenv("ANTHROPIC_MODEL_NAME", "claude-3-5-sonnet-latest")
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        gen_config = GenerationConfig.from_environment("ANTHROPIC")
        console.print_info(f"Konfiguracja generowania Anthropic: {gen_config}")
        return cls(model_name=model_name, api_key=api_key, default_generation_config=gen_config)

    def _initialize_client(self) -> anthropic.Anthropic:
        return anthropic.Anthropic(api_key=self.api_key)

    def create_chat_session(self, system_instruction: str, history: Optional[List[Dict]] = None, thinking_budget: int = 0, generation_config: Optional[GenerationConfig] = None) -> AnthropicChatSession:
        config = generation_config or self.default_generation_config
        return AnthropicChatSession(client=self._client, model_name=self.model_name, system_instruction=system_instruction, history=history, config=config)

    def count_history_tokens(self, history: List[Dict]) -> int:
        if not history:
            return 0
        text = " ".join(part["text"] for msg in history for part in msg.get("parts", []))
        return max(1, len(text) // 4)

    def get_model_name(self) -> str:
        return self.model_name

    def is_available(self) -> bool:
        return self._client is not None and bool(self.api_key)

    def ready_for_use_message(self) -> str:
        masked = "****" if len(self.api_key) < 8 else f"{self.api_key[:4]}...{self.api_key[-4:]}"
        return f"✅ Klient Anthropic gotowy (Model: {self.model_name}, Key: {masked})"

    @property
    def client(self):
        return self._client

    def set_default_generation_config(self, config: GenerationConfig) -> None:
        self.default_generation_config = config

