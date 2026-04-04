# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Formatters
Display formatting utilities for CAPS.
"""

import frappe
from frappe.utils import fmt_money, format_date, format_datetime, flt


def format_currency(amount, currency=None):
    """Format amount as currency string."""
    currency = currency or frappe.defaults.get_global_default("currency") or "USD"
    return fmt_money(flt(amount), currency=currency)


def format_percentage(value, precision=1):
    """Format value as percentage string."""
    return f"{flt(value, precision)}%"


def format_date_short(date_value):
    """Format date in short user-friendly format."""
    return format_date(date_value, "dd MMM yyyy") if date_value else ""


def format_datetime_short(dt_value):
    """Format datetime in short user-friendly format."""
    return format_datetime(dt_value, "dd MMM yyyy HH:mm") if dt_value else ""


def truncate(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis."""
    if not text or len(text) <= max_length:
        return text or ""
    return text[:max_length - 3] + "..."


def format_file_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
