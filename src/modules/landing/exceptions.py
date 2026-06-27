from src.core.exceptions import AppException


class LandingAboutSingleItem(AppException):
    status_code = 422
    code = "LANDING_ABOUT_SINGLE_ITEM"
    message = "The about section must contain exactly 1 item."


class InvalidLandingSection(AppException):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "section must be one of: hero_slide, offer, about."
