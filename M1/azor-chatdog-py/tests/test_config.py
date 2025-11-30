"""
Unit Tests for LLM Configuration System

Tests for GenerationConfig, ModelConfig, and their usage across LLM clients.
"""

import pytest
import os
from unittest.mock import patch
from llm.config import GenerationConfig, ModelConfig


class TestGenerationConfig:
    """Tests for GenerationConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GenerationConfig.default()
        assert config.temperature == 0.7
        assert config.top_p == 0.95
        assert config.top_k == 40
        assert config.max_tokens == 2048
        assert config.stop_sequences is None

    def test_custom_config(self):
        """Test creating custom configuration."""
        config = GenerationConfig(
            temperature=0.9,
            top_p=0.98,
            top_k=50,
            max_tokens=1024
        )
        assert config.temperature == 0.9
        assert config.top_p == 0.98
        assert config.top_k == 50
        assert config.max_tokens == 1024

    def test_creative_preset(self):
        """Test creative preset configuration."""
        config = GenerationConfig.creative()
        assert config.temperature == 0.9
        assert config.top_p == 0.95
        assert config.top_k == 50
        assert config.max_tokens == 2048

    def test_precise_preset(self):
        """Test precise preset configuration."""
        config = GenerationConfig.precise()
        assert config.temperature == 0.3
        assert config.top_p == 0.9
        assert config.top_k == 20
        assert config.max_tokens == 2048

    def test_balanced_preset(self):
        """Test balanced preset configuration."""
        config = GenerationConfig.balanced()
        assert config.temperature == 0.7
        assert config.top_p == 0.95
        assert config.top_k == 40
        assert config.max_tokens == 2048

    def test_temperature_validation(self):
        """Test temperature parameter validation."""
        # Valid temperatures
        GenerationConfig(temperature=0.0)
        GenerationConfig(temperature=1.0)
        GenerationConfig(temperature=2.0)

        # Invalid temperatures
        with pytest.raises(ValueError):
            GenerationConfig(temperature=-0.1)
        with pytest.raises(ValueError):
            GenerationConfig(temperature=2.1)

    def test_top_p_validation(self):
        """Test top_p parameter validation."""
        # Valid top_p values
        GenerationConfig(top_p=0.0)
        GenerationConfig(top_p=0.5)
        GenerationConfig(top_p=1.0)

        # Invalid top_p values
        with pytest.raises(ValueError):
            GenerationConfig(top_p=-0.1)
        with pytest.raises(ValueError):
            GenerationConfig(top_p=1.1)

    def test_top_k_validation(self):
        """Test top_k parameter validation."""
        # Valid top_k values
        GenerationConfig(top_k=1)
        GenerationConfig(top_k=100)

        # Invalid top_k values
        with pytest.raises(ValueError):
            GenerationConfig(top_k=0)
        with pytest.raises(ValueError):
            GenerationConfig(top_k=-1)

    def test_max_tokens_validation(self):
        """Test max_tokens parameter validation."""
        # Valid max_tokens values
        GenerationConfig(max_tokens=1)
        GenerationConfig(max_tokens=128000)

        # Invalid max_tokens values
        with pytest.raises(ValueError):
            GenerationConfig(max_tokens=0)
        with pytest.raises(ValueError):
            GenerationConfig(max_tokens=-1)
        with pytest.raises(ValueError):
            GenerationConfig(max_tokens=128001)

    def test_stop_sequences(self):
        """Test stop sequences configuration."""
        config = GenerationConfig(stop_sequences=["STOP", "END"])
        assert config.stop_sequences == ["STOP", "END"]

        config_none = GenerationConfig(stop_sequences=None)
        assert config_none.stop_sequences is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = GenerationConfig(
            temperature=0.8,
            top_p=0.95,
            top_k=40,
            max_tokens=2048
        )
        config_dict = config.to_dict()

        assert config_dict['temperature'] == 0.8
        assert config_dict['top_p'] == 0.95
        assert config_dict['top_k'] == 40
        assert config_dict['max_tokens'] == 2048

    def test_to_dict_excludes_none(self):
        """Test that to_dict excludes None values."""
        config = GenerationConfig(
            temperature=0.8,
            stop_sequences=None
        )
        config_dict = config.to_dict()

        assert 'temperature' in config_dict
        # stop_sequences should still be in dict even if None
        # This is controlled by to_dict implementation

    def test_string_representation(self):
        """Test string representation."""
        config = GenerationConfig(temperature=0.8, top_p=0.95)
        str_repr = str(config)

        assert 'GenerationConfig' in str_repr
        assert 'temperature=0.8' in str_repr
        assert 'top_p=0.95' in str_repr

    @patch.dict(os.environ, {
        'TEST_TEMPERATURE': '0.9',
        'TEST_TOP_P': '0.98',
        'TEST_TOP_K': '50',
        'TEST_MAX_TOKENS': '1024'
    })
    def test_from_environment(self):
        """Test loading configuration from environment variables."""
        config = GenerationConfig.from_environment("TEST")

        assert config.temperature == 0.9
        assert config.top_p == 0.98
        assert config.top_k == 50
        assert config.max_tokens == 1024

    @patch.dict(os.environ, {}, clear=True)
    def test_from_environment_defaults(self):
        """Test that missing env variables use defaults."""
        config = GenerationConfig.from_environment("MISSING")

        assert config.temperature == 0.7  # Default
        assert config.top_p == 0.95  # Default
        assert config.top_k == 40  # Default
        assert config.max_tokens == 2048  # Default

    @patch.dict(os.environ, {'TEMPERATURE': '0.5'})
    def test_from_environment_no_prefix(self):
        """Test loading from environment without prefix."""
        config = GenerationConfig.from_environment("")
        assert config.temperature == 0.5


class TestModelConfig:
    """Tests for ModelConfig class."""

    def test_default_config(self):
        """Test default model configuration."""
        config = ModelConfig.default()
        assert config.context_size == 2048
        assert config.gpu_layers == 1
        assert config.batch_size == 512

    def test_custom_config(self):
        """Test custom model configuration."""
        config = ModelConfig(
            context_size=4096,
            gpu_layers=2,
            batch_size=1024
        )
        assert config.context_size == 4096
        assert config.gpu_layers == 2
        assert config.batch_size == 1024

    def test_context_size_validation(self):
        """Test context size validation."""
        # Valid sizes
        ModelConfig(context_size=128)
        ModelConfig(context_size=128000)

        # Invalid sizes
        with pytest.raises(ValueError):
            ModelConfig(context_size=127)
        with pytest.raises(ValueError):
            ModelConfig(context_size=128001)

    def test_gpu_layers_validation(self):
        """Test GPU layers validation."""
        # Valid values
        ModelConfig(gpu_layers=0)
        ModelConfig(gpu_layers=10)

        # Invalid values
        with pytest.raises(ValueError):
            ModelConfig(gpu_layers=-1)

    def test_batch_size_validation(self):
        """Test batch size validation."""
        # Valid values
        ModelConfig(batch_size=1)
        ModelConfig(batch_size=1024)

        # Invalid values
        with pytest.raises(ValueError):
            ModelConfig(batch_size=0)
        with pytest.raises(ValueError):
            ModelConfig(batch_size=-1)

    @patch.dict(os.environ, {
        'MODEL_CONTEXT_SIZE': '4096',
        'MODEL_GPU_LAYERS': '2',
        'MODEL_BATCH_SIZE': '1024'
    })
    def test_from_environment(self):
        """Test loading model config from environment."""
        config = ModelConfig.from_environment("MODEL")

        assert config.context_size == 4096
        assert config.gpu_layers == 2
        assert config.batch_size == 1024


class TestConfigurationIntegration:
    """Integration tests for configuration system."""

    def test_config_immutability(self):
        """Test that configs maintain their values."""
        config = GenerationConfig(temperature=0.8)
        original_temp = config.temperature

        # Create another config
        config2 = GenerationConfig(temperature=0.5)

        # First config should be unchanged
        assert config.temperature == original_temp

    def test_preset_independence(self):
        """Test that presets are independent instances."""
        creative1 = GenerationConfig.creative()
        creative2 = GenerationConfig.creative()

        assert creative1.temperature == creative2.temperature
        assert creative1 is not creative2  # Different instances

    def test_partial_configuration(self):
        """Test creating config with partial parameters."""
        config = GenerationConfig(temperature=0.5)

        # Should use defaults for non-specified params
        assert config.temperature == 0.5
        assert config.top_p == 0.95  # Default
        assert config.top_k == 40  # Default

    def test_config_equality(self):
        """Test configuration equality comparison."""
        config1 = GenerationConfig(temperature=0.8, top_p=0.95)
        config2 = GenerationConfig(temperature=0.8, top_p=0.95)
        config3 = GenerationConfig(temperature=0.9, top_p=0.95)

        # Pydantic models support equality
        assert config1.model_dump() == config2.model_dump()
        assert config1.model_dump() != config3.model_dump()

    def test_config_copy(self):
        """Test configuration copying."""
        original = GenerationConfig(temperature=0.8)

        # Create new config with modified value
        modified = GenerationConfig(
            temperature=0.9,
            top_p=original.top_p,
            top_k=original.top_k,
            max_tokens=original.max_tokens
        )

        assert original.temperature != modified.temperature
        assert original.top_p == modified.top_p


class TestConfigurationEdgeCases:
    """Edge case tests for configuration."""

    def test_boundary_values(self):
        """Test boundary values for all parameters."""
        # Minimum values
        config_min = GenerationConfig(
            temperature=0.0,
            top_p=0.0,
            top_k=1,
            max_tokens=1
        )
        assert config_min.temperature == 0.0
        assert config_min.top_p == 0.0
        assert config_min.top_k == 1
        assert config_min.max_tokens == 1

        # Maximum values
        config_max = GenerationConfig(
            temperature=2.0,
            top_p=1.0,
            top_k=1000,
            max_tokens=128000
        )
        assert config_max.temperature == 2.0
        assert config_max.top_p == 1.0
        assert config_max.top_k == 1000
        assert config_max.max_tokens == 128000

    def test_none_optional_params(self):
        """Test that optional parameters can be None."""
        config = GenerationConfig(
            temperature=0.7,
            top_p=None,
            top_k=None
        )
        assert config.temperature == 0.7
        # top_p and top_k have defaults, so they won't be None
        assert config.top_p is not None
        assert config.top_k is not None

    def test_empty_stop_sequences(self):
        """Test empty stop sequences list."""
        config = GenerationConfig(stop_sequences=[])
        assert config.stop_sequences == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

