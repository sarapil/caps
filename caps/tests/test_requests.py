"""
CAPS — Capability Request Workflow Tests
==========================================

Tests for request API (caps.api_requests) and CapabilityRequest controller:
 - submit_request
 - approve_request (auto-grant)
 - reject_request
 - cancel_request
 - duplicate prevention
 - get_my_requests / get_pending_requests

Prefix: capstest_req_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_requests
"""

import frappe
import unittest
from frappe.utils import now_datetime

_TEST_PREFIX = "capstest_req_"

_CAPS = {
    "alpha": f"{_TEST_PREFIX}cap:alpha",
    "beta": f"{_TEST_PREFIX}cap:beta",
    "inactive": f"{_TEST_PREFIX}cap:inactive",
}

_USERS = {
    "requester": f"{_TEST_PREFIX}requester@test.local",
    "approver": f"{_TEST_PREFIX}approver@test.local",
}


def _setup_request_data():
    _teardown_request_data()

    # Create capabilities
    for key, cap_name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": cap_name,
            "label": cap_name,
            "category": "Custom",
            "is_active": 1 if key != "inactive" else 0,
        }).insert(ignore_permissions=True)

    # Create users
    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSReq",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
            }).insert(ignore_permissions=True)

    # Give CAPS Manager role to approver
    approver = frappe.get_doc("User", _USERS["approver"])
    if not any(r.role == "CAPS Manager" for r in approver.roles):
        approver.append("roles", {"role": "CAPS Manager"})
        approver.save(ignore_permissions=True)

    frappe.db.commit()


