from rest_framework.views import exception_handler

from utils.persian_errors import extract_error_message


def persian_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    message = extract_error_message(response.data)
    response.data = {"error": message}
    return response
