from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.users.schemas import UserResponse


class LoginRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    identifier: str  # email or phone
    password: str


class AuthTokens(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    access_token: str
    refresh_token: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    tokens: AuthTokens
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    email: str


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    token: str
    new_password: str
