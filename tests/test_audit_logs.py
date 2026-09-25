import pytest
import src.app  # noqa: F401
from datetime import datetime
from src.modules.audit.models import ActivityLog
from src.modules.audit.router import ActivityLogResponse


def test_activity_log_response_serialization():
    log = ActivityLog(
        id=101,
        user_id=5,
        action="TEST_ACTION",
        category="auth",
        entity_type="user",
        entity_id=5,
        branch_id=2,
        metadata_={"ip": "127.0.0.1", "device": "chrome"},
        ip_address="127.0.0.1",
        created_at=datetime(2026, 9, 25, 12, 0, 0),
    )

    validated = ActivityLogResponse.model_validate(log)
    dumped = validated.model_dump(by_alias=True)

    assert dumped["id"] == 101
    assert dumped["userId"] == 5
    assert dumped["action"] == "TEST_ACTION"
    assert dumped["category"] == "auth"
    assert dumped["branchId"] == 2
    assert dumped["metadata"] == {"ip": "127.0.0.1", "device": "chrome"}
    assert dumped["ipAddress"] == "127.0.0.1"
    assert "createdAt" in dumped