def _teardown_request_data():
    # Clean requests
    for req in frappe.get_all(
        "Capability Request",
        filters={"capability": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Capability Request", req, force=True, ignore_permissions=True)

    # Clean audit logs
    frappe.db.sql(
        "DELETE FROM `tabCAPS Audit Log` WHERE capability LIKE %s",
        (f"{_TEST_PREFIX}%",),
    )

    # Clean notification logs
    frappe.db.sql(
        "DELETE FROM `tabNotification Log` WHERE subject LIKE %s",
        (f"%{_TEST_PREFIX}%",),
    )

    for email in _USERS.values():
        frappe.cache.delete_value(f"caps:user:{email}")
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email, force=True, ignore_permissions=True)

    for cap_name in _CAPS.values():
        if frappe.db.exists("Capability", cap_name):
            frappe.delete_doc("Capability", cap_name, force=True, ignore_permissions=True)

    for email in _USERS.values():
        _safe_delete_user(email)

    frappe.db.commit()


def _safe_delete_user(email):
    """Delete user, handling linked docs from other apps."""
    if not frappe.db.exists("User", email):
        return
    try:
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    except Exception:
        try:
            for dt in ("GP User Profile",):
                for name in frappe.get_all(dt, filters={"user": email}, pluck="name"):
                    frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        except Exception:
            pass


def _as_user(email):
    class _Ctx:
        def __init__(self):
            self.old = frappe.session.user
        def __enter__(self):
            frappe.set_user(email)
            return self
        def __exit__(self, *args):
            frappe.set_user(self.old)
    return _Ctx()


# ── Tests ─────────────────────────────────────────────────────────────


class TestSubmitRequest(unittest.TestCase):
    """Tests for caps.api_requests.submit_request."""

    @classmethod
    def setUpClass(cls):
        _setup_request_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_request_data()

    def _clean_requests(self):
        for req in frappe.get_all(
            "Capability Request",
            filters={"capability": ("like", f"{_TEST_PREFIX}%")},
            pluck="name",
        ):
            frappe.delete_doc("Capability Request", req, force=True, ignore_permissions=True)

    def test_submit_success(self):
        self._clean_requests()
        from caps.api_requests import submit_request

        with _as_user(_USERS["requester"]):
            result = submit_request(
                capability=_CAPS["alpha"],
                reason="Need for project X",
            )

        self.assertEqual(result["status"], "submitted")
        self.assertTrue(result["request"])

        doc = frappe.get_doc("Capability Request", result["request"])
        self.assertEqual(doc.user, _USERS["requester"])
        self.assertEqual(doc.status, "Pending")
        self.assertEqual(doc.priority, "Medium")

    def test_submit_inactive_cap_fails(self):
        self._clean_requests()
        from caps.api_requests import submit_request

        with _as_user(_USERS["requester"]):
            with self.assertRaises(frappe.exceptions.ValidationError):
                submit_request(
                    capability=_CAPS["inactive"],
                    reason="Want inactive",
                )

    def test_duplicate_pending_fails(self):
        self._clean_requests()
        from caps.api_requests import submit_request

        with _as_user(_USERS["requester"]):
            submit_request(capability=_CAPS["alpha"], reason="First request")
            with self.assertRaises(frappe.exceptions.ValidationError):
                submit_request(capability=_CAPS["alpha"], reason="Duplicate request")

    def test_submit_with_priority(self):
        self._clean_requests()
        from caps.api_requests import submit_request

        with _as_user(_USERS["requester"]):
            result = submit_request(
                capability=_CAPS["beta"],
                reason="Urgent",
                priority="High",
            )

        doc = frappe.get_doc("Capability Request", result["request"])
        self.assertEqual(doc.priority, "High")


class TestApproveRequest(unittest.TestCase):
    """Tests for caps.api_requests.approve_request — includes auto-grant."""

    @classmethod
    def setUpClass(cls):
        _setup_request_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_request_data()

    def _submit_and_return(self, cap_key="alpha"):
        # Clean previous requests for this cap
        for req in frappe.get_all(
            "Capability Request",
            filters={"capability": _CAPS[cap_key], "user": _USERS["requester"]},
            pluck="name",
        ):
            frappe.delete_doc("Capability Request", req, force=True, ignore_permissions=True)

        # Clean any existing user capability
        if frappe.db.exists("User Capability", _USERS["requester"]):
            frappe.delete_doc("User Capability", _USERS["requester"],
                              force=True, ignore_permissions=True)
        frappe.cache.delete_value(f"caps:user:{_USERS['requester']}")

        from caps.api_requests import submit_request
        with _as_user(_USERS["requester"]):
            result = submit_request(
                capability=_CAPS[cap_key],
                reason="Need it",
            )
        return result["request"]

    def test_approve_grants_capability(self):
        req_name = self._submit_and_return()
        from caps.api_requests import approve_request

        with _as_user(_USERS["approver"]):
            result = approve_request(
                request_name=req_name,
                resolution_note="Approved for project",
            )

        self.assertEqual(result["status"], "approved")

        # Verify capability was granted
        doc = frappe.get_doc("User Capability", _USERS["requester"])
        cap_names = [r.capability for r in doc.direct_capabilities]
        self.assertIn(_CAPS["alpha"], cap_names)

        # Verify request status
        req = frappe.get_doc("Capability Request", req_name)
        self.assertEqual(req.status, "Approved")
        self.assertEqual(req.approver, _USERS["approver"])

    def test_approve_non_pending_fails(self):
        req_name = self._submit_and_return("beta")
        from caps.api_requests import approve_request, reject_request

        with _as_user(_USERS["approver"]):
            reject_request(request_name=req_name)
            with self.assertRaises(frappe.exceptions.ValidationError):
                approve_request(request_name=req_name)


class TestRejectRequest(unittest.TestCase):
    """Tests for caps.api_requests.reject_request."""

    @classmethod
    def setUpClass(cls):
        _setup_request_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_request_data()

    def test_reject_request(self):
        # Clean
        for req in frappe.get_all(
            "Capability Request",
            filters={"capability": _CAPS["alpha"], "user": _USERS["requester"]},
            pluck="name",
        ):
            frappe.delete_doc("Capability Request", req, force=True, ignore_permissions=True)

        from caps.api_requests import submit_request, reject_request

        with _as_user(_USERS["requester"]):
            result = submit_request(capability=_CAPS["alpha"], reason="Need it")

        with _as_user(_USERS["approver"]):
            reject_result = reject_request(
                request_name=result["request"],
                resolution_note="Not justified",
            )

        self.assertEqual(reject_result["status"], "rejected")
        req = frappe.get_doc("Capability Request", result["request"])
        self.assertEqual(req.status, "Rejected")
        self.assertEqual(req.resolution_note, "Not justified")


class TestCancelRequest(unittest.TestCase):
    """Tests for caps.api_requests.cancel_request."""

    @classmethod
    def setUpClass(cls):
        _setup_request_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_request_data()

    def test_requester_can_cancel(self):
        # Clean
        for req in frappe.get_all(
            "Capability Request",
            filters={"capability": _CAPS["alpha"], "user": _USERS["requester"]},
            pluck="name",
        ):
            frappe.delete_doc("Capability Request", req, force=True, ignore_permissions=True)

        from caps.api_requests import submit_request, cancel_request

        with _as_user(_USERS["requester"]):
            result = submit_request(capability=_CAPS["alpha"], reason="Changed mind")
            cancel_result = cancel_request(request_name=result["request"])

        self.assertEqual(cancel_result["status"], "cancelled")
        req = frappe.get_doc("Capability Request", result["request"])
        self.assertEqual(req.status, "Cancelled")

    def test_cancel_non_pending_fails(self):
        # Clean
        for req in frappe.get_all(
            "Capability Request",
            filters={"capability": _CAPS["beta"], "user": _USERS["requester"]},
            pluck="name",
        ):
            frappe.delete_doc("Capability Request", req, force=True, ignore_permissions=True)
        if frappe.db.exists("User Capability", _USERS["requester"]):
            frappe.delete_doc("User Capability", _USERS["requester"],
                              force=True, ignore_permissions=True)
        frappe.cache.delete_value(f"caps:user:{_USERS['requester']}")

        from caps.api_requests import submit_request, approve_request, cancel_request

        with _as_user(_USERS["requester"]):
            result = submit_request(capability=_CAPS["beta"], reason="Want it")

        with _as_user(_USERS["approver"]):
            approve_request(request_name=result["request"])

        with _as_user(_USERS["requester"]):
            with self.assertRaises(frappe.exceptions.ValidationError):
                cancel_request(request_name=result["request"])


class TestGetMyRequests(unittest.TestCase):
    """Tests for caps.api_requests.get_my_requests."""

    @classmethod
    def setUpClass(cls):
        _setup_request_data()
        # Submit a request
        from caps.api_requests import submit_request
        frappe.set_user(_USERS["requester"])
        submit_request(capability=_CAPS["alpha"], reason="My request")
        frappe.set_user("Administrator")

    @classmethod
    def tearDownClass(cls):
        _teardown_request_data()

    def test_returns_own_requests(self):
        from caps.api_requests import get_my_requests
        with _as_user(_USERS["requester"]):
            result = get_my_requests()

        self.assertTrue(len(result) >= 1)
        caps = [r["capability"] for r in result]
        self.assertIn(_CAPS["alpha"], caps)

    def test_filter_by_status(self):
        from caps.api_requests import get_my_requests
        with _as_user(_USERS["requester"]):
            result = get_my_requests(status="Pending")

        self.assertTrue(len(result) >= 1)
        for r in result:
            self.assertEqual(r["status"], "Pending")


class TestGetPendingRequests(unittest.TestCase):
    """Tests for caps.api_requests.get_pending_requests."""

    @classmethod
    def setUpClass(cls):
        _setup_request_data()
        from caps.api_requests import submit_request
        frappe.set_user(_USERS["requester"])
        submit_request(capability=_CAPS["beta"], reason="Pending test")
        frappe.set_user("Administrator")

    @classmethod
    def tearDownClass(cls):
        _teardown_request_data()

    def test_returns_pending(self):
        from caps.api_requests import get_pending_requests
        with _as_user(_USERS["approver"]):
            result = get_pending_requests()

        self.assertTrue(len(result) >= 1)
        caps = [r["capability"] for r in result]
        self.assertIn(_CAPS["beta"], caps)
