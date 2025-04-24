"""
Simple test script to verify that our Pydantic-based configuration is working correctly.
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import the configuration
from backend.config import settings

def test_config():
    """Test that the configuration is loaded correctly."""
    print("Testing Pydantic-based configuration...")

    # Print some configuration values
    print(f"AWS Region: {settings.aws.region}")
    print(f"Bedrock Model Name: {settings.bedrock.model_name}")
    print(f"Knowledge Base ID: {settings.knowledge_base.kb_id}")
    # Agent settings removed as they're no longer used
    print("Agent settings: Removed from codebase")
    print(f"WebSocket URL: {settings.websocket.url}")
    print(f"Server Port: {settings.server.port}")

    # Test the helper functions
    from backend.config import get_aws_config, get_full_config

    aws_config = get_aws_config()
    print(f"\nAWS Config: {aws_config}")

    # Agent config function removed
    print("\nAgent Config: Removed from codebase")

    full_config = get_full_config()
    print(f"\nFull Config Keys: {list(full_config.keys())}")

    print("\nConfiguration test completed successfully!")

if __name__ == "__main__":
    test_config()
