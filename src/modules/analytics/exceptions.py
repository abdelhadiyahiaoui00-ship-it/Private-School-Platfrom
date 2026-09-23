from src.core.error_codes import ErrorCode
from src.core.exceptions import AppException


class AnalyticsPeriodInvalid(AppException):
    status_code = 400
    code = ErrorCode.ANALYTICS_PERIOD_INVALID
    message = "Requested period is invalid or in the future."


class AnalyticsExportEmpty(AppException):
    status_code = 404
    code = ErrorCode.ANALYTICS_EXPORT_EMPTY
    message = "No payment data found for the requested export range."
