import asyncio
from src.app import app
from src.core.database import sessionmanager
from sqlalchemy import select
from src.modules.classes.repository import ClassRepository
from src.modules.sessions.repository import SessionRepository
from src.modules.sessions.service import SessionService
from src.modules.users.models import User
from src.modules.classes.models import Class
from src.modules.classes.service import _format_schedule_summary

async def main():
    async with sessionmanager.session() as db:
        # Test 2
        active = await ClassRepository(db).count_active_for_branch(1)
        print("Active classes for branch 1:", active)
        
        # Test 3
        summary = _format_schedule_summary([{"day_of_week": 0, "start_time": "08:00:00", "end_time": "10:00:00"}])
        print("Schedule summary output:", summary)
        
        # Test 4
        # Just manually check list_sessions response payload
        user = User(id=1, role="superAdmin")
        sessions_res = await SessionService(db).list_sessions({"page": 1, "page_size": 10}, user)
        filters = sessions_res.get("filters", {})
        print("Sessions teachers filters count:", len(filters.get("teachers", [])))
        print("Teachers list:", filters.get("teachers"))

asyncio.run(main())
