import asyncio
from httpx import AsyncClient, ASGITransport
from src.app import app
from src.modules.users.models import User
from src.modules.auth.dependencies import require_manage_subscriptions, require_role, require_manage_enrollments
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

async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        # TEST 1
        r1 = await client.get('/api/payments?page=1&pageSize=10&sortBy=recordedAt&sortOrder=desc')
        print('GET /payments status:', r1.status_code)
        
        # TEST 2
        r2 = await client.get('/api/sessions')
        print('GET /sessions status:', r2.status_code)
        if r2.status_code == 200:
            items = r2.json()['data']['items']
            if items:
                print('Session 0 branchName:', items[0].get('branchName'))

asyncio.run(main())
