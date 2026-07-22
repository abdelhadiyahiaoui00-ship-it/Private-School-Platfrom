from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.audit.service import log_action
from src.modules.config.exceptions import ConfigNotFound
from src.modules.config.models import SystemConfig
from src.modules.config.schemas import AboutStat, SocialLinks, SystemConfigResponse
from src.modules.users.models import User


class ConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> SystemConfigResponse:
        result = await self._session.execute(
            select(SystemConfig).where(SystemConfig.id == 1)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ConfigNotFound()
        return self._to_response(config)

    async def update(self, data: dict, actor: User, ip: Optional[str] = None) -> SystemConfigResponse:
        result = await self._session.execute(
            select(SystemConfig).where(SystemConfig.id == 1)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ConfigNotFound()

        # Validation
        if "monthly_default_duration_days" in data and data["monthly_default_duration_days"] is not None:
            v = data["monthly_default_duration_days"]
            if not (1 <= v <= 365):
                from src.core.exceptions import ValidationError
                raise ValidationError(message="monthlyDefaultDurationDays must be between 1 and 365.")

        if "monthly_expiry_warning_days" in data and data["monthly_expiry_warning_days"] is not None:
            v = data["monthly_expiry_warning_days"]
            if not (1 <= v <= 30):
                from src.core.exceptions import ValidationError
                raise ValidationError(message="monthlyExpiryWarningDays must be between 1 and 30.")

        if "session_based_expiry_warning_sessions" in data and data["session_based_expiry_warning_sessions"] is not None:
            v = data["session_based_expiry_warning_sessions"]
            if not (1 <= v <= 20):
                from src.core.exceptions import ValidationError
                raise ValidationError(message="sessionBasedExpiryWarningSessions must be between 1 and 20.")

        if "session_generation_horizon_weeks" in data and data["session_generation_horizon_weeks"] is not None:
            v = data["session_generation_horizon_weeks"]
            if not (1 <= v <= 52):
                from src.core.exceptions import ValidationError
                raise ValidationError(message="sessionGenerationHorizonWeeks must be between 1 and 52.")

        if "founding_year" in data and data["founding_year"] is not None:
            current_year = date.today().year
            if not (1900 <= data["founding_year"] <= current_year):
                from src.core.exceptions import ValidationError
                raise ValidationError(message=f"foundingYear must be between 1900 and {current_year}.")

        changed = []
        scalar_fields = [
            "default_language", "school_name", "contact_email", "contact_phone",
            "address", "founding_year", "logo_url", "wide_logo_url", "favicon_url",
            "about_title", "about_description",
            "monthly_default_duration_days", "monthly_expiry_warning_days",
            "session_based_expiry_warning_sessions", "session_generation_horizon_weeks",
        ]
        for field in scalar_fields:
            if field in data:
                setattr(config, field, data[field])
                changed.append(field)

        if "about_stats" in data and data["about_stats"] is not None:
            config.about_stats = [
                s.model_dump() if hasattr(s, "model_dump") else s
                for s in data["about_stats"]
            ]
            changed.append("aboutStats")

        if "social_links" in data and data["social_links"] is not None:
            sl = data["social_links"]
            config.social_links = (
                sl.model_dump() if hasattr(sl, "model_dump") else sl
            )
            changed.append("socialLinks")

        config.updated_at = datetime.now(timezone.utc)
        config.updated_by = actor.id

        merged = await self._session.merge(config)
        await self._session.flush()
        await self._session.refresh(merged)

        await log_action(
            self._session,
            user_id=actor.id,
            action="SYSTEM_CONFIG_UPDATED",
            category="system",
            entity_type="system_config",
            entity_id=1,
            metadata={"changedFields": changed},
            ip_address=ip,
        )

        return self._to_response(merged)

    def _to_response(self, config: SystemConfig) -> SystemConfigResponse:
        about_stats = []
        for s in (config.about_stats or []):
            if isinstance(s, dict):
                about_stats.append(AboutStat(**s))
            else:
                about_stats.append(s)

        raw_sl = config.social_links or {}
        if isinstance(raw_sl, dict):
            social_links = SocialLinks(**raw_sl)
        else:
            social_links = raw_sl

        return SystemConfigResponse(
            id=config.id,
            default_language=config.default_language,
            school_name=config.school_name,
            contact_email=config.contact_email,
            contact_phone=config.contact_phone,
            address=config.address,
            founding_year=config.founding_year,
            logo_url=config.logo_url,
            wide_logo_url=config.wide_logo_url,
            favicon_url=config.favicon_url,
            about_title=config.about_title,
            about_description=config.about_description,
            about_stats=about_stats,
            social_links=social_links,
            monthly_default_duration_days=config.monthly_default_duration_days,
            monthly_expiry_warning_days=config.monthly_expiry_warning_days,
            session_based_expiry_warning_sessions=config.session_based_expiry_warning_sessions,
            session_generation_horizon_weeks=config.session_generation_horizon_weeks,
            updated_at=config.updated_at,
            updated_by=config.updated_by,
        )
