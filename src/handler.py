from serverless_toolkit.observability.lambda_logger import (
    get_lambda_logger,
    inject_lambda_context,
)

from service import CheckAvailabilityService
from settings import settings

logger = get_lambda_logger()
service = CheckAvailabilityService(settings=settings, logger=logger)


@inject_lambda_context(logger)
def handler(event: dict | None, context: object | None) -> dict:
    """Return the available Novo CAGED FTP files grouped by year and month."""
    request_event = event or {}
    logger.info("Starting CAGED availability check")

    try:
        response = service.execute(request_event)
    except Exception:
        logger.exception("Failed to check CAGED availability, Check DEBUG level logs")
        raise

    logger.info("Finished CAGED availability check", years_count=len(response))
    return response


lambda_handler = handler
