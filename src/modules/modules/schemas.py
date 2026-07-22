from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ModuleResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    is_active: bool
    classes_count: int = 0
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class CreateModuleRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None


class UpdateModuleRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None


class SetModuleStatusRequest(BaseModel):
    is_active: bool
