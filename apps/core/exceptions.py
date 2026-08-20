"""
Project-wide DRF exception handler.

Normalizes every DRF error response into a single consistent shape:

    {
        "detail": "Human readable summary.",
        "code": "some_error_code",
        "errors": { "field_name": ["..."], ... }
    }

so API consumers never need to branch on whether a given endpoint returns a
plain string, a list, or a nested dict (DRF's default behavior varies by
exception type).
"""

from __future__ import annotations

from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        # Not a DRF-recognized exception (e.g. an unhandled Python
        # exception) — let Django's normal 500 handling deal with it.
        return response

    data = response.data
    code = getattr(exc, "default_code", exc.__class__.__name__.lower())

    if isinstance(data, dict) and set(data.keys()) == {"detail"}:
        detail = data["detail"]
        message = str(detail)
        code = getattr(detail, "code", code)
        errors: dict = {}
    elif isinstance(data, list):
        message = "Validation failed."
        errors = {"non_field_errors": data}
    elif isinstance(data, dict):
        message = "Validation failed."
        errors = data
    else:
        message = str(data)
        errors = {}

    response.data = {"detail": message, "code": code, "errors": errors}
    return response
