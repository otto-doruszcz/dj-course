"""
Base LLM Client Interface
Defines the contract that all LLM clients must implement for consistency.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from .config import GenerationConfig


class BaseLLMClient(ABC):
    """
    Abstract base class for all LLM clients.

    This interface ensures that all LLM clients (Gemini, LLaMA, OpenAI, etc.)
    provide a consistent API for interacting with language models.

    All concrete implementations must provide:
    - Client initialization from environment variables
    - Chat session creation with configurable parameters
    - Token counting functionality
    - Model availability checking
    - Status messages for user feedback

    Added ability to update default generation configuration at runtime.
    """

    @abstractmethod
    def __init__(self, *args, default_generation_config: Optional[GenerationConfig] = None, **kwargs):
        """
        Initialize the LLM client.

        Args:
            default_generation_config: Default generation configuration for all sessions
        """
        pass

    @classmethod
    @abstractmethod
    def from_environment(cls) -> 'BaseLLMClient':
        """
        Factory method that creates a client instance from environment variables.

        Returns:
            Client instance initialized with environment variables

        Raises:
            ValueError: If required environment variables are not set
        """
        pass

    @staticmethod
    @abstractmethod
    def preparing_for_use_message() -> str:
        """
        Returns a message indicating that the client is being prepared.

        Returns:
            Formatted preparation message string
        """
        pass

    @abstractmethod
    def create_chat_session(
        self,
        system_instruction: str,
        history: Optional[List[Dict]] = None,
        thinking_budget: int = 0,
        generation_config: Optional[GenerationConfig] = None
    ) -> Any:
        """
        Creates a new chat session with the specified configuration.

        Args:
            system_instruction: System role/prompt for the assistant
            history: Previous conversation history (optional)
            thinking_budget: Thinking budget for the model (if supported)
            generation_config: Generation configuration (uses default if not provided)

        Returns:
            Chat session object with send_message() and get_history() methods
        """
        pass

    @abstractmethod
    def count_history_tokens(self, history: List[Dict]) -> int:
        """
        Counts tokens for the given conversation history.

        Args:
            history: Conversation history in universal dict format

        Returns:
            Total token count
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Returns the currently configured model name.

        Returns:
            Model name string
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Checks if the LLM service is available and properly configured.

        Returns:
            True if service is available, False otherwise
        """
        pass

    @abstractmethod
    def ready_for_use_message(self) -> str:
        """
        Returns a ready-to-use message with model info.

        Returns:
            Formatted message string for display
        """
        pass

    @abstractmethod
    def set_default_generation_config(self, config: GenerationConfig) -> None:
        """Update the client's default generation configuration at runtime."""
        pass


class BaseChatSession(ABC):
    """
    Abstract base class for chat sessions.

    All chat sessions must provide:
    - Message sending functionality
    - Conversation history access
    """

    @abstractmethod
    def send_message(self, text: str) -> Any:
        """
        Sends a message and returns a response object.

        Args:
            text: User's message

        Returns:
            Response object with .text attribute containing the response
        """
        pass

    @abstractmethod
    def get_history(self) -> List[Dict]:
        """
        Returns the current conversation history.

        Returns:
            List of dictionaries with format: {"role": "user|model", "parts": [{"text": "..."}]}
        """
        pass
