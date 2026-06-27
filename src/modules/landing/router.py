from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

from src.core.database import DBSessionDep
from src.modules.auth.dependencies import require_role
from src.modules.landing.schemas import (
    LandingContentResponse,
    UpsertLandingSectionRequest,
)
from src.modules.landing.service import LandingService
from src.modules.users.models import User

router = APIRouter(prefix="/landing-content", tags=["Landing Content"])


def get_landing_service(session: DBSessionDep) -> LandingService:
    return LandingService(session)


@router.get("", summary="Get landing content (public)")
async def get_landing_content(
    service: LandingService = Depends(get_landing_service),
    section: Optional[str] = Query(None),
    active_only: bool = Query(True, alias="activeOnly"),
):
    """Public endpoint — no auth required."""
    items = await service.get_content(section=section, active_only=active_only)
    return {
        "data": {
            "items": [i.model_dump(by_alias=True) for i in items]
        }
    }


@router.put("/{section}", summary="Replace all content for a section (owner/superAdmin only)")
async def update_section(
    section: str,
    body: UpsertLandingSectionRequest,
    request: Request,
    actor: User = Depends(require_role(["owner", "superAdmin"])),
    service: LandingService = Depends(get_landing_service),
):
    result = await service.update_section(
        section,
        body,
        actor,
        ip=request.client.host if request.client else None,
    )
    return {"data": result}
