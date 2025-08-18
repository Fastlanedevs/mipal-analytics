# pkg/config/config.py

from dataclasses import dataclass, field
from typing import List, Optional
from omegaconf import MISSING


@dataclass
class Neo4jConfig:
    uri: str
    user: str
    password: str
    max_pool_size: int = 50
    max_retries: int = 3
    retry_delay: int = 1


@dataclass
class JWTAuthConfig:
    super_secret_key: str
    refresh_secret_key: str


@dataclass
class SMTPConfig:
    smtp_server: str
    smtp_port: str
    username: str
    password: str


@dataclass
class OpenAIConfig:
    openai_api_key: str
    deepseek_api_key: str
    groq_api_key: str
    gemini_api_key: str
    chart_generation_model: str = "gpt-4o-mini"
    chart_adjustment_model: str = "gpt-4o-mini"
    analytics_pal_model: str = "gpt-4o-mini"


@dataclass
class AWSConfig:
    kms_key_id: Optional[str] = None
    s3_bucket_name: str
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "eu-north-1"

@dataclass
class LocalKMSConfig:
    password : str
    key_storage_path : Optional[str] = None
    key_size : int = 32 


@dataclass
class QueueConfig:
    sync_documents: str


@dataclass
class RedisConfig:
    host: str
    port: str
    password: str





@dataclass
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str




@dataclass
class ServiceURL:
    code_execution_url: str


@dataclass
class AppConfig:
    neo4j: Neo4jConfig
    jwt_auth: JWTAuthConfig
    smtp: SMTPConfig
    openai: OpenAIConfig
    queue: QueueConfig
    redis: RedisConfig
    aws: AWSConfig
    postgres: PostgresConfig
    service_url: ServiceURL
    local_kms : LocalKMSConfig

