from src.core.exceptions import AppException


class AssignmentNotFound(AppException):
    status_code = 404
    code = "ASSIGNMENT_NOT_FOUND"
    message = "Assignment not found"


class AssignmentGroupMismatch(AppException):
    status_code = 422
    code = "ASSIGNMENT_GROUP_MISMATCH"
    message = "Session does not belong to the specified group"


class AssignmentGroupsCrossClass(AppException):
    status_code = 422
    code = "ASSIGNMENT_GROUPS_CROSS_CLASS"
    message = "All groups must belong to the same class"


class AssignmentSessionScopeMultiGroupInvalid(AppException):
    status_code = 422
    code = "ASSIGNMENT_SESSION_SCOPE_MULTI_GROUP_INVALID"
    message = "Session scope is only valid with a single group"


class AssignmentNotEffectiveTeacher(AppException):
    status_code = 403
    code = "ASSIGNMENT_NOT_EFFECTIVE_TEACHER"
    message = "You are not the effective teacher of this group"


class SubmissionNotFound(AppException):
    status_code = 404
    code = "SUBMISSION_NOT_FOUND"
    message = "Submission not found"


class StudentNotEnrolled(AppException):
    status_code = 404
    code = "STUDENT_NOT_ENROLLED"
    message = "Student is not enrolled in this group"
