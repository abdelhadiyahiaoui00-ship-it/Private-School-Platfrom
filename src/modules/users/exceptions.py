from src.core.exceptions import AppException


# ─── User not found ───────────────────────────────────────────────────────────
class UserNotFound(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "User not found."


# ─── Unique constraint violations ─────────────────────────────────────────────
class EmailOrPhoneTaken(AppException):
    status_code = 409
    code = "EMAIL_OR_PHONE_TAKEN"
    message = "This email or phone number is already in use."


# ─── Parent-student link ──────────────────────────────────────────────────────
class LinkAlreadyExists(AppException):
    status_code = 409
    code = "LINK_ALREADY_EXISTS"
    message = "This parent-student link already exists."


class ParentRequiresStudent(AppException):
    status_code = 422
    code = "PARENT_REQUIRES_STUDENT"
    message = "A parent account must be linked to at least one student."


# ─── Admin constraints ────────────────────────────────────────────────────────
class AdminRequiresBranch(AppException):
    status_code = 422
    code = "ADMIN_REQUIRES_BRANCH"
    message = "An admin account must be assigned to at least one branch."


# ─── Delete/status guards ─────────────────────────────────────────────────────
class CannotDeleteSelf(AppException):
    status_code = 409
    code = "CANNOT_DELETE_SELF"
    message = "You cannot delete or deactivate your own account."


class CannotDeleteLastOwner(AppException):
    status_code = 409
    code = "CANNOT_DELETE_LAST_OWNER"
    message = "Cannot delete the last owner account in the system."


class UserHasActiveDependencies(AppException):
    status_code = 409
    code = "USER_HAS_ACTIVE_DEPENDENCIES"
    message = "This user has active data and cannot be deleted."
