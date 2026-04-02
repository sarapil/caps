# CAPS User Guide

A guide for end users on how CAPS affects your daily workflow.

---

## What is CAPS?

CAPS (Capability-Based Access Control System) controls what you can see and do within the system. Your administrator has set up specific capabilities based on your role, team, and responsibilities.

**You don't need to do anything** — CAPS works automatically in the background.

---

## How It Affects You

### Fields You Can't See

Some fields may be **hidden** or **masked** based on your capabilities:

- **Hidden fields**: The field is completely invisible on the form
- **Masked fields**: The field shows a partial value like `●●●●●1234` instead of the full phone number
- **Read-only fields**: You can see the value but can't edit it

This is normal and configured by your administrator based on your role.

### Buttons You Can't See

Some action buttons may be hidden. For example:
- A "Delete" button might be hidden for non-managers
- An "Approve" button might only show for authorized approvers

If you need access to a hidden button, [request the capability](#requesting-new-capabilities).

---

## Requesting New Capabilities

If you need access to a field or action that's restricted:

### Step 1: Submit a Request

1. Go to **Capability Request** → New (or ask your admin for the URL)
2. Fill in:
   - **Capability**: The specific capability you need (ask your admin if unsure)
   - **Reason**: Why you need this access
   - **Priority**: Low / Medium / High
3. Submit

### Step 2: Wait for Approval

Your CAPS Manager or Admin will review your request. You'll receive a notification when it's:
- ✅ **Approved** — The capability is automatically granted
- ❌ **Rejected** — You'll see the rejection reason

### Step 3: Check Status

Go to **Capability Request** list to see all your requests and their statuses.

### Cancelling a Request

If you no longer need a pending request, open it and click **Cancel**.

---

## Checking Your Capabilities

### View Your Capabilities

You can see your full capability list:
1. Open the browser console (F12 → Console)
2. Type: `frappe.boot.caps.capabilities`
3. This shows all your current capabilities

### Understanding Expiry

Some capabilities have an **expiry date**. You'll receive a notification before they expire (usually 7 days before). When a capability expires:
- The field/action becomes restricted again
- You can request a renewal from your admin

---

## Delegation (If Available)

If you're a CAPS Manager, you can **delegate** your capabilities to team members:

### Delegating a Capability

1. Go to the delegation panel in your admin tools
2. Select the capability you want to delegate
3. Select the team member
4. (Optional) Add a reason
5. Confirm

**Rules:**
- You can only delegate capabilities you currently hold
- The capability must be marked as "delegatable" by the admin
- Delegations can be revoked at any time

### Revoking a Delegation

Go to your delegations list and click "Revoke" on any delegation.

---

## FAQ

### Why can't I see a field that my colleague can see?

Your colleague likely has a capability that you don't. Different roles and teams have different access levels. If you need the same access, submit a Capability Request.

### Why did a field suddenly become hidden?

Possible reasons:
- Your capability expired (check notifications for expiry alerts)
- A policy change removed the capability from your role
- An admin revoked the capability

Contact your CAPS Admin for details.

### Why is a phone number showing as `●●●●●1234`?

The field is **masked** — you can see the last few digits but not the full value. This is a privacy/security measure. If you need the full value, request the appropriate capability.

### Can I give my capabilities to a colleague temporarily?

Only CAPS Managers can delegate capabilities. Ask your manager to delegate the capability to your colleague.

### How long does it take for new capabilities to take effect?

Usually within 5 minutes (the cache refresh time). You can force a refresh by:
1. Hard-refreshing the page (Ctrl+Shift+R)
2. Or asking your admin to "bust cache" for your user

---

## Getting Help

- **For access requests**: Submit a Capability Request
- **For technical issues**: Contact your CAPS Admin
- **For questions about what you can/can't do**: Check with your team manager
