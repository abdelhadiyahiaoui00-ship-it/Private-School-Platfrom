from typing import Any, Optional


class AppException(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."
    details: Optional[list[dict[str, Any]]] = None

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.code = code or self.__class__.code
        self.status_code = status_code or self.__class__.status_code
        self.details = details or self.__class__.details
        super().__init__(self.message)


class ResourceNotFound(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "Resource not found."


class PermissionDenied(AppException):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class ForbiddenBranch(AppException):
    status_code = 403
    code = "FORBIDDEN_BRANCH"
    message = "You do not have access to this branch."


class Unauthorized(AppException):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "Authentication required."


class ValidationError(AppException):
    status_code = 400
    code = "VALIDATION_ERROR"
    message = "Validation failed."


class Conflict(AppException):
    status_code = 409
    code = "CONFLICT"
    message = "A conflict occurred."
