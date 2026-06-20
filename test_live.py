import requests

url = "https://private-school-platfrom.onrender.com/api/v1"

print("Logging in...")
res = requests.post(
    f"{url}/auth/login",
    json={"identifier": "owner@school.dz", "password": "Owner@School2026!"}
)
print("Login status:", res.status_code)
if res.status_code != 200:
    print(res.text)
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
