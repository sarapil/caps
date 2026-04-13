# User — Usage Scenarios
# سيناريوهات المستخدم العادي

## Role Overview

- **Title**: Regular User / المستخدم العادي
- **CAPS Capabilities**: View own capabilities, Request capabilities
- **Primary DocTypes**: Capability Request (own), User Capability (view own)
- **Device**: Desktop / Tablet / Mobile

## Daily Scenarios (يومي)

### DS-001: View My Capabilities

- **Goal**: See what capabilities I currently have
- **Pre-conditions**: User is logged in
- **Steps**:
  1. Navigate to `/desk/caps-admin` or use navbar dropdown
  2. View "My Capabilities" section
  3. See list of active capabilities with sources
  4. Check expiry dates for time-boxed access
- **Screen**: [my-capabilities](../screens/my-capabilities.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅ / Mobile ✅
- **Error scenarios**: No capabilities → info message shown

### DS-002: Understand Permission Denied

- **Goal**: Know why I can't access a feature
- **Pre-conditions**: User encountered access restriction
- **Steps**:
  1. Note the permission error message
  2. Navigate to "My Capabilities" section
  3. Search for relevant capability
  4. If missing, view "Required Capabilities" for the feature
  5. Consider submitting capability request
- **Screen**: [permission-denied-help](../screens/permission-denied-help.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅ / Mobile ✅

### DS-003: Check capability expiry

- **Goal**: Know when my temporary access expires
- **Pre-conditions**: User has time-boxed capabilities
- **Steps**:
  1. Open "My Capabilities" section
  2. Look for capabilities with "Expires On" date
  3. Note warning icons for soon-to-expire
  4. Contact manager if renewal needed
- **Screen**: [my-capabilities](../screens/my-capabilities.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅ / Mobile ✅

## Weekly Scenarios (أسبوعي)

### WS-001: Request Additional Capability

- **Goal**: Obtain capability needed for new assignment
- **Pre-conditions**: User knows which capability is needed
- **Steps**:
  1. Navigate to `Capability Request` creation
  2. Search and select required capability
  3. Provide business justification
  4. Optionally request time-boxed or permanent
  5. Submit for manager approval
- **Screen**: [capability-request-form](../screens/capability-request-form.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅ / Mobile ✅
- **Error scenarios**: Duplicate request → warning shown

### WS-002: Track My Request Status

- **Goal**: Check if my capability request was processed
- **Pre-conditions**: User has submitted request
- **Steps**:
  1. Navigate to `Capability Request` list (filtered to own)
  2. View request status (Pending/Approved/Rejected)
  3. If rejected, read resolution note
  4. If approved, verify capability now active
- **Screen**: [my-requests](../screens/my-requests.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅ / Mobile ✅

## Monthly Scenarios (شهري)

### MS-001: Review My Access Summary

- **Goal**: Periodic review of all my permissions
- **Pre-conditions**: Compliance awareness
- **Steps**:
  1. Open "My Capabilities" summary view
  2. Review all capabilities by category
  3. Identify any capabilities no longer needed
  4. Notify manager to revoke unneeded access
- **Screen**: [my-capabilities-summary](../screens/my-capabilities-summary.md)
- **Breakpoints**: Desktop ✅

## Exception Scenarios (استثنائي)

### ES-001: Delegate Capability Temporarily

- **Goal**: Allow colleague to act on my behalf during vacation
- **Pre-conditions**: Delegation enabled, user has delegatable capabilities
- **Steps**:
  1. Navigate to delegation interface
  2. Select capability to delegate
  3. Choose delegate user
  4. Set start and end dates
  5. Provide reason for delegation
  6. Submit delegation
- **Screen**: [delegation-form](../screens/delegation-form.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅
- **Error scenarios**: Capability not delegatable → error shown

### ES-002: Emergency Access Request

- **Goal**: Request urgent elevated access
- **Pre-conditions**: Business emergency, normal channels too slow
- **Steps**:
  1. Create Capability Request with "High" priority
  2. Mark as urgent in description
  3. Submit and directly contact manager
  4. Manager can use emergency approval
- **Screen**: [capability-request-form](../screens/capability-request-form.md)
- **Breakpoints**: Desktop ✅ / Tablet ✅ / Mobile ✅
