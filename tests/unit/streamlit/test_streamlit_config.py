"""
Simple test script to verify that our Pydantic-based configuration is working correctly for Streamlit.
"""
import sys
import os
import pytest

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import the configuration
from streamlit.config import streamlit_settings, get_full_config, PORT

@pytest.mark.unit
def test_streamlit_settings():
    """Test that the streamlit_settings is loaded correctly."""
    assert streamlit_settings is not None
    assert hasattr(streamlit_settings, "port")
    assert streamlit_settings.port == PORT

@pytest.mark.unit
def test_get_full_config():
    """Test that get_full_config returns a dictionary with expected keys."""
    full_config = get_full_config()
    assert isinstance(full_config, dict)
    assert "server" in full_config
    assert "port" in full_config["server"]

if __name__ == "__main__":
    print("This test file is now designed to be run with pytest.")
    print("Run with: python -m pytest tests/unit/streamlit/test_streamlit_config.py -v")
