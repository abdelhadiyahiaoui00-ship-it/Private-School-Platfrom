from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BranchBasicResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: int
    name: str
    is_active: bool


class BranchResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_embed_url: Optional[str] = None
    photo_urls: list[str] = []
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Computed counts (0 until classes module is built in Sprint 4)
    active_classes_count: int = 0
    total_users_count: int = 0


class BranchStats(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    total: int
    active: int
    inactive: int


class CreateBranchRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_embed_url: Optional[str] = None
    photo_urls: list[str] = []
    description: Optional[str] = None
    is_active: bool = True


class UpdateBranchRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_embed_url: Optional[str] = None
    photo_urls: Optional[list[str]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SetBranchStatusRequest(BaseModel):
    is_active: bool
