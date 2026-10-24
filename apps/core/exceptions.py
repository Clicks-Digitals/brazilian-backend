from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

STATUS_CODES = {
    400: "validation_error",
    401: "authentication_error",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    429: "throttled",
}


class APIError(APIException):
    status_code = 400
    default_code = "error"

    def __init__(self, message, code=None, status=None, details=None):
        self.status_code = status or self.status_code
        self.default_code = code or self.default_code
        payload = {"detail": message, "code": self.default_code}
        if details:
            payload["details"] = details
        super().__init__(detail=payload)


def _first_message(data):
    if isinstance(data, list) and data:
        return _first_message(data[0])
    if isinstance(data, dict):
        for value in data.values():
            return _first_message(value)
    return str(data)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    fallback = STATUS_CODES.get(response.status_code, "error")
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        payload = {
            "error": {
                "code": fallback,
                "message": str(data["detail"]),
                "details": {},
            }
        }
    elif isinstance(data, dict):
        nested_details = data.get("details")
        message = data.get("detail") or data.get("message")
        if message is None:
            message = _first_message(data) or "Request could not be processed."
        extra = {
            k: v
            for k, v in data.items()
            if k not in {"detail", "message", "code", "details"}
        }
        if isinstance(nested_details, dict):
            extra = {**nested_details, **extra}
        payload = {
            "error": {
                "code": data.get("code") if isinstance(data.get("code"), str) else fallback,
                "message": str(message),
                "details": extra,
            }
        }
    else:
        payload = {
            "error": {
                "code": fallback,
                "message": _first_message(data) or "Request could not be processed.",
                "details": data,
            }
        }
    response.data = payload
    return response
