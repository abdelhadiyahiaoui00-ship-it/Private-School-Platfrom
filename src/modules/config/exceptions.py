from src.core.exceptions import AppException


class ConfigNotFound(AppException):
    status_code = 404
    code = "CONFIG_NOT_FOUND"
    message = "System config not found. Row id=1 was never seeded."
