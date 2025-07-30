import asyncio
from omegaconf import OmegaConf
from cmd_server.server.container import create_container

async def main():
    config = OmegaConf.load("conf/config.yaml")
    container = create_container(cfg=config)

    code_execution_client = container.code_execution_client()

    result = code_execution_client.execute_code_sync(
        code="print('Hello, world!')",
        user_id="d63d687ef15d4941b72c2a1866e371a8",
        input_data={},
        timeout_seconds=30
    )

    print(result)

asyncio.run(main())