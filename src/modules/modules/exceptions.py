from src.core.exceptions import AppException


class ModuleNotFound(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "Module not found."


class ModuleNameTaken(AppException):
    status_code = 409
    code = "MODULE_NAME_TAKEN"
    message = "A module with this name already exists."


class ModuleHasActiveDependencies(AppException):
    status_code = 409
    code = "MODULE_HAS_ACTIVE_DEPENDENCIES"
    message = "Cannot delete a module that has classes."
