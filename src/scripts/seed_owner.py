import asyncio
import logging
import sys

# Adjust the path to import from src
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import sessionmanager
from src.core.security import hash_password
from src.modules.users.models import User
from src.modules.users.repository import UserRepository
from src.modules.branches.models import Branch  # Import to ensure SQLAlchemy registry has Branch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_owner():
    async with sessionmanager.session() as session:
        repo = UserRepository(session)
        
        # Check if the owner already exists
        existing_owner = await repo.get_by_email(settings.OWNER_EMAIL)
        if existing_owner:
            logger.info(f"Owner user '{settings.OWNER_EMAIL}' already exists. Skipping seed.")
            return

        # Create the owner user
        owner_user = User(
            email=settings.OWNER_EMAIL,
            password_hash=hash_password(settings.OWNER_PASSWORD),
            first_name=settings.OWNER_FIRST_NAME,
            last_name=settings.OWNER_LAST_NAME,
            role="owner",
            status="active",
            permissions={
                "manageUsers": True,
                "manageBranches": True,
                "manageBilling": True,
                "allAccess": True
            },
            must_change_password=False,
        )
        
        session.add(owner_user)
        await session.commit()
        logger.info(f"Successfully seeded owner user: {settings.OWNER_EMAIL}")

if __name__ == "__main__":
    asyncio.run(seed_owner())
