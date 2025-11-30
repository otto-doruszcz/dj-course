"""
LLM Generation Configuration
Provides configuration classes for LLM generation parameters with validation.
Uses Pydantic for robust validation and type safety.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class GenerationConfig(BaseModel):
    """
    Configuration for LLM text generation parameters.
    
    This class encapsulates all generation parameters that can be used across
    different LLM providers (Gemini, LLaMA, OpenAI, etc.) with sensible defaults
    and validation.
    
    Attributes:
        temperature: Controls randomness (0.0 = deterministic, 2.0 = very random)
        top_p: Nucleus sampling threshold (0.0-1.0)
        top_k: Top-k sampling parameter (limits to top k tokens)
        max_tokens: Maximum number of tokens to generate
        stop_sequences: List of sequences that will stop generation
    """
    
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Controls randomness in generation (0.0 = deterministic, 2.0 = very random)"
    )
    
    top_p: Optional[float] = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling: cumulative probability threshold"
    )
    
    top_k: Optional[int] = Field(
        default=40,
        ge=1,
        description="Top-k sampling: number of top tokens to consider"
    )
    
    max_tokens: int = Field(
        default=2048,
        ge=1,
        le=128000,
        description="Maximum number of tokens to generate"
    )
    
    stop_sequences: Optional[list[str]] = Field(
        default=None,
        description="Sequences that will stop generation when encountered"
    )
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Ensure temperature is within valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v
    
    @field_validator('top_p')
    @classmethod
    def validate_top_p(cls, v: Optional[float]) -> Optional[float]:
        """Ensure top_p is within valid range if provided."""
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("top_p must be between 0.0 and 1.0")
        return v
    
    @field_validator('top_k')
    @classmethod
    def validate_top_k(cls, v: Optional[int]) -> Optional[int]:
        """Ensure top_k is positive if provided."""
        if v is not None and v < 1:
            raise ValueError("top_k must be at least 1")
        return v
    
    @classmethod
    def default(cls) -> 'GenerationConfig':
        """
        Returns a default configuration with balanced parameters.
        
        Returns:
            GenerationConfig with default values
        """
        return cls()
    
    @classmethod
    def creative(cls) -> 'GenerationConfig':
        """
        Returns a configuration optimized for creative, diverse outputs.
        Higher temperature and nucleus sampling for more varied responses.
        
        Returns:
            GenerationConfig with creative parameters
        """
        return cls(
            temperature=0.9,
            top_p=0.95,
            top_k=50,
            max_tokens=2048
        )
    
    @classmethod
    def precise(cls) -> 'GenerationConfig':
        """
        Returns a configuration optimized for precise, deterministic outputs.
        Lower temperature for more focused and consistent responses.
        
        Returns:
            GenerationConfig with precise parameters
        """
        return cls(
            temperature=0.3,
            top_p=0.9,
            top_k=20,
            max_tokens=2048
        )
    
    @classmethod
    def balanced(cls) -> 'GenerationConfig':
        """
        Returns a balanced configuration between creativity and precision.
        
        Returns:
            GenerationConfig with balanced parameters
        """
        return cls(
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_tokens=2048
        )
    
    @classmethod
    def from_environment(cls, prefix: str = "") -> 'GenerationConfig':
        """
        Creates a GenerationConfig from environment variables.
        
        Environment variables (with optional prefix):
            {PREFIX}_TEMPERATURE: float (0.0-2.0)
            {PREFIX}_TOP_P: float (0.0-1.0)
            {PREFIX}_TOP_K: int (>= 1)
            {PREFIX}_MAX_TOKENS: int (>= 1)
        
        Args:
            prefix: Optional prefix for environment variables (e.g., "LLAMA")
            
        Returns:
            GenerationConfig initialized from environment or defaults
            
        Example:
            config = GenerationConfig.from_environment("LLAMA")
            # Will read LLAMA_TEMPERATURE, LLAMA_TOP_P, etc.
        """
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        def get_env_float(key: str, default: float) -> float:
            value = os.getenv(key)
            return float(value) if value else default
        
        def get_env_int(key: str, default: int) -> int:
            value = os.getenv(key)
            return int(value) if value else default
        
        prefix_str = f"{prefix}_" if prefix else ""
        
        return cls(
            temperature=get_env_float(f"{prefix_str}TEMPERATURE", 0.7),
            top_p=get_env_float(f"{prefix_str}TOP_P", 0.95),
            top_k=get_env_int(f"{prefix_str}TOP_K", 40),
            max_tokens=get_env_int(f"{prefix_str}MAX_TOKENS", 2048)
        )
    
    def to_dict(self) -> dict:
        """
        Converts configuration to dictionary, excluding None values.
        
        Returns:
            Dictionary with non-None configuration values
        """
        return {k: v for k, v in self.model_dump().items() if v is not None}
    
    def __str__(self) -> str:
        """Returns a human-readable string representation."""
        return (
            f"GenerationConfig(temperature={self.temperature}, "
            f"top_p={self.top_p}, top_k={self.top_k}, "
            f"max_tokens={self.max_tokens})"
        )


class ModelConfig(BaseModel):
    """
    Configuration for model initialization parameters.
    
    This class handles model-specific configuration like context size,
    GPU layers, and other initialization parameters.
    
    Attributes:
        context_size: Maximum context window size in tokens
        gpu_layers: Number of layers to offload to GPU (for local models)
        batch_size: Batch size for processing
    """
    
    context_size: int = Field(
        default=2048,
        ge=128,
        le=128000,
        description="Maximum context window size in tokens"
    )
    
    gpu_layers: int = Field(
        default=1,
        ge=0,
        description="Number of layers to offload to GPU (0 = CPU only)"
    )
    
    batch_size: int = Field(
        default=512,
        ge=1,
        description="Batch size for processing"
    )
    
    @classmethod
    def default(cls) -> 'ModelConfig':
        """Returns default model configuration."""
        return cls()
    
    @classmethod
    def from_environment(cls, prefix: str = "") -> 'ModelConfig':
        """
        Creates a ModelConfig from environment variables.
        
        Args:
            prefix: Optional prefix for environment variables
            
        Returns:
            ModelConfig initialized from environment or defaults
        """
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        def get_env_int(key: str, default: int) -> int:
            value = os.getenv(key)
            return int(value) if value else default
        
        prefix_str = f"{prefix}_" if prefix else ""
        
        return cls(
            context_size=get_env_int(f"{prefix_str}CONTEXT_SIZE", 2048),
            gpu_layers=get_env_int(f"{prefix_str}GPU_LAYERS", 1),
            batch_size=get_env_int(f"{prefix_str}BATCH_SIZE", 512)
        )
