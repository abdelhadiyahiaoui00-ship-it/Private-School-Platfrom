import requests
import time
import subprocess
import os

# Start server
env = os.environ.copy()
env["PYTHONPATH"] = "."
proc = subprocess.Popen([".venv/bin/uvicorn", "src.app:create_app", "--port", "8000"], env=env)

time.sleep(3) # Wait for server to start

url = "http://127.0.0.1:8000/api/v1"

print("Logging in...")
res = requests.post(
    f"{url}/auth/login",
    json={"identifier": "owner@school.dz", "password": "Owner@School2026!"}
)
print("Login status:", res.status_code)
if res.status_code != 200:
    print(res.text)
    proc.terminate()
    exit(1)

token = res.json()["data"]["tokens"]["access_token"]
print("Got token:", token[:10], "...")

print("Fetching users...")
res2 = requests.get(
    f"{url}/users",
    headers={"Authorization": f"Bearer {token}"}
)
print("Users status:", res2.status_code)
if res2.status_code != 200:
    print(res2.text)
else:
    print("Success!")

proc.terminate()
