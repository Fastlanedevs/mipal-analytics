from pydantic import BaseModel


class PostgresCredentials(BaseModel):
    db_type: str = "postgres"
    host: str
    port: int = 5432
    username: str
    password: str
    database: str
