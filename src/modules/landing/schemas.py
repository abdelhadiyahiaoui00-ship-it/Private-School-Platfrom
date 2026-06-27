from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

VALID_SECTIONS = {"hero_slide", "offer", "about"}
VALID_BADGES = {"new", "on_sale", "popular"}


class LandingContentResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: int
    section: str
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    badge: Optional[str] = None
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UpsertLandingItemDTO(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: Optional[int] = None          # ignored on server
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    badge: Optional[str] = None
    display_order: int
    is_active: bool


class UpsertLandingSectionRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    items: list[UpsertLandingItemDTO]
