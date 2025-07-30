from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    uri: str
    username: str
    password: str
    max_pool_size: int = 20
    max_retries: int = 3
    retry_delay: int = 1

    @property
    def connection_url(self) -> str:
        return f"neo4j+s://{self.username}:{self.password}@{self.uri}"


@dataclass
class PostgresConfig:
    host: str
    port: int
    username: str
    password: str
    database: str = "postgres"  # Default database
    pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 10  # seconds
    pool_recycle: int = 1800