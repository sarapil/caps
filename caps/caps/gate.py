# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS Permission Gate — Module-level proxy.
Re-exports from the root caps.gate module for consistency
with the standard <app>/caps/gate.py pattern.
"""

from caps.gate import has_capability, check_user_capability  # noqa: F401
