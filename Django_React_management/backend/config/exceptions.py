from rest_framework.views import exception_handler

from module_api.persian_errors import extract_error_message


def persian_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    if isinstance(data, dict) and "error" in data and len(data) == 1:
        message = extract_error_message(data)
        response.data = {"error": message}
        return response

    message = extract_error_message(data)
    response.data = {"error": message}
    return response
