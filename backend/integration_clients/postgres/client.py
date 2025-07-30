import asyncpg

from pkg.log.logger import Logger


class PostgresClient:
    def __init__(self, logger: Logger):
        self.client_id = client_id
        self.client_secret = client_secret
        self.logger = logger

    async def connect(self, credentials: UserDatabaseCredentials):
        self.pool = await asyncpg.create_pool(
            host=credentials.host,
            port=credentials.port,
            user=credentials.username,
            password=credentials.password,
            database=credentials.database,
        )

    async def close(self):
        await self.pool.close()

    async def execute(self, sql: str) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            result = await conn.fetch(sql)
            return [dict(row) for row in result]

    async def get_table_info(self) -> dict[str, list[str]]:
        async with self.pool.acquire() as conn:
            tables = await conn.fetch(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )

            table_info = {}
            for table in tables:
                columns = await conn.fetch(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = $1",
                    table["table_name"],
                )
                table_info[table["table_name"]] = [
                    column["column_name"] for column in columns
                ]

            return table_info
