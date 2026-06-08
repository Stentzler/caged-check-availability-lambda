from src import handler


class FakeCheckAvailabilityService:
    def execute(self, event: dict) -> dict:
        assert event == {"request_id": "local-test"}
        return {
            "2026": {
                "202601": [
                    "CAGEDEXC202601.7z",
                    "CAGEDFOR202601.7z",
                    "CAGEDMOV202601.7z",
                ],
            },
        }


class FakeLambdaContext:
    function_name = "check-availability"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    aws_request_id = "local-request"


def test_lambda_handler_returns_service_response(monkeypatch) -> None:
    monkeypatch.setattr(handler, "service", FakeCheckAvailabilityService())

    response = handler.lambda_handler(
        {"request_id": "local-test"},
        context=FakeLambdaContext(),
    )

    assert response == {
        "2026": {
            "202601": [
                "CAGEDEXC202601.7z",
                "CAGEDFOR202601.7z",
                "CAGEDMOV202601.7z",
            ],
        },
    }
