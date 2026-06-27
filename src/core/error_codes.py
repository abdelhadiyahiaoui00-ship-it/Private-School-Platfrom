from enum import Enum


class ErrorCode(str, Enum):
    # ─── Auth ────────────────────────────────────────────────────────────────
    VALIDATION_ERROR = "VALIDATION_ERROR"
    WRONG_CURRENT_PASSWORD = "WRONG_CURRENT_PASSWORD"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_REFRESH_TOKEN = "INVALID_REFRESH_TOKEN"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"

    # ─── Authorization ───────────────────────────────────────────────────────
    FORBIDDEN = "FORBIDDEN"
    FORBIDDEN_BRANCH = "FORBIDDEN_BRANCH"

    # ─── Users ───────────────────────────────────────────────────────────────
    NOT_FOUND = "NOT_FOUND"
    EMAIL_OR_PHONE_TAKEN = "EMAIL_OR_PHONE_TAKEN"
    LINK_ALREADY_EXISTS = "LINK_ALREADY_EXISTS"
    USER_HAS_ACTIVE_DEPENDENCIES = "USER_HAS_ACTIVE_DEPENDENCIES"
    CANNOT_DELETE_SELF = "CANNOT_DELETE_SELF"
    CANNOT_DELETE_LAST_OWNER = "CANNOT_DELETE_LAST_OWNER"
    PARENT_REQUIRES_STUDENT = "PARENT_REQUIRES_STUDENT"
    ADMIN_REQUIRES_BRANCH = "ADMIN_REQUIRES_BRANCH"

    # ─── Rate Limiting ───────────────────────────────────────────────────────
    RATE_LIMITED = "RATE_LIMITED"

    # ─── Branches ────────────────────────────────────────────────────────────
    BRANCH_NAME_TAKEN = "BRANCH_NAME_TAKEN"
    BRANCH_HAS_ACTIVE_DEPENDENCIES = "BRANCH_HAS_ACTIVE_DEPENDENCIES"
    TOO_MANY_PHOTOS = "TOO_MANY_PHOTOS"
    INVALID_MAP_URL = "INVALID_MAP_URL"

    # ─── Config ──────────────────────────────────────────────────────────────
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"

    # ─── Landing ─────────────────────────────────────────────────────────────
    LANDING_ABOUT_SINGLE_ITEM = "LANDING_ABOUT_SINGLE_ITEM"

    # ─── Server ──────────────────────────────────────────────────────────────
    INTERNAL_ERROR = "INTERNAL_ERROR"
