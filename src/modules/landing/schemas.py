from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel

VALID_SECTIONS = {"hero_slide", "offer", "about"}
VALID_BADGES = {"new", "on_sale", "popular"}


class ElementPosition(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    vertical: Literal["top", "center", "bottom"]
    vertical_offset: int
    horizontal: Literal["left", "center", "right"]
    horizontal_offset: int

    @field_validator("vertical_offset", "horizontal_offset")
    @classmethod
    def clamp_offset(cls, v: int) -> int:
        return max(0, min(100, v))


class HeroSlidePositions(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    title: ElementPosition
    description: ElementPosition
    cta: ElementPosition


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
    positions: Optional[HeroSlidePositions] = None


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
    positions: Optional[HeroSlidePositions] = None


class UpsertLandingSectionRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    items: list[UpsertLandingItemDTO]
