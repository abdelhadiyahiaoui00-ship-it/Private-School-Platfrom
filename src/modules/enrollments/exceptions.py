from src.core.exceptions import AppException


class EnrollmentNotFound(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "Enrollment not found."


class VisitorRequestNotFound(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "Visitor enrollment request not found."


class AlreadyEnrolled(AppException):
    status_code = 409
    code = "ALREADY_ENROLLED"
    message = "This student already has an active enrollment in this group."


class GroupFull(AppException):
    status_code = 409
    code = "GROUP_FULL"
    message = "No seats available in this group."


class NotLinkedChild(AppException):
    status_code = 403
    code = "NOT_LINKED_CHILD"
    message = "You can only enroll students linked to your account."


class VisitorRequestAlreadyResolved(AppException):
    status_code = 409
    code = "VISITOR_REQUEST_ALREADY_RESOLVED"
    message = "This visitor request has already been converted or rejected."


class ParentActionRequired(AppException):
    status_code = 422
    code = "PARENT_ACTION_REQUIRED"
    message = "parentAction details are missing or inconsistent."


class CannotCancelActiveWithSubscription(AppException):
    status_code = 409
    code = "CANNOT_CANCEL_ACTIVE_WITH_SUBSCRIPTION"
    message = "Cannot cancel an active enrollment with an existing subscription. Cancel the subscription first."


# ─── Transfer Exceptions (Sprint 10) ─────────────────────────────────────────

class TransferSameGroup(AppException):
    status_code = 422
    code = "TRANSFER_SAME_GROUP"
    message = "Target group is the same as the current group."


class TransferTargetDifferentClass(AppException):
    status_code = 422
    code = "TRANSFER_TARGET_DIFFERENT_CLASS"
    message = "Target group must belong to the same class."


class TransferTargetFull(AppException):
    status_code = 409
    code = "TRANSFER_TARGET_FULL"
    message = "Target group has no available seats."


class TransferInvalidSourceStatus(AppException):
    status_code = 409
    code = "TRANSFER_INVALID_SOURCE_STATUS"
    message = "Enrollment must be active or pending to transfer."

