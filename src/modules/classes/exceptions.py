from src.core.exceptions import AppException


class ClassNotFound(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "Class not found."


class ClassHasActiveDependencies(AppException):
    status_code = 409
    code = "CLASS_HAS_ACTIVE_DEPENDENCIES"
    message = "Cannot delete a class that has sessions."


class InvalidLevelTargeting(AppException):
    status_code = 422
    code = "INVALID_LEVEL_TARGETING"
    message = "Level targeting fields are inconsistent."


class TeacherNotAssignedToBranch(AppException):
    status_code = 422
    code = "TEACHER_NOT_ASSIGNED_TO_BRANCH"
    message = "The selected teacher is not assigned to this branch."
