"""
OpenAI LLM Client Implementation
Provides unified interface aligned with BaseLLMClient and GenerationConfig.
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from .config import GenerationConfig
from .base_client import BaseLLMClient
from cli import console

try:
    from openai import OpenAI  # openai>=1.0.0
except Exception:  # pragma: no cover - optional dependency resolution
    OpenAI = None


class OpenAIChatSession:
    """Chat session wrapper for OpenAI responses providing get_history() and send_message()."""

    def __init__(self, client: OpenAI, model_name: str, system_instruction: str, history: Optional[List[Dict]] = None, config: GenerationConfig = None):
        self._client = client
        self.model_name = model_name
        self.system_instruction = system_instruction or "You are a helpful assistant."
        self._history: List[Dict] = history or []
        self.config = config or GenerationConfig.default()

    def _build_messages(self) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        if self.system_instruction:
            messages.append({"role": "system", "content": self.system_instruction})
        for item in self._history:
            role = item.get("role")
            # Map internal roles (model -> assistant)
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
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                max_tokens=self.config.max_tokens,
                stop=self.config.stop_sequences
            )
            choice = response.choices[0]
            response_text = getattr(choice.message, "content", "")
            self._history.append({"role": "model", "parts": [{"text": response_text}]})
            return OpenAIResponse(response_text)
        except Exception as e:  # pragma: no cover - runtime failure path
            console.print_error(f"Błąd OpenAI: {e}")
            error_text = "Wystąpił błąd podczas generowania odpowiedzi OpenAI."
            self._history.append({"role": "model", "parts": [{"text": error_text}]})
            return OpenAIResponse(error_text)

    def get_history(self) -> List[Dict]:
        return self._history


class OpenAIResponse:
    def __init__(self, text: str):
        self.text = text


class OpenAILLMClient(BaseLLMClient):
    """
    OpenAI client wrapper supporting GenerationConfig mapping.

    Environment variables:
        OPENAI_API_KEY
        OPENAI_MODEL_NAME (default: gpt-4o-mini)
        OPENAI_TEMPERATURE, OPENAI_TOP_P, OPENAI_MAX_TOKENS, OPENAI_TOP_K (ignored by API), OPENAI_STOP_SEQUENCES
    """

    def __init__(self, model_name: str, api_key: str, default_generation_config: Optional[GenerationConfig] = None):
        if not api_key:
            raise ValueError("OPENAI_API_KEY cannot be empty")
        if OpenAI is None:
            raise RuntimeError("openai package not installed. Add 'openai' to requirements and install.")

        self.model_name = model_name
        self.api_key = api_key
        self.default_generation_config = default_generation_config or GenerationConfig.default()
        self._client = self._initialize_client()

    @staticmethod
    def preparing_for_use_message() -> str:
        return "🧠 Przygotowywanie klienta OpenAI..."

    @classmethod
    def from_environment(cls) -> "OpenAILLMClient":
        load_dotenv()
        model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY", "")
        gen_config = GenerationConfig.from_environment("OPENAI")
        console.print_info(f"Konfiguracja generowania OpenAI: {gen_config}")
        return cls(model_name=model_name, api_key=api_key, default_generation_config=gen_config)

    def _initialize_client(self) -> OpenAI:
        return OpenAI(api_key=self.api_key)

    def create_chat_session(self, system_instruction: str, history: Optional[List[Dict]] = None, thinking_budget: int = 0, generation_config: Optional[GenerationConfig] = None) -> OpenAIChatSession:
        config = generation_config or self.default_generation_config
        return OpenAIChatSession(client=self._client, model_name=self.model_name, system_instruction=system_instruction, history=history, config=config)

    def count_history_tokens(self, history: List[Dict]) -> int:
        # Rough estimation: approximate tokens by splitting (without actual tokenizer)
        if not history:
            return 0
        text = " ".join(part["text"] for msg in history for part in msg.get("parts", []))
        # Heuristic: avg 4 chars per token
        return max(1, len(text) // 4)

    def get_model_name(self) -> str:
        return self.model_name

    def is_available(self) -> bool:
        return self._client is not None and bool(self.api_key)

    def ready_for_use_message(self) -> str:
        masked = "****" if len(self.api_key) < 8 else f"{self.api_key[:4]}...{self.api_key[-4:]}"
        return f"✅ Klient OpenAI gotowy (Model: {self.model_name}, Key: {masked})"

    @property
    def client(self):  # compatibility
        return self._client

    def set_default_generation_config(self, config: GenerationConfig) -> None:
        self.default_generation_config = config

