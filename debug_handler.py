import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
DEFAULT_EVENT_PATH = PROJECT_ROOT / "events" / "check-availability.json"

os.environ.setdefault("DYNAMODB_ENDPOINT_URL", "http://127.0.0.1:8000")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "dummy")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "dummy")


class LocalLambdaContext:
    """Local Lambda context metadata used by logger middleware during debugging."""

    function_name = "local-check-availability-lambda"
    function_version = "$LATEST"
    invoked_function_arn = (
        "arn:aws:lambda:local:000000000000:function:local-check-availability-lambda"
    )
    memory_limit_in_mb = 128
    aws_request_id = "local-request-id"
    log_group_name = "/aws/lambda/local-check-availability-lambda"
    log_stream_name = "local"


def load_event(event_path: Path = DEFAULT_EVENT_PATH) -> dict[str, Any]:
    """Load the local event payload used to simulate a Lambda invocation."""
    if not event_path.exists():
        return {}

    event_text = event_path.read_text()
    if not event_text.strip():
        return {}

    return json.loads(event_text)


def load_lambda_handler() -> Any:
    """Import the Lambda handler from src/handler.py."""
    sys.path.insert(0, str(SRC_DIR))
    handler_module = importlib.import_module("handler")
    return handler_module.lambda_handler


def main() -> None:
    event = load_event()
    lambda_handler = load_lambda_handler()
    response = lambda_handler(event, LocalLambdaContext())

    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
