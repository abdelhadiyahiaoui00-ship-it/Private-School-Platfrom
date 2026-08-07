import asyncio
import uvicorn
from src.app import app
from src.modules.users.models import User
from src.modules.auth.dependencies import require_manage_subscriptions, require_role, require_manage_enrollments
from src.modules.groups.router import require_manage_classes
from src.core.database import sessionmanager
from sqlalchemy import select

async def get_real_user():
    async with sessionmanager.session() as db:
        res = await db.execute(select(User).limit(1))
        return res.scalar_one_or_none()

def override_dependency():
    user = asyncio.run(get_real_user())
    if not user:
        user = User(id=1, email="admin@test.com", role="superAdmin")
    return user

def override_require_role(*args, **kwargs):
    def dep():
        return override_dependency()
    return dep

app.dependency_overrides[require_manage_subscriptions] = override_dependency
app.dependency_overrides[require_manage_enrollments] = override_dependency
app.dependency_overrides[require_manage_classes] = override_dependency
app.dependency_overrides[require_role] = override_require_role

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
