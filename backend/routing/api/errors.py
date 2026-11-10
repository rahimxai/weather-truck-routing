from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

from ..errors import AppError


def body(code, message, **extra):
    return {"error": {"code": code, "message": message, **extra}}


def error(code, message, status):
    return JsonResponse(body(code, message), status=status)


# Django's default handlers return HTML pages; the frontend expects JSON everywhere.
def bad_request(request, exception):
    return error("BAD_REQUEST", "Bad request.", 400)


def not_found(request, exception):
    return error("NOT_FOUND", "Nothing here. Check the URL.", 404)


def server_error(request):
    return error("SERVER_ERROR", "Something went wrong on our side. Try again.", 500)


def first_message(detail, prefix=""):
    """First readable message from DRF's nested validation errors, e.g. 'origin.lat: ...'."""
    if isinstance(detail, dict):
        key, value = next(iter(detail.items()))
        name = "" if key == "non_field_errors" else f"{prefix}{key}"
        return first_message(value, f"{name}." if name else "")
    if isinstance(detail, list):
        return first_message(detail[0], prefix)
    return f"{prefix[:-1]}: {detail}" if prefix else str(detail)


def api_exception_handler(exc, context):
    """Every API error uses the same {"error": {"code", "message"}} shape."""
    if isinstance(exc, AppError):
        return Response(body(exc.code, exc.message), status=exc.status)
    if isinstance(exc, ValidationError):
        return Response(
            body("INVALID_INPUT", first_message(exc.detail), fields=exc.detail), status=400
        )
    resp = exception_handler(exc, context)
    if resp is not None:
        code = getattr(exc, "default_code", "error").upper()
        resp.data = body(code, str(resp.data.get("detail", "Request failed.")))
    return resp
