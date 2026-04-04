# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Standard API Response Helpers
Consistent response format for all CAPS API endpoints.
"""

import frappe
from frappe import _
import math


def success(data=None, message=None, status_code=200):
    """Return a standardized success response.

    Args:
        data: Response payload (dict, list, or scalar).
        message: Optional human-readable message.
        status_code: HTTP status code (default 200).

    Returns:
        dict: {"status": "success", "data": ..., "message": ...}
    """
    response = {"status": "success"}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = _(message)
    frappe.response["http_status_code"] = status_code
    return response


def error(message, error_code=None, details=None, status_code=400):
    """Return a standardized error response.

    Args:
        message: Human-readable error description.
        error_code: Machine-readable error code (e.g. "VALIDATION_ERROR").
        details: Additional context (dict).
        status_code: HTTP status code (default 400).

    Returns:
        dict: {"status": "error", "error_code": ..., "message": ..., "details": ...}
    """
    response = {
        "status": "error",
        "message": _(message),
    }
    if error_code:
        response["error_code"] = error_code
    if details:
        response["details"] = details
    frappe.response["http_status_code"] = status_code
    return response


def paginated(data, total, page=1, page_size=20):
    """Return a standardized paginated list response.

    Args:
        data: List of items for current page.
        total: Total count of matching items.
        page: Current page number (1-based).
        page_size: Items per page.

    Returns:
        dict: {"status": "success", "data": [...], "meta": {...}}
    """
    page_size = min(page_size, 100)  # Cap at 100
    return {
        "status": "success",
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if page_size else 1,
            "has_next": (page * page_size) < total,
        },
    }
