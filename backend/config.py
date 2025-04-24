"""
Centralized configuration module using Pydantic's BaseSettings for type-safe configuration.
This replaces the previous approach of using environment variables directly and YAML files.
"""
from typing import Dict, Any, Optional
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class AWSSettings(BaseSettings):
    """AWS-related configuration settings."""
    # Feature flag for AWS authentication method
    auth_method: str = Field(
        default=os.getenv("AWS_AUTH_METHOD", "credentials"),
        description="AWS authentication method ('credentials' or 'iam_role')",
        json_schema_extra={"env": "AWS_AUTH_METHOD"}
    )
    region: str = Field(
        default=os.getenv("AWS_REGION"),
        description="AWS region",
        json_schema_extra={"env": "AWS_REGION"}
    )
    access_key_id: Optional[str] = Field(
        default=os.getenv("AWS_ACCESS_KEY_ID"),
        description="AWS access key ID (used when auth_method is 'credentials')",
        json_schema_extra={"env": "AWS_ACCESS_KEY_ID"}
    )
    secret_access_key: Optional[str] = Field(
        default=os.getenv("AWS_SECRET_ACCESS_KEY"),
        description="AWS secret access key (used when auth_method is 'credentials')",
        json_schema_extra={"env": "AWS_SECRET_ACCESS_KEY"}
    )
    region_name: Optional[str] = Field(
        default=os.getenv("AWS_REGION_NAME"),
        description="AWS region name (fallback to region if not set)",
        json_schema_extra={"env": "AWS_REGION_NAME"}
    )

    model_config = ConfigDict(env_file=".env", extra="ignore")

    @property
    def use_iam_role(self) -> bool:
        """Determine if IAM role authentication should be used."""
        return self.auth_method.lower() == "iam_role"

class BedrockSettings(BaseSettings):
    """Amazon Bedrock configuration settings."""
    model_name: str = Field(
        default=os.getenv("BEDROCK_MODEL_NAME"),
        description="Bedrock model name",
        json_schema_extra={"env": "BEDROCK_MODEL_NAME"}
    )
    model_arn: str = Field(
        default=os.getenv("BEDROCK_MODEL_ARN"),
        description="Bedrock model ARN",
        json_schema_extra={"env": "BEDROCK_MODEL_ARN"}
    )

    model_config = ConfigDict(env_file=".env", extra="ignore")

class KnowledgeBaseSettings(BaseSettings):
    """Knowledge base configuration settings."""
    kb_id: str = Field(
        default=os.getenv("KB_ID"),
        description="Main knowledge base ID",
        json_schema_extra={"env": "KB_ID"}
    )
    lpu_kb_id: Optional[str] = Field(
        default=os.getenv("LPU_KB_ID"),
        description="LPU-specific knowledge base ID",
        json_schema_extra={"env": "LPU_KB_ID"}
    )
    amity_kb_id: Optional[str] = Field(
        default=os.getenv("AMITY_KB_ID"),
        description="Amity-specific knowledge base ID",
        json_schema_extra={"env": "AMITY_KB_ID"}
    )

    model_config = ConfigDict(env_file=".env", extra="ignore")

# AgentSettings class removed as it's no longer used

class RetrievalSettings(BaseSettings):
    """Retrieval configuration settings."""
    num_results: int = Field(
        default=int(os.getenv("RETRIEVAL_NUM_RESULTS", "5")),
        description="Number of retrieval results",
        json_schema_extra={"env": "RETRIEVAL_NUM_RESULTS"}
    )
    min_score: float = Field(
        default=float(os.getenv("RETRIEVAL_MIN_SCORE", "0.5")),
        description="Minimum score for retrieval results",
        json_schema_extra={"env": "RETRIEVAL_MIN_SCORE"}
    )
    source_field: str = Field(
        default=os.getenv("RETRIEVAL_SOURCE_FIELD", "source_url"),
        description="Source field for retrieval",
        json_schema_extra={"env": "RETRIEVAL_SOURCE_FIELD"}
    )

    model_config = ConfigDict(env_file=".env", extra="ignore")

class CacheSettings(BaseSettings):
    """Cache configuration settings."""
    enabled: bool = Field(
        default=os.getenv("CACHE_ENABLED", "true").lower() == "true",
        description="Whether caching is enabled",
        json_schema_extra={"env": "CACHE_ENABLED"}
    )
    expiry_seconds: int = Field(
        default=int(os.getenv("CACHE_EXPIRY_SECONDS", "3600")),
        description="Cache expiry time in seconds",
        json_schema_extra={"env": "CACHE_EXPIRY_SECONDS"}
    )

    model_config = ConfigDict(env_file=".env", extra="ignore")

class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    enabled: bool = Field(
        default=os.getenv("REDIS_ENABLED", "false").lower() == "true",
        description="Whether Redis is enabled",
        json_schema_extra={"env": "REDIS_ENABLED"}
    )
    host: str = Field(
        default=os.getenv("REDIS_HOST", "localhost"),
        description="Redis host",
        json_schema_extra={"env": "REDIS_HOST"}
    )
    port: int = Field(
        default=int(os.getenv("REDIS_PORT", "6379")),
        description="Redis port",
        json_schema_extra={"env": "REDIS_PORT"}
    )
    password: Optional[str] = Field(
        default=os.getenv("REDIS_PASSWORD", ""),
        description="Redis password",
        json_schema_extra={"env": "REDIS_PASSWORD"}
    )
    db: int = Field(
        default=int(os.getenv("REDIS_DB", "0")),
        description="Redis database number",
        json_schema_extra={"env": "REDIS_DB"}
    )

    model_config = ConfigDict(env_file=".env", extra="ignore")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override with environment variables if present
        if "REDIS_PORT" in os.environ:
            self.port = int(os.environ["REDIS_PORT"])
        if "REDIS_HOST" in os.environ:
            self.host = os.environ["REDIS_HOST"]
        if "REDIS_ENABLED" in os.environ:
            self.enabled = os.environ["REDIS_ENABLED"].lower() == "true"

