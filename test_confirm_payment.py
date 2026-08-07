import asyncio
import httpx
from src.app import app
from src.modules.users.models import User
from src.modules.auth.dependencies import require_manage_subscriptions, require_role, require_manage_enrollments
from fastapi.testclient import TestClient

def override_require_manage_subscriptions():
    return User(id=1, email="admin@test.com", role="owner", first_name="Test", last_name="Admin")

def override_require_role(*args, **kwargs):
    def dep():
        return override_require_manage_subscriptions()
    return dep

app.dependency_overrides[require_manage_subscriptions] = override_require_manage_subscriptions
app.dependency_overrides[require_manage_enrollments] = override_require_manage_subscriptions
app.dependency_overrides[require_role] = override_require_role

client = TestClient(app, raise_server_exceptions=False)
res = client.post("/api/enrollments/1/confirm-payment", json={"amount": 100})
print("STATUS:", res.status_code)
print("RESPONSE:", res.json())
