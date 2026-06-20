import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import sessionmanager
from src.modules.auth.service import AuthService

async def test_login():
    async with sessionmanager.session() as session:
        auth_service = AuthService(session)
        try:
            res = await auth_service.login("owner@school.dz", "Owner@School2026!", ip="127.0.0.1", user_agent="test")
            print("Login success:", res)
        except Exception as e:
            print("Login error:", type(e), e)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_login())
