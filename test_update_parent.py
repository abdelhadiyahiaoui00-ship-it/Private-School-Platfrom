import asyncio
from fastapi.testclient import TestClient
from src.app import app
from src.core.security import create_access_token
import json

client = TestClient(app)
token = create_access_token({"sub": "1", "role": "superAdmin", "sessionId": "123"})

# Test update parent user (id=11)
payload = {
    "linkedStudentIds": [10, 11], # add student 11 maybe? Wait, user 11 is parent. Let's add student 8 (admin) or we can create a mock student.
    "relationships": {"10": "parent", "8": "guardian"}
}
response = client.patch("/api/users/11", json=payload, headers={"Authorization": f"Bearer {token}"})
print("Status:", response.status_code)
if response.status_code != 200:
    print(response.json())
