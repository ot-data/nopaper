"""
Unit tests for configuration using Pydantic's BaseSettings.
"""
import pytest
import os
from unittest.mock import patch

from backend.config import (
    settings,
    AWSSettings,
    RedisSettings,
    MemorySettings,
    get_aws_config,
    get_full_config
)

@pytest.mark.unit
class TestConfig:
    """Test configuration using Pydantic's BaseSettings."""

    def test_settings_instance(self):
        """Test that settings is an instance of Settings."""
        assert settings is not None
        assert hasattr(settings, "aws")
        assert hasattr(settings, "redis")
        assert hasattr(settings, "memory")
        assert hasattr(settings, "websocket")
        assert hasattr(settings, "server")

    def test_aws_settings(self):
        """Test AWS settings."""
        aws_settings = AWSSettings()
        assert hasattr(aws_settings, "region")
        assert hasattr(aws_settings, "access_key_id")
        assert hasattr(aws_settings, "secret_access_key")
        assert hasattr(aws_settings, "region_name")

    def test_redis_settings(self):
        """Test Redis settings."""
        redis_settings = RedisSettings()
        assert hasattr(redis_settings, "enabled")
        assert hasattr(redis_settings, "host")
        assert hasattr(redis_settings, "port")
        assert hasattr(redis_settings, "password")
        assert hasattr(redis_settings, "db")

        # Test default values
        assert redis_settings.host == "localhost"
        assert redis_settings.port == 6379
        assert redis_settings.db == 0

    def test_memory_settings(self):
        """Test memory settings."""
        memory_settings = MemorySettings()
        assert hasattr(memory_settings, "max_history")
        assert hasattr(memory_settings, "session_ttl")

        # Test default values
        assert memory_settings.max_history == 5
        assert memory_settings.session_ttl == 86400  # 1 day

    def test_get_aws_config(self):
        """Test get_aws_config function."""
        config = get_aws_config()
        assert isinstance(config, dict)
        assert "region" in config
        assert "bedrock_model" in config
        assert "s3_kb_id" in config
        assert "access_key" in config
        assert "secret_key" in config
        assert "model_arn" in config

    def test_get_full_config(self):
        """Test get_full_config function."""
        config = get_full_config()
        assert isinstance(config, dict)
        assert "aws" in config
        assert "agent" in config
        assert "retrieval" in config
        assert "cache" in config
        assert "websocket" in config

    @patch.dict(os.environ, {"REDIS_ENABLED": "true"})
    def test_redis_enabled_from_env(self):
        """Test that Redis enabled setting is read from environment variable."""
        redis_settings = RedisSettings()
        assert redis_settings.enabled is True

    @patch.dict(os.environ, {"REDIS_ENABLED": "false"})
    def test_redis_disabled_from_env(self):
        """Test that Redis disabled setting is read from environment variable."""
        redis_settings = RedisSettings()
        assert redis_settings.enabled is False

    @patch.dict(os.environ, {"REDIS_HOST": "redis.example.com", "REDIS_PORT": "6380"})
    def test_redis_connection_from_env(self):
        """Test that Redis connection settings are read from environment variables."""
        redis_settings = RedisSettings()
        assert redis_settings.host == "redis.example.com"
        assert redis_settings.port == 6380

    def test_memory_settings_from_env(self):
        """Test that memory settings are read from environment variables."""
        # Create a new instance with custom values
        memory_settings = MemorySettings(
            max_history=10,
            session_ttl=3600
        )
        assert memory_settings.max_history == 10
        assert memory_settings.session_ttl == 3600
