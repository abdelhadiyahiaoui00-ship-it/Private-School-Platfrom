import asyncio
from src.app import app
from src.core.database import sessionmanager
from src.modules.users.service import UserService
from src.modules.users.models import User
from src.modules.users.schemas import UserResponse

async def main():
    async with sessionmanager.session() as session:
        actor = User(id=1, role="superAdmin")
        service = UserService(session)
        try:
            print("Fetching all users to test model mapping...")
            users, total = await service._repo.list_users(page_size=100)
            for u in users:
                try:
                    res = UserResponse.model_validate(u).model_dump(by_alias=True)
                    print(f"User {u.id} ({u.role}) mapped ok")
                except Exception as ex:
                    print(f"User {u.id} ({u.role}) failed mapping: {ex}")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(main())
