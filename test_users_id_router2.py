import asyncio
from src.app import app
from src.core.database import sessionmanager
from src.modules.users.service import UserService
from src.modules.users.models import User
from src.modules.users.schemas import UserDetailResponse

async def main():
    async with sessionmanager.session() as session:
        actor = User(id=1, role="superAdmin")
        service = UserService(session)
        try:
            print("Testing get_user router logic with UserDetailResponse...")
            user = await service.get_user(1, actor)
            res = UserDetailResponse.model_validate(user).model_dump(by_alias=True)
            print("get_user mapped ok! keys:", res.keys())
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(main())
