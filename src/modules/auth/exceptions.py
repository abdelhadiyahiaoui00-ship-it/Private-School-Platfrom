from src.core.exceptions import AppException


class InvalidCredentials(AppException):
    status_code = 401
    code = "INVALID_CREDENTIALS"
    message = "Invalid email/phone or password."


class AccountInactive(AppException):
    status_code = 403
    code = "ACCOUNT_INACTIVE"
    message = "This account has been deactivated."


class InvalidRefreshToken(AppException):
    status_code = 401
    code = "INVALID_REFRESH_TOKEN"
    message = "Invalid or expired refresh token."


class WrongCurrentPassword(AppException):
    status_code = 400
    code = "WRONG_CURRENT_PASSWORD"
    message = "The current password provided is incorrect."


class TokenExpired(AppException):
    status_code = 401
    code = "TOKEN_EXPIRED"
    message = "Token has expired."


class TokenInvalid(AppException):
    status_code = 401
    code = "TOKEN_INVALID"
    message = "Invalid token."
