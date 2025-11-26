"""
Google Gemini LLM Client Implementation
Encapsulates all Google Gemini AI interactions.
"""

import os
import sys
from typing import Optional, List, Any, Dict
from google import genai
from google.genai import types
from dotenv import load_dotenv
from cli import console
from .gemini_validation import GeminiConfig
from .config import GenerationConfig
from .base_client import BaseLLMClient

class GeminiChatSessionWrapper:
    """
    Wrapper for Gemini chat session that provides universal dictionary-based history format.
    This ensures compatibility with LlamaClient's history format.
    """
    
    def __init__(self, gemini_session):
        """
        Initialize wrapper with Gemini chat session.
        
        Args:
            gemini_session: The actual Gemini chat session object
        """
        self.gemini_session = gemini_session
    
    def send_message(self, text: str) -> Any:
        """
        Forwards message to Gemini session.
        
        Args:
            text: User's message
            
        Returns:
            Response object from Gemini
        """
        return self.gemini_session.send_message(text)
    
    def get_history(self) -> List[Dict]:
        """
        Gets conversation history in universal dictionary format.
        
        Returns:
            List of dictionaries with format: {"role": "user|model", "parts": [{"text": "..."}]}
        """
        gemini_history = self.gemini_session.get_history()
        universal_history = []
        
        for content in gemini_history:
            # Convert Gemini Content object to universal dictionary format
            text_part = ""
            if hasattr(content, 'parts') and content.parts:
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_part = part.text
                        break
            
            if text_part:
                universal_content = {
                    "role": content.role,
                    "parts": [{"text": text_part}]
                }
                universal_history.append(universal_content)
        
        return universal_history

class GeminiLLMClient(BaseLLMClient):
    """
    Encapsulates all Google Gemini AI interactions.
    Provides a clean interface for chat sessions, token counting, and configuration.
    """
    
    def __init__(self, model_name: str, api_key: str, default_generation_config: Optional[GenerationConfig] = None):
        """
        Initialize the Gemini LLM client with explicit parameters.
        
        Args:
            model_name: Model to use (e.g., 'gemini-2.5-flash')
            api_key: Google Gemini API key
            default_generation_config: Default generation configuration for all sessions

        Raises:
            ValueError: If api_key is empty or None
        """
        if not api_key:
            raise ValueError("API key cannot be empty or None")
        
        self.model_name = model_name
        self.api_key = api_key
        self.default_generation_config = default_generation_config if default_generation_config is not None else GenerationConfig.default()

        # Initialize the client during construction
        self._client = self._initialize_client()
    
    @staticmethod
    def preparing_for_use_message() -> str:
        """
        Returns a message indicating that Gemini client is being prepared.
        
        Returns:
            Formatted preparation message string
        """
        return "🤖 Przygotowywanie klienta Gemini..."
    
    @classmethod
    def from_environment(cls) -> 'GeminiLLMClient':
        """
        Factory method that creates a GeminiLLMClient instance from environment variables.
        
        Returns:
            GeminiLLMClient instance initialized with environment variables
            
        Raises:
            ValueError: If required environment variables are not set
        """
        load_dotenv()
    
        # Walidacja z Pydantic
        config = GeminiConfig(
            model_name=os.getenv('MODEL_NAME', 'gemini-2.5-flash'),
            gemini_api_key=os.getenv('GEMINI_API_KEY', '')
        )
        
        # Load generation config from environment
        generation_config = GenerationConfig.from_environment("GEMINI")

        console.print_info(f"Konfiguracja generowania Gemini: {generation_config}")

        return cls(
            model_name=config.model_name,
            api_key=config.gemini_api_key,
            default_generation_config=generation_config
        )

    def _initialize_client(self) -> genai.Client:
        """
        Initializes the Google GenAI client.
        
        Returns:
            Initialized GenAI client
            
        Raises:
            SystemExit: If client initialization fails
        """
        try:
            return genai.Client()
        except Exception as e:
            console.print_error(f"Błąd inicjalizacji klienta Gemini: {e}")
            sys.exit(1)
    
    def create_chat_session(self, 
                          system_instruction: str, 
                          history: Optional[List[Dict]] = None,
                          thinking_budget: int = 0,
                          generation_config: Optional[GenerationConfig] = None) -> GeminiChatSessionWrapper:
        """
        Creates a new chat session with the specified configuration.
        
        Args:
            system_instruction: System role/prompt for the assistant
            history: Previous conversation history (optional, in universal dict format)
            thinking_budget: Thinking budget for the model
            generation_config: Generation configuration (uses default if not provided)

        Returns:
            GeminiChatSessionWrapper with universal dictionary-based interface
        """
        if not self._client:
            raise RuntimeError("LLM client not initialized")
        
        # Use provided config, or fall back to default
        config = generation_config if generation_config is not None else self.default_generation_config

        # Convert universal dict format to Gemini Content objects
        gemini_history = []
        if history:
            for entry in history:
                if isinstance(entry, dict) and 'role' in entry and 'parts' in entry:
                    text = entry['parts'][0].get('text', '') if entry['parts'] else ''
                    if text:
                        content = types.Content(
                            role=entry['role'],
                            parts=[types.Part.from_text(text=text)]
                        )
                        gemini_history.append(content)
        
        # Build generation config for Gemini
        gemini_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_tokens,
            stop_sequences=config.stop_sequences
        )

        gemini_session = self._client.chats.create(
            model=self.model_name,
            history=gemini_history,
            config=gemini_config
        )
        
        return GeminiChatSessionWrapper(gemini_session)
    
    def count_history_tokens(self, history: List[Dict]) -> int:
        """
        Counts tokens for the given conversation history.
        
        Args:
            history: Conversation history in universal dict format
            
        Returns:
            Total token count
        """
        if not history:
            return 0
        
        try:
            # Convert universal dict format to Gemini Content objects for token counting
            gemini_history = []
            for entry in history:
                if isinstance(entry, dict) and 'role' in entry and 'parts' in entry:
                    text = entry['parts'][0].get('text', '') if entry['parts'] else ''
                    if text:
                        content = types.Content(
                            role=entry['role'],
                            parts=[types.Part.from_text(text=text)]
                        )
                        gemini_history.append(content)
            
            response = self._client.models.count_tokens(
                model=self.model_name,
                contents=gemini_history
            )
            return response.total_tokens
        except Exception as e:
            console.print_error(f"Błąd podczas liczenia tokenów: {e}")
            return 0
    
    def get_model_name(self) -> str:
        """Returns the currently configured model name."""
        return self.model_name
    
    def is_available(self) -> bool:
        """
        Checks if the LLM service is available and properly configured.
        
        Returns:
            True if client is properly initialized and has API key
        """
        return self._client is not None and bool(self.api_key)
    
    def ready_for_use_message(self) -> str:
        """
        Returns a ready-to-use message with model info and masked API key.
        
        Returns:
            Formatted message string for display
        """
        # Mask API key - show first 4 and last 4 characters
        if len(self.api_key) <= 8:
            masked_key = "****"
        else:
            masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}"
        
        return f"✅ Klient Gemini gotowy do użycia (Model: {self.model_name}, Key: {masked_key})"
    
    @property
    def client(self):
        """
        Provides access to the underlying GenAI client for backwards compatibility.
        This property should be used sparingly and eventually removed.
        """
        return self._client

    def set_default_generation_config(self, config: GenerationConfig) -> None:
        """Update default generation configuration at runtime."""
        self.default_generation_config = config
