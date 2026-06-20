from src.core.security import create_access_token
from src.core.jwt import decode_access_token

token = create_access_token({"sub": "1"})
print("Token:", token[:10])
try:
    payload = decode_access_token(token)
    print("Payload:", payload)
except Exception as e:
    print("Error:", type(e).__name__, str(e))
