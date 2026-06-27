from src.core.exceptions import AppException


class BranchNotFound(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "Branch not found."


class BranchNameTaken(AppException):
    status_code = 409
    code = "BRANCH_NAME_TAKEN"
    message = "A branch with this name already exists."


class BranchHasActiveDependencies(AppException):
    status_code = 409
    code = "BRANCH_HAS_ACTIVE_DEPENDENCIES"
    message = "Branch has active classes or users and cannot be deleted/deactivated."


class TooManyPhotos(AppException):
    status_code = 422
    code = "TOO_MANY_PHOTOS"
    message = "A branch can have at most 10 photos."


class InvalidMapUrl(AppException):
    status_code = 422
    code = "INVALID_MAP_URL"
    message = "mapEmbedUrl must be a valid Google Maps Embed URL (https://www.google.com/maps/embed...)."
