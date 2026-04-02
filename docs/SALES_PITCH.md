# 🛡️ CAPS — Sales & Client Presentation

---

## The Problem

> **"Everyone sees everything. Or no one sees anything."**

Traditional ERP systems give you two options:
1. **Full access** — All users see all fields, all buttons, all data
2. **No access** — Users can't even open the form

There's nothing in between. No way to say "Sales agents can see the customer name but not the phone number" or "Junior staff can view but not approve discounts."

### Real-World Pain Points

| Scenario | Traditional Approach | CAPS Approach |
|----------|---------------------|---------------|
| Call center agent shouldn't see customer's full phone | 🔴 Can't do it without code | ✅ Phone shows as `●●●●●1234` |
| Only senior managers can approve discounts > 20% | 🔴 Custom development needed | ✅ Button hidden for non-managers |
| Temporary access during Ramadan/holiday season | 🔴 Manual role changes, often forgotten | ✅ Auto-applying/expiring policy |
| New hire needs same access as colleague | 🔴 IT ticket, manual setup | ✅ One-click "clone capabilities" |
| Audit: who changed what access, when? | 🔴 No record exists | ✅ Full audit trail, 16 event types |

---

## The Solution: CAPS

**CAPS** (Capability-Based Access Control System) gives you **surgical precision** over who sees what and who can do what — without writing a single line of code.

### How It Works (30-Second Explanation)

1. **Define capabilities** — "Can see phone number", "Can approve discounts"
2. **Map to fields/buttons** — Phone field on Lead → requires "Can see phone"
3. **Assign to users** — By role, by team, by individual, or by policy
4. **Done!** — The system enforces automatically everywhere

---

## ⭐ Key Features

### 1. Field-Level Security 🔒

Control **individual fields** on any form:

| What You Can Do | Example |
|-----------------|---------|
| **Hide** a field | Tax ID hidden from non-accounting staff |
| **Mask** a field | Phone shows as `●●●●●1234` |
| **Make read-only** | Email visible but not editable by agents |

**Zero code. Zero developer time. Just configure in the UI.**

### 2. Action-Level Security ⚡

Control **buttons and actions** on any form:

- Hide the "Delete" button from non-admins
- Disable "Approve Discount" for junior agents
- Hide workflow transition buttons based on capabilities

### 3. Smart Assignment 🧩

Multiple ways to assign capabilities:

| Method | Use Case |
|--------|----------|
| **By Role** | "All Sales Managers get these capabilities" |
| **By Group** | "MENA Sales Team gets regional access" |
| **By Bundle** | "Agent Bundle = 15 capabilities, Manager Bundle = 30" |
| **Direct** | "This specific user gets this specific capability" |
| **By Policy** | "During Ramadan, all agents get extended access" |

### 4. Capability Hierarchy 🏗️

Parent capabilities automatically grant children:

```
CRM Full Access
├── CRM Read Access (auto-granted)
├── CRM Write Access (auto-granted)
└── CRM Admin Access
    ├── Manage Users (auto-granted)
    └── Manage Settings (auto-granted)
```

### 5. Self-Service Requests 📋

Users can request capabilities themselves:

1. User submits request with reason
2. Manager receives notification
3. One-click approve → capability instantly granted
4. Full audit trail

### 6. Time-Bound Policies ⏰

Automate access changes:

- "Give all agents 'Holiday Discount' capability from Dec 1-31"
- "Remove 'VIP Access' after probation period ends"
- Policies apply and expire **automatically**

### 7. Complete Audit Trail 📊

Every action is logged:

- Who checked what capability, when
- Who granted/revoked access, and why
- Who approved/rejected requests
- Who delegated capabilities to whom
- Full IP address and timestamp tracking

### 8. Admin Dashboard 📈

One-page overview of your entire access control:

- Total capabilities, users, groups
- Pending requests
- Active policies
- Expiring capabilities
- Audit activity timeline

---

## 💼 Business Benefits

### For Management

| Benefit | Impact |
|---------|--------|
| **Compliance** | Full audit trail for regulatory requirements |
| **Data Protection** | Sensitive fields masked/hidden by default |
| **Operational Control** | Granular access without development cost |
| **Risk Reduction** | Junior staff can't accidentally approve/delete |

### For IT/Admin

| Benefit | Impact |
|---------|--------|
| **Zero-Code** | No developer needed for access changes |
| **Self-Service** | Users request access, admins approve with one click |
| **Import/Export** | Backup and restore configurations easily |
| **Debug Tools** | "View As" mode to see what any user sees |

### For Users

| Benefit | Impact |
|---------|--------|
| **Clean Interface** | Only see fields/buttons relevant to your role |
| **Self-Service** | Request capabilities without IT tickets |
| **Transparency** | Know exactly what you can and can't do |

---

## 📊 By the Numbers

| Metric | Value |
|--------|-------|
| **DocTypes** | 22 (complete data model) |
| **API Endpoints** | 54+ (full REST coverage) |
| **Automated Tests** | 286 (comprehensive coverage) |
| **Setup Time** | < 1 hour for basic configuration |
| **Code Required** | Zero for standard use cases |
| **Audit Event Types** | 16 (full compliance tracking) |

---

## 🔗 Works With Everything

CAPS is **domain-agnostic** — it works with ANY Frappe/ERPNext module:

- ✅ CRM (Leads, Customers, Opportunities)
- ✅ Sales (Sales Orders, Quotations, Invoices)
- ✅ HR (Employee records, Salary, Leave)
- ✅ Manufacturing (BOM, Work Orders)
- ✅ Accounting (Journal Entries, Reports)
- ✅ Any custom Frappe application

### Already Integrated With

- **AuraCRM** — 80+ capabilities, 5 role-based bundles, field & action restrictions for all CRM DocTypes

---

## 🚀 Getting Started

1. **Install CAPS** (5 minutes)
2. **Configure settings** (5 minutes)
3. **Define your first capability** (2 minutes)
4. **Map it to a field** (1 minute)
5. **See it work** — the field is hidden/masked for users without the capability

**Total time to first result: ~15 minutes**

---

## 🏢 Ideal For

- **Financial institutions** requiring data segregation
- **Healthcare** organizations with HIPAA/privacy requirements
- **Government** agencies with clearance-level access
- **Multi-team enterprises** with role-based field visibility
- **Any organization** that needs "who can see what" beyond basic roles

---

## Demo Scenarios

### Scenario 1: Phone Number Masking
> "Watch as Agent Ahmed sees `●●●●●1234` while Manager Sara sees the full number — on the exact same Lead form."

### Scenario 2: Button Restriction
> "The 'Approve Discount' button is invisible for junior agents. Only senior managers can see and click it."

### Scenario 3: Self-Service Request
> "Ahmed requests 'View Full Phone' capability. His manager approves with one click. Ahmed immediately sees the full number."

### Scenario 4: Holiday Policy
> "We create a policy: 'All agents get Holiday Discount capability from Dec 1-31.' It applies and expires automatically."

### Scenario 5: Impersonation Debug
> "Admin clicks 'View As Ahmed' — instantly sees exactly what Ahmed sees. Orange banner at top. Click 'Stop' to return."
