from src.core.exceptions import AppException


class SubscriptionNotFound(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "Subscription not found."


class EnrollmentNotPending(AppException):
    status_code = 409
    code = "ENROLLMENT_NOT_PENDING"
    message = "Payment confirmation requires the enrollment to be in 'pending' status."


class SubscriptionAlreadyCancelled(AppException):
    status_code = 409
    code = "SUBSCRIPTION_ALREADY_CANCELLED"
    message = "This subscription has already been cancelled."


class InvalidExtensionTarget(AppException):
    status_code = 422
    code = "INVALID_EXTENSION_TARGET"
    message = "daysToAdd applies to monthly subscriptions; sessionsToAdd to session-based subscriptions."


class InvalidExtensionAmount(AppException):
    status_code = 422
    code = "INVALID_EXTENSION_AMOUNT"
    message = "Extension amount must be greater than 0."


class NoActiveSubscriptionsToExtend(AppException):
    status_code = 422
    code = "NO_ACTIVE_SUBSCRIPTIONS_TO_EXTEND"
    message = "No active subscriptions found for this group to extend."


class AmountMustBePositive(AppException):
    status_code = 422
    code = "AMOUNT_MUST_BE_POSITIVE"
    message = "Payment amount must be greater than 0."
