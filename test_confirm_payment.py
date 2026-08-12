import asyncio
from src.app import app
from src.modules.users.models import User
from src.modules.enrollments.models import Enrollment
from src.modules.auth.dependencies import require_manage_enrollments
from src.core.database import sessionmanager
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport

async def override_actor():
    async with sessionmanager.session() as db:
        res = await db.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        user.role = 'superAdmin'
        return user

app.dependency_overrides[require_manage_enrollments] = override_actor

async def main():
    # find a pending enrollment
    async with sessionmanager.session() as db:
        res = await db.execute(select(Enrollment).where(Enrollment.status == 'pending').limit(1))
        enroll = res.scalar_one_or_none()
        if not enroll:
            print("No pending enrollment found — can't test confirm-payment")
            return
        print(f"Using pending enrollment ID: {enroll.id}")
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        r = await client.post(
            f'/api/enrollments/{enroll.id}/confirm-payment',
            json={"amount": 500, "method": "cash"}
        )
        print(f"Status: {r.status_code}")
        body = r.json()
        if r.status_code == 200:
            data = body.get('data', {})
            print("Keys returned:", list(data.keys()))
            print("  enrollment.id :", data.get('enrollment', {}).get('id'))
            print("  enrollment.status:", data.get('enrollment', {}).get('status'))
            print("  subscription.id  :", data.get('subscription', {}).get('id'))
            print("  payment.id       :", data.get('payment', {}).get('id'))
            print("  payment.amount   :", data.get('payment', {}).get('amount'))
        else:
            print("Error detail:", body)

asyncio.run(main())