class MemorySettings(BaseSettings):
    """Memory configuration settings."""
    max_history: int = Field(
        default=int(os.getenv("MEMORY_MAX_HISTORY", "5")),
        description="Maximum number of interactions to keep in history",
        json_schema_extra={"env": "MEMORY_MAX_HISTORY"}
    )
    session_ttl: int = Field(
        default=int(os.getenv("MEMORY_SESSION_TTL", "86400")),
        description="Session time-to-live in seconds (default: 1 day)",
        json_schema_extra={"env": "MEMORY_SESSION_TTL"}
    )

    model_config = ConfigDict(env_file=".env", extra="ignore")

class WebSocketSettings(BaseSettings):
    """WebSocket configuration settings."""
    url: str = Field(
        default=os.getenv("WEBSOCKET_URL", "ws://localhost:8000/chat"),
        description="WebSocket URL",
        json_schema_extra={"env": "WEBSOCKET_URL"}
    )

    model_config = ConfigDict(env_file=".env", extra="ignore")

class ServerSettings(BaseSettings):
    """Server configuration settings."""
    port: int = Field(
        default=int(os.getenv("PORT", "8000")),
        description="Server port",
        json_schema_extra={"env": "PORT"}
    )

    model_config = ConfigDict(env_file=".env", extra="ignore")

class Settings(BaseSettings):
    """Main settings class that combines all configuration settings."""
    aws: AWSSettings = Field(default_factory=AWSSettings)
    bedrock: BedrockSettings = Field(default_factory=BedrockSettings)
    knowledge_base: KnowledgeBaseSettings = Field(default_factory=KnowledgeBaseSettings)
    # agent field removed as it's no longer used
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    websocket: WebSocketSettings = Field(default_factory=WebSocketSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)

    model_config = ConfigDict(env_file=".env", extra="ignore")

# Create a global settings instance
settings = Settings()

# For backward compatibility with existing code
AWS_REGION = settings.aws.region
AWS_ACCESS_KEY_ID = settings.aws.access_key_id
AWS_SECRET_ACCESS_KEY = settings.aws.secret_access_key
AWS_REGION_NAME = settings.aws.region_name or settings.aws.region
BEDROCK_MODEL_NAME = settings.bedrock.model_name
BEDROCK_MODEL_ARN = settings.bedrock.model_arn
KB_ID = settings.knowledge_base.kb_id
LPU_KB_ID = settings.knowledge_base.lpu_kb_id or KB_ID
AMITY_KB_ID = settings.knowledge_base.amity_kb_id
# AGENT_ID and ALIAS_ID removed as they are no longer used
RETRIEVAL_NUM_RESULTS = settings.retrieval.num_results
RETRIEVAL_MIN_SCORE = settings.retrieval.min_score
RETRIEVAL_SOURCE_FIELD = settings.retrieval.source_field
CACHE_ENABLED = settings.cache.enabled
CACHE_EXPIRY_SECONDS = settings.cache.expiry_seconds
WEBSOCKET_URL = settings.websocket.url
PORT = settings.server.port

def get_aws_config() -> Dict[str, Any]:
    """Get AWS configuration as a dictionary."""
    config = {
        "region": settings.aws.region,
        "bedrock_model": settings.bedrock.model_name,
        "s3_kb_id": settings.knowledge_base.kb_id,
        "model_arn": settings.bedrock.model_arn,
        "auth_method": settings.aws.auth_method,
    }

    # Only include credentials if not using IAM role
    if not settings.aws.use_iam_role:
        config["access_key"] = settings.aws.access_key_id
        config["secret_key"] = settings.aws.secret_access_key

    return config

# get_agent_config function removed as it's no longer used

def get_retrieval_config() -> Dict[str, Any]:
    """Get retrieval configuration as a dictionary."""
    return {
        "num_results": settings.retrieval.num_results,
        "min_score": settings.retrieval.min_score,
        "source_field": settings.retrieval.source_field,
    }

def get_cache_config() -> Dict[str, Any]:
    """Get cache configuration as a dictionary."""
    return {
        "enabled": settings.cache.enabled,
        "expiry_seconds": settings.cache.expiry_seconds,
    }

def get_full_config() -> Dict[str, Any]:
    """Get the full configuration as a dictionary."""
    return {
        "aws": get_aws_config(),
        # agent config removed as it's no longer used
        "retrieval": get_retrieval_config(),
        "cache": get_cache_config(),
        "websocket": {
            "url": settings.websocket.url,
        },
    }

def set_aws_credentials():
    """Set AWS credentials in environment variables based on authentication method."""
    # Always ensure region is set
    if not os.environ.get("AWS_REGION_NAME"):
        os.environ["AWS_REGION_NAME"] = settings.aws.region_name or settings.aws.region

    # If using IAM role authentication, we don't need to set credentials
    if settings.aws.use_iam_role:
        print("Using IAM role authentication - not setting AWS credential environment variables")
        return

    # Otherwise set credentials from settings
    if not os.environ.get("AWS_ACCESS_KEY_ID") and settings.aws.access_key_id:
        os.environ["AWS_ACCESS_KEY_ID"] = settings.aws.access_key_id
    if not os.environ.get("AWS_SECRET_ACCESS_KEY") and settings.aws.secret_access_key:
        os.environ["AWS_SECRET_ACCESS_KEY"] = settings.aws.secret_access_key

    print("Using credential-based authentication for AWS services")
