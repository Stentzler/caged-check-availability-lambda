import handler


class FakeLogger:
    def __init__(self) -> None:
        self.info_calls: list[tuple[str, dict[str, object]]] = []

    def info(self, message: str, **kwargs: object) -> None:
        self.info_calls.append((message, kwargs))


class FakeCheckAvailabilityService:
    def execute(self, event: dict) -> dict:
        assert event == {"request_id": "local-test"}
        return {
            "new_files": [
                {
                    "filename": "CAGEDMOV202601.7z",
                    "ftp_url": (
                        "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/"
                        "2026/202601/CAGEDMOV202601.7z"
                    ),
                    "reference_month": "202601",
                    "reference_year": "2026",
                    "s3_key": (
                        "raw/caged/year=2026/month=01/"
                        "file_type=movement/CAGEDMOV202601.7z"
                    ),
                },
            ],
        }


class FakeLambdaContext:
    function_name = "check-availability"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    aws_request_id = "local-request"


def test_lambda_handler_returns_service_response(monkeypatch) -> None:
    fake_logger = FakeLogger()
    monkeypatch.setattr(handler, "service", FakeCheckAvailabilityService())
    monkeypatch.setattr(handler, "logger", fake_logger)

    response = handler.lambda_handler(
        {"request_id": "local-test"},
        context=FakeLambdaContext(),
    )

    assert response == {
        "new_files": [
            {
                "filename": "CAGEDMOV202601.7z",
                "ftp_url": (
                    "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/"
                    "2026/202601/CAGEDMOV202601.7z"
                ),
                "reference_month": "202601",
                "reference_year": "2026",
                "s3_key": (
                    "raw/caged/year=2026/month=01/file_type=movement/CAGEDMOV202601.7z"
                ),
            },
        ],
    }
    assert fake_logger.info_calls[-1] == (
        "Finished CAGED availability check",
        {
            "new_files_count": 1,
            "new_files": response["new_files"],
        },
    )
