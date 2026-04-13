# Usage Scenarios — سيناريوهات الاستخدام

This directory contains per-role usage scenarios for **CAPS** (Capability-Based Access Control System).

Each scenario file documents:
- Daily / Weekly / Monthly workflows
- Pre-conditions and expected outcomes  
- Screen references (links to `../screens/`)
- Device breakpoint compatibility
- Error scenarios and edge cases

## Files

| File | Role | Description |
|------|------|-------------|
| [admin.md](admin.md) | System Administrator | Setup, configuration, capability management |
| [manager.md](manager.md) | CAPS Manager | User assignments, request approvals, group management |
| [user.md](user.md) | Regular User | View capabilities, submit requests, delegation |
| [cross-role.md](cross-role.md) | Multi-role | Workflows involving multiple participants |

## Roles Overview — نظرة عامة على الأدوار

| Role | Arabic | Primary Actions |
|------|--------|-----------------|
| **System Administrator** | مدير النظام | Full system configuration, capability definitions |
| **CAPS Manager** | مدير CAPS | Approve requests, manage groups, assign bundles |
| **Regular User** | مستخدم عادي | View own capabilities, submit requests, delegate |
| **Auditor** | مدقق | View reports, compliance snapshots, audit logs |

## How to Use

1. Identify which role you are developing for
2. Read the role's scenario file
3. Ensure all scenarios map to screen designs in `../screens/`
4. Write tests that cover each scenario
5. Update help content in `caps/help/` to match workflows

## Scenario ID Convention

- `DS-###` = Daily Scenario
- `WS-###` = Weekly Scenario
- `MS-###` = Monthly Scenario
- `ES-###` = Exception Scenario
- `CR-###` = Cross-Role Scenario

## Updating Scenarios

When adding new features to CAPS:
1. Create scenario(s) describing the workflow
2. Link to screen spec in `../screens/`
3. Update [cross-role.md](cross-role.md) if multiple roles involved
4. Add test cases in `caps/tests/`
