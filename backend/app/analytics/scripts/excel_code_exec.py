import asyncio
from omegaconf import OmegaConf
from cmd_server.server.container import create_container
from pkg.llm_provider.llm_client import LLMModel
from app.pal.analytics.analytics_workflow import AnalyticsPAL
from app.pal.analytics.executors.excel_executor import ExcelExecutor

async def get_excel_preview(preview_excel,database_uid: str, table_uid: str, limit: int = 10):
    return await preview_excel(database_uid, table_uid, limit)

async def main():
    config = OmegaConf.load("conf/config.yaml")
    container = create_container(cfg=config)

    s3_client = container.s3_client()
    llm_client = container.llm_client()
    redis_client = container.redis_client()
    tokens_service = container.tokens_service()
    logger = container.logger()
    analytics_service = container.analytics_service()
    chat_repository = container.chat_repository()
    analytics_repository = container.analytics_repository_adapter()
    
    analytics_pal = AnalyticsPAL(
        llm_client=llm_client,
        chat_repository=chat_repository,
        s3_client=s3_client,
        redis_client=redis_client,
        tokens_service=tokens_service,
        logger=logger,
        analytics_repository=analytics_repository,
        analytics_service=analytics_service,
        model=LLMModel.GEMINI_2_0_FLASH,  # Direct value for now to ensure it works
        dev_mode=True,
        dev_log_dir="./logs/analytics"
    )

    excel_executor = ExcelExecutor(
        s3_client=s3_client,
        analytics_repository=analytics_repository,
        logger=logger
    )

    result, error = await get_excel_preview(excel_executor.preview_excel, "292270538c25451a9705a1f11a2196bc", "aaf161ac0a28444f8b9248685a813429", 10)
    print(result)
    print(error)





if __name__ == "__main__":
    # Run the main function
    print("Starting Excel related operations")
    asyncio.run(main())
    print("Script completed")