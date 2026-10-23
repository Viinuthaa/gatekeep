
from app.request_logs import log_request


def test_request_log_contains_usage():
    result = log_request(
        tenant_id="demo-tenant",
        model="test-model",
        prompt_tokens=10,
        completion_tokens=5,
        latency_ms=120.456,
    )

    assert result["tenant_id"] == "demo-tenant"
    assert result["model"] == "test-model"
    assert result["prompt_tokens"] == 10
    assert result["completion_tokens"] == 5
    assert result["total_tokens"] == 15
    assert result["latency_ms"] == 120.46
    assert result["request_id"]


def test_request_logs_have_unique_ids():
    first = log_request("tenant-a", "test-model", 1, 1, 50)
    second = log_request("tenant-a", "test-model", 1, 1, 50)

    assert first["request_id"] != second["request_id"]
