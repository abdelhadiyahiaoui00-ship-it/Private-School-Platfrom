from fastapi import APIRouter, Depends, Request, Response

from src.modules.auth.dependencies import CurrentUser, get_auth_service
from src.modules.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    SignInRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
)
from src.modules.auth.service import AuthService
from src.modules.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/sign-in", summary="Login with email/phone")
async def sign_in(
    body: SignInRequest,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    result = await service.login(body.identifier, body.password, ip, user_agent)
    
    # We must explicitly validate ORM objects through our response schemas
    user_out = UserResponse.model_validate(result["user"]).model_dump(by_alias=True)
    
    response.set_cookie(
        key="school_access_token",
        value=result["tokens"]["access_token"],
        max_age=15 * 60,
        httponly=False,  # Frontend reads this via js-cookie
        samesite="lax",
        secure=True,
    )
    response.set_cookie(
        key="school_refresh_token",
        value=result["tokens"]["refresh_token"],
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=True,
    )
    
    must_change = result["user"].must_change_password
    
    # TODO: REMOVE BEFORE PRODUCTION — access_token exposed for testing only
    return {"data": {"user": user_out, "mustChangePassword": must_change, "accessToken": result["tokens"]["access_token"]}}


@router.post("/refresh", summary="Refresh access token")
async def refresh(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    refresh_token = request.cookies.get("school_refresh_token")
    if not refresh_token:
        # Fallback to header or body if needed, but cookie is standard
        # However, if it's missing, return 401
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    result = await service.refresh_token(refresh_token, ip)
    
    user_out = UserResponse.model_validate(result["user"]).model_dump(by_alias=True)
    
    response.set_cookie(
        key="school_access_token",
        value=result["tokens"]["access_token"],
        max_age=15 * 60,
        httponly=False,
        samesite="lax",
        secure=True,
    )
    response.set_cookie(
        key="school_refresh_token",
        value=result["tokens"]["refresh_token"],
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=True,
    )
    
    return {"data": {"user": user_out}}


@router.post("/sign-out", summary="Revoke refresh token")
async def sign_out(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    refresh_token = request.cookies.get("school_refresh_token")
    if refresh_token:
        await service.logout(refresh_token, ip)
    
    response.delete_cookie("school_access_token")
    response.delete_cookie("school_refresh_token")
    return {"data": {"signedOut": True}}


@router.get("/me", summary="Get current user")
async def get_me(
    actor: CurrentUser,
):
    user_out = UserResponse.model_validate(actor).model_dump(by_alias=True)
    return {"data": user_out}


@router.post("/change-password", summary="Change current password")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    actor: CurrentUser,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    await service.change_password(actor.id, body.current_password, body.new_password, ip)
    return {"data": {"changed": True}}


@router.post("/forgot-password", summary="Request password reset link")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    await service.forgot_password(body.identifier, ip)
    return {"data": {"sent": True}}


@router.post("/reset-password", summary="Reset password using token")
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    ip = request.client.host if request.client else None
    await service.reset_password(body.token, body.new_password, ip)
    return {"data": {"reset": True}}
