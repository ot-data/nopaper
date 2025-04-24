"""
Streamlit configuration module that imports from the backend configuration.
This avoids duplication and ensures consistency between backend and frontend.
"""
import os
import sys
from typing import Dict, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings

# Add the backend directory to the path so we can import from it
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend.config import (
    settings,
    get_aws_config,
    # get_agent_config removed as it's no longer used
    set_aws_credentials,
    AWS_REGION,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION_NAME,
    BEDROCK_MODEL_NAME,
    BEDROCK_MODEL_ARN,
    KB_ID,
    WEBSOCKET_URL
)

# Override the port for Streamlit (different from backend)
class StreamlitServerSettings(BaseSettings):
    """Streamlit-specific server settings."""
    port: int = Field(default=int(os.getenv("STREAMLIT_PORT", "8501")), env="STREAMLIT_PORT", description="Streamlit server port")

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

# Create a Streamlit-specific settings instance
streamlit_settings = StreamlitServerSettings()

# Override PORT for Streamlit
PORT = streamlit_settings.port

def get_full_config() -> Dict[str, Any]:
    """Get the full configuration as a dictionary."""
    return {
        "aws": get_aws_config(),
        # agent config removed as it's no longer used
        "websocket": {
            "url": WEBSOCKET_URL,
        },
        "server": {
            "port": PORT
        }
    }
