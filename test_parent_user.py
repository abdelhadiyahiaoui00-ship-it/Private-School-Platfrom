import asyncio
from fastapi.testclient import TestClient
from src.app import app
from src.core.security import create_access_token
import json

client = TestClient(app)
token = create_access_token({"sub": "1", "role": "superAdmin", "sessionId": "123"})

# Test parent user (id=11)
response = client.get("/api/users/11", headers={"Authorization": f"Bearer {token}"})
print("Status:", response.status_code)
if response.status_code == 200:
    data = response.json()["data"]
    print("Role:", data["role"])
    print("linkedStudents count:", len(data["linkedStudents"]))
    for link in data["linkedStudents"]:
        print("  Link id:", link["id"])
        print("  studentId:", link["studentId"])
        print("  student object:", json.dumps(link.get("student"), indent=4)[:300] if link.get("student") else "NULL")
else:
    print(response.json())

# Test student user (id=10)
response2 = client.get("/api/users/10", headers={"Authorization": f"Bearer {token}"})
print("\nStatus:", response2.status_code)
if response2.status_code == 200:
    data2 = response2.json()["data"]
    print("Role:", data2["role"])
    print("linkedParents count:", len(data2["linkedParents"]))
    for link in data2["linkedParents"]:
        print("  Link id:", link["id"])
        print("  parentId:", link["parentId"])
        print("  parent object:", json.dumps(link.get("parent"), indent=4)[:300] if link.get("parent") else "NULL")
else:
    print(response2.json())
