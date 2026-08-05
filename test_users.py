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
            print("Testing list_users...")
            res = await service.list_users(actor=actor)
            print("list_users ok:", len(res['items']), "items")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(main())
