from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import require_role
from src.modules.config.models import SystemConfig
from src.modules.config.schemas import AboutStat, SocialLinks, SystemConfigResponse, UpdateConfigRequest
from src.modules.config.service import ConfigService
from src.modules.users.models import User

router = APIRouter(prefix="/config", tags=["Config"])
limiter = Limiter(key_func=get_remote_address)

FALLBACK_CONFIG = {
    "id": 1,
    "defaultLanguage": "ar",
    "schoolName": "Académie Al-Nour",
    "contactEmail": None,
    "contactPhone": None,
    "address": None,
    "foundingYear": None,
    "logoUrl": None,
    "wideLogoUrl": None,
    "faviconUrl": None,
    "aboutTitle": None,
    "aboutDescription": None,
    "aboutStats": [],
    "socialLinks": {"facebook": None, "instagram": None, "youtube": None, "whatsapp": None},
    "monthlyDefaultDurationDays": 30,
    "monthlyExpiryWarningDays": 3,
    "sessionBasedExpiryWarningSessions": 3,
    "updatedAt": None,
    "updatedBy": None,
}


def get_config_service(session: DBSessionDep) -> ConfigService:
    return ConfigService(session)


@router.get("", summary="Get system config (public)")
@limiter.limit("30/minute")
async def get_config(request: Request, session: DBSessionDep):
    """Public endpoint — no auth required."""
    result = await session.execute(select(SystemConfig).limit(1))
    config = result.scalar_one_or_none()
    if not config:
        return {"data": FALLBACK_CONFIG}
    service = ConfigService(session)
    response = service._to_response(config)
    return {"data": response.model_dump(by_alias=True)}


@router.put("", summary="Update system config (owner/superAdmin only)")
async def update_config(
    body: UpdateConfigRequest,
    request: Request,
    actor: User = Depends(require_role(["owner", "superAdmin"])),
    service: ConfigService = Depends(get_config_service),
):
    result = await service.update(
        body.model_dump(exclude_none=True, by_alias=False),
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": result.model_dump(by_alias=True)}
