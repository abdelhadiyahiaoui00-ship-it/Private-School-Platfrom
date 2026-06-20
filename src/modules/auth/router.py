from fastapi import APIRouter, Depends, Request

from src.modules.auth.dependencies import CurrentUser, get_auth_service
from src.modules.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
)
from src.modules.auth.service import AuthService
from src.modules.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", summary="Login with email/phone")
async def login(
    body: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    result = await service.login(body.identifier, body.password, ip, user_agent)
    
    # We must explicitly validate ORM objects through our response schemas
    user_out = UserResponse.model_validate(result["user"]).model_dump(by_alias=True)
    return {"data": {"tokens": result["tokens"], "user": user_out}}


@router.post("/refresh", summary="Refresh access token")
async def refresh(
    body: RefreshTokenRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    result = await service.refresh_token(body.refresh_token, ip)
    
    user_out = UserResponse.model_validate(result["user"]).model_dump(by_alias=True)
    return {"data": {"tokens": result["tokens"], "user": user_out}}


@router.post("/logout", summary="Revoke refresh token")
async def logout(
    body: RefreshTokenRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    await service.logout(body.refresh_token, ip)
    return {"message": "Logged out successfully"}


@router.post("/change-password", summary="Change current password")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    actor: CurrentUser,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    await service.change_password(actor.id, body.current_password, body.new_password, ip)
    return {"message": "Password changed successfully"}


@router.post("/forgot-password", summary="Request password reset link")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    await service.forgot_password(body.email, ip)
    return {"message": "If this email is registered, a reset link has been sent."}


@router.post("/reset-password", summary="Reset password using token")
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    await service.reset_password(body.token, body.new_password, ip)
    return {"message": "Password has been reset successfully"}
