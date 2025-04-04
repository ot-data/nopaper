"""
Centralized configuration module that loads all environment variables directly.
This replaces the previous YAML-based configuration approach.
"""
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Load environment variables from .env file if it exists
load_dotenv()

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION_NAME = os.getenv("AWS_REGION", AWS_REGION)  # Fallback to AWS_REGION if AWS_REGION_NAME not set

# Bedrock Configuration
BEDROCK_MODEL_NAME = os.getenv("BEDROCK_MODEL_NAME")
BEDROCK_MODEL_ARN = os.getenv("BEDROCK_MODEL_ARN")

# Knowledge Base Configuration
KB_ID = os.getenv("KB_ID")

# Agent Configuration
AGENT_ID = os.getenv("AGENT_ID")
ALIAS_ID = os.getenv("ALIAS_ID")

# WebSocket Configuration
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://localhost:8000/chat")

# Server Configuration
PORT = int(os.getenv("PORT", "8501"))  # Default Streamlit port

def get_aws_config() -> Dict[str, Any]:
    """Get AWS configuration as a dictionary."""
    return {
        "region": AWS_REGION,
        "bedrock_model": BEDROCK_MODEL_NAME,
        "s3_kb_id": KB_ID,
        "access_key": AWS_ACCESS_KEY_ID,
        "secret_key": AWS_SECRET_ACCESS_KEY,
        "model_arn": BEDROCK_MODEL_ARN,
    }

def get_agent_config() -> Dict[str, Any]:
    """Get agent configuration as a dictionary."""
    return {
        "agent_id": AGENT_ID,
        "alias_id": ALIAS_ID,
    }

def get_full_config() -> Dict[str, Any]:
    """Get the full configuration as a dictionary, similar to the previous YAML structure."""
    return {
        "aws": get_aws_config(),
        "agent": get_agent_config(),
        "websocket": {
            "url": WEBSOCKET_URL,
        },
    }

def set_aws_credentials():
    """Set AWS credentials in environment variables."""
    # Only set if not already set
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
    if not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY
    if not os.environ.get("AWS_REGION_NAME"):
        os.environ["AWS_REGION_NAME"] = AWS_REGION_NAME
