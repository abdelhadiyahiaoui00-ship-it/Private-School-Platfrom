from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import DBSessionDep
from src.modules.config.models import SystemConfig
from src.modules.config.schemas import SystemConfigResponse

router = APIRouter(prefix="/config", tags=["Config"])

FALLBACK_CONFIG = {
    "id": 1,
    "default_language": "ar",
    "school_name": "Académie Al-Nour",
    "contact_email": None,
    "contact_phone": None,
    "monthly_default_duration_days": 30,
    "monthly_expiry_warning_days": 3,
    "session_based_expiry_warning_sessions": 3,
}


@router.get("", summary="Get system config")
async def get_config(session: DBSessionDep):
    result = await session.execute(select(SystemConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        return {"data": FALLBACK_CONFIG}
    return {"data": SystemConfigResponse.model_validate(config).model_dump(by_alias=True)}
