import asyncio
import sys
from src.app import app  # This ensures all routes and models are imported

from src.core.database import sessionmanager
from src.modules.groups.service import GroupService
from src.modules.users.models import User

async def main():
    async with sessionmanager.session() as session:
        # Create a mock user
        actor = User(id=1, role="superAdmin", permissions={"manageClasses": True})
        
        service = GroupService(session)
        try:
            print("Testing list_groups...")
            res = await service.list_groups({}, actor)
            print("list_groups ok:", len(res['items']), "items")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(main())
