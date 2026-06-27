from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.audit.service import log_action
from src.modules.landing.exceptions import LandingAboutSingleItem, InvalidLandingSection
from src.modules.landing.repository import LandingRepository
from src.modules.landing.schemas import (
    LandingContentResponse,
    UpsertLandingSectionRequest,
    VALID_SECTIONS,
)
from src.modules.users.models import User


class LandingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = LandingRepository(session)

    async def get_content(
        self,
        section: Optional[str] = None,
        active_only: bool = True,
    ) -> list[LandingContentResponse]:
        if section and section not in VALID_SECTIONS:
            raise InvalidLandingSection()
        items = await self._repo.get_by_section(section=section, active_only=active_only)
        return [LandingContentResponse.model_validate(i) for i in items]

    async def update_section(
        self,
        section: str,
        body: UpsertLandingSectionRequest,
        actor: User,
        ip: Optional[str] = None,
    ) -> dict:
        if section not in VALID_SECTIONS:
            raise InvalidLandingSection()

        items_data = body.items

        # Enforce about section = exactly 1 item
        if section == "about" and len(items_data) != 1:
            raise LandingAboutSingleItem()

        # Validate section-specific required fields
        for item in items_data:
            if section == "hero_slide" and not item.image_url:
                from src.core.exceptions import ValidationError
                raise ValidationError(message="imageUrl is required for hero_slide items.")
            if section == "offer":
                if not item.image_url:
                    from src.core.exceptions import ValidationError
                    raise ValidationError(message="imageUrl is required for offer items.")
                if not item.title:
                    from src.core.exceptions import ValidationError
                    raise ValidationError(message="title is required for offer items.")

        raw_items = [item.model_dump(by_alias=False) for item in items_data]
        await self._repo.replace_section(section, raw_items)

        await log_action(
            self._session,
            user_id=actor.id,
            action="LANDING_CONTENT_UPDATED",
            category="system",
            entity_type="landing_page_content",
            metadata={"section": section, "itemCount": len(items_data)},
            ip_address=ip,
        )

        return {"section": section, "itemCount": len(items_data)}
