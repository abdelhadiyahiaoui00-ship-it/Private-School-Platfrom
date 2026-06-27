from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.landing.models import LandingPageContent


class LandingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_section(
        self,
        section: Optional[str] = None,
        active_only: bool = False,
    ) -> list[LandingPageContent]:
        q = select(LandingPageContent)
        if section:
            q = q.where(LandingPageContent.section == section)
        if active_only:
            q = q.where(LandingPageContent.is_active == True)  # noqa: E712
        q = q.order_by(LandingPageContent.display_order.asc())
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def replace_section(
        self,
        section: str,
        items: list[dict],
    ) -> list[LandingPageContent]:
        """Full replace: delete all rows for section, then insert new rows."""
        await self._session.execute(
            delete(LandingPageContent).where(LandingPageContent.section == section)
        )
        new_rows = []
        now = datetime.now(timezone.utc)
        for item in items:
            row = LandingPageContent(
                section=section,
                title=item.get("title"),
                subtitle=item.get("subtitle"),
                description=item.get("description"),
                image_url=item.get("image_url"),
                link_url=item.get("link_url"),
                badge=item.get("badge"),
                display_order=item.get("display_order", 0),
                is_active=item.get("is_active", True),
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
            new_rows.append(row)
        await self._session.flush()
        for row in new_rows:
            await self._session.refresh(row)
        return new_rows
