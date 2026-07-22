from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class AboutStat(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    label: str
    value: str
    icon: Optional[str] = None


class SocialLinks(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None
    whatsapp: Optional[str] = None


class SystemConfigResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: int
    default_language: str
    school_name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    founding_year: Optional[int] = None
    logo_url: Optional[str] = None
    wide_logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    about_title: Optional[str] = None
    about_description: Optional[str] = None
    about_stats: list[AboutStat] = []
    social_links: SocialLinks = SocialLinks()
    monthly_default_duration_days: int
    monthly_expiry_warning_days: int
    session_based_expiry_warning_sessions: int
    session_generation_horizon_weeks: int
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None


class UpdateConfigRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    default_language: Optional[str] = None
    school_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    founding_year: Optional[int] = None
    logo_url: Optional[str] = None
    wide_logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    about_title: Optional[str] = None
    about_description: Optional[str] = None
    about_stats: Optional[list[AboutStat]] = None
    social_links: Optional[SocialLinks] = None
    monthly_default_duration_days: Optional[int] = None
    monthly_expiry_warning_days: Optional[int] = None
    session_based_expiry_warning_sessions: Optional[int] = None
    session_generation_horizon_weeks: Optional[int] = None
