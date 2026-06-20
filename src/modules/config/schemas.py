from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SystemConfigResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: int
    default_language: str
    school_name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    monthly_default_duration_days: int
    monthly_expiry_warning_days: int
    session_based_expiry_warning_sessions: int
