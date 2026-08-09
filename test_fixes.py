import asyncio
from httpx import AsyncClient, ASGITransport
from src.app import app
from src.modules.users.models import User
from src.modules.enrollments.models import Enrollment
from src.modules.subscriptions.models import Subscription
from src.modules.groups.models import Group
from src.modules.classes.models import Class
from src.modules.auth.dependencies import require_manage_subscriptions, require_role, require_manage_enrollments
from src.modules.groups.router import require_manage_classes
from src.core.database import sessionmanager
from sqlalchemy import select

async def override_dependency():
    async with sessionmanager.session() as db:
        res = await db.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        if not user:
            user = User(id=1, email='admin@test.com', role='superAdmin')
        user.role = 'superAdmin'
        return user

app.dependency_overrides[require_manage_subscriptions] = override_dependency
app.dependency_overrides[require_manage_enrollments] = override_dependency
app.dependency_overrides[require_manage_classes] = override_dependency

async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        # TEST 1: GET /payments?sortBy=recordedAt
        r = await client.get('/api/payments?page=1&pageSize=10&sortBy=recordedAt&sortOrder=desc')
        print('GET /payments (Fix 2):', r.status_code)
        
        # TEST 2: GET /branches
        r2 = await client.get('/api/branches')
        print('GET /branches (Fix 3A):', r2.status_code)
        if r2.status_code == 200:
            items = r2.json()['data']['items']
            if items:
                print('Branch 0 activeClassesCount:', items[0].get('activeClassesCount'))
        
        # TEST 3: GET /classes (Fix 3B scheduleSummary)
        r3 = await client.get('/api/classes')
        print('GET /classes (Fix 3B):', r3.status_code)
        if r3.status_code == 200:
            items = r3.json()['data']['items']
            if items and items[0].get('groupsSummary'):
                print('Class 0 Group 0 scheduleSummary:', items[0]['groupsSummary'][0].get('scheduleSummary'))
                
        # TEST 4: GET /sessions (Fix 4 Teachers filter)
        r4 = await client.get('/api/sessions')
        print('GET /sessions (Fix 4):', r4.status_code)
        if r4.status_code == 200:
            filters = r4.json()['data']['filters']
            print('Sessions Filters Teachers count:', len(filters.get('teachers', [])))
            print('Teachers array:', filters.get('teachers', []))

asyncio.run(main())
