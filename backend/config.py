"""
Centralized configuration module that loads all environment variables directly.

"""
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional

load_dotenv()

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION_NAME = os.getenv("AWS_REGION", AWS_REGION)  

# Bedrock Configuration
BEDROCK_MODEL_NAME = os.getenv("BEDROCK_MODEL_NAME")
BEDROCK_MODEL_ARN = os.getenv("BEDROCK_MODEL_ARN")

# Knowledge Base Configuration
KB_ID = os.getenv("KB_ID")

# Agent Configuration
AGENT_ID = os.getenv("AGENT_ID")
ALIAS_ID = os.getenv("ALIAS_ID")

# Institution-specific Knowledge Base IDs
LPU_KB_ID = os.getenv("LPU_KB_ID", KB_ID)  # Fallback to main KB_ID if not set
AMITY_KB_ID = os.getenv("AMITY_KB_ID")

# Retrieval Configuration
RETRIEVAL_NUM_RESULTS = int(os.getenv("RETRIEVAL_NUM_RESULTS", "5"))
RETRIEVAL_MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.5"))
RETRIEVAL_SOURCE_FIELD = os.getenv("RETRIEVAL_SOURCE_FIELD", "source_url")

# Cache Configuration
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_EXPIRY_SECONDS = int(os.getenv("CACHE_EXPIRY_SECONDS", "3600"))

# WebSocket Configuration
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://localhost:8000/chat")

# Server Configuration
PORT = int(os.getenv("PORT", "8000"))

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

def get_retrieval_config() -> Dict[str, Any]:
    """Get retrieval configuration as a dictionary."""
    return {
        "num_results": RETRIEVAL_NUM_RESULTS,
        "min_score": RETRIEVAL_MIN_SCORE,
        "source_field": RETRIEVAL_SOURCE_FIELD,
    }

def get_cache_config() -> Dict[str, Any]:
    """Get cache configuration as a dictionary."""
    return {
        "enabled": CACHE_ENABLED,
        "expiry_seconds": CACHE_EXPIRY_SECONDS,
    }

def get_full_config() -> Dict[str, Any]:
    """Get the full configuration as a dictionary, similar to the previous YAML structure."""
    return {
        "aws": get_aws_config(),
        "agent": get_agent_config(),
        "retrieval": get_retrieval_config(),
        "cache": get_cache_config(),
        "websocket": {
            "url": WEBSOCKET_URL,
        },
    }

def set_aws_credentials():
    """Set AWS credentials in environment variables."""
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
    if not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY
    if not os.environ.get("AWS_REGION_NAME"):
        os.environ["AWS_REGION_NAME"] = AWS_REGION_NAME
