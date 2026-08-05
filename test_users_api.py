import asyncio
from fastapi.testclient import TestClient
from src.app import app
from src.core.security import create_access_token
from src.core.config import settings

client = TestClient(app)

# Generate a valid token for user 1
token = create_access_token({"sub": "1", "role": "superAdmin", "sessionId": "123"})

response = client.get("/api/users/1", headers={"Authorization": f"Bearer {token}"})
print(response.status_code)
print(response.json())
