from serverless_toolkit.aws.dynamodb import get_dynamodb_table
from serverless_toolkit.observability.lambda_logger import (
    get_lambda_logger,
    inject_lambda_context,
)

from service import CheckAvailabilityService
from settings import settings

logger = get_lambda_logger()
registry_table = get_dynamodb_table(settings.REGISTRY_TABLE_NAME)
service = CheckAvailabilityService(
    settings=settings,
    logger=logger,
    registry_table=registry_table,
)


@inject_lambda_context(logger)
def handler(event: dict | None, context: object | None) -> dict:
    """Return files for Novo CAGED FTP files that need processing."""
    request_event = event or {}
    logger.info("Starting CAGED availability check")

    try:
        response = service.execute(request_event)
    except Exception:
        logger.exception("Failed to check CAGED availability, Check DEBUG level logs")
        raise

    logger.info(
        "Finished CAGED availability check",
        new_files_count=len(response["new_files"]),
    )
    return response


lambda_handler = handler
