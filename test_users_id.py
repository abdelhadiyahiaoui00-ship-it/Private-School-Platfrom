import asyncio
from src.app import app
from src.core.database import sessionmanager
from src.modules.users.service import UserService
from src.modules.users.models import User

async def main():
    async with sessionmanager.session() as session:
        actor = User(id=1, role="superAdmin")
        service = UserService(session)
        try:
            print("Testing get_user...")
            # We'll get user with ID 1 which usually exists
            res = await service.get_user(1, actor)
            print("get_user ok:", res)
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(main())
