# Permissions & CAPS — الصلاحيات ونظام القدرات

## Overview — نظرة عامة

CAPS uses the **CAPS** (Capability-Based Access Control) system for fine-grained permissions.

## Capability Categories — فئات القدرات

### Module Capabilities — قدرات الوحدات
Access to features and modules.

| Capability | Description (EN) | الوصف (AR) |
|-----------|-------------------|------------|
<!-- | `CAPS__manage_xxx` | Access xxx management | الوصول لإدارة xxx | -->

### Action Capabilities — قدرات الإجراءات
Permission for specific operations.

| Capability | Description (EN) | الوصف (AR) |
|-----------|-------------------|------------|
<!-- | `CAPS__approve_xxx` | Approve xxx | الموافقة على xxx | -->

### Field Capabilities — قدرات الحقول
Field-level masking/hiding.

| Capability | DocType | Field | Behavior |
|-----------|---------|-------|----------|
<!-- | `CAPS__view_cost` | `CAPS_ Project` | `total_cost` | mask | -->

### Report Capabilities — قدرات التقارير
Access to specific reports.

| Capability | Report | الوصف (AR) |
|-----------|--------|------------|
<!-- | `CAPS__export_reports` | All reports | تصدير التقارير | -->

## Roles — الأدوار

| Role | Capabilities | Description |
|------|-------------|-------------|
<!-- | `CAPS_ User` | Basic read access | المستخدم الأساسي | -->

## Jobs/Positions — الوظائف

| Job | Roles Included | Description |
|-----|---------------|-------------|
<!-- | `CAPS_ Manager` | User + Admin roles | المدير | -->

## Checking Permissions in Code — فحص الصلاحيات في الكود

```python
from caps.caps.gate import check_user_capability

# Check capability (throws on failure)
check_user_capability("CAPS__manage_records", throw=True)

# Check capability (returns bool)
if check_user_capability("CAPS__approve_records", throw=False):
    approve_record(doc)
```

## Auto-Enforcement — التنفيذ التلقائي

CAPS automatically enforces permissions via `doc_events`:
- `on_load` → Filters/masks fields
- `before_save` → Validates write permissions
- `on_session_creation` → Injects capabilities into session
