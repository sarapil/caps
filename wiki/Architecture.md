# Architecture — هندسة النظام

## Overview — نظرة عامة

CAPS follows the Arkan Lab architecture standards built on Frappe v16.

## Module Structure — هيكل الوحدات

```
caps/
├── caps/
│   ├── hooks.py              # App configuration
│   ├── install.py            # After install hook
│   ├── seed.py               # Reference data seeding
│   ├── api/v1/               # Versioned API endpoints
│   ├── services/             # Business logic layer
│   ├── caps/gate.py          # CAPS permission checks
│   ├── overrides/            # DocType extensions
│   ├── <module>/doctype/     # DocType definitions
│   ├── help/                 # File-based help
│   ├── translations/         # i18n files
│   └── public/               # Frontend assets
```

## Design Patterns — أنماط التصميم

### Thin Controller Pattern — نمط المتحكم الخفيف

All business logic lives in `services/`, NOT in DocType controllers:

```python
class MyDocType(Document):
    def validate(self):
        from caps.services.my_service import MyService
        MyService.validate(self)
```

### CAPS Integration — تكامل CAPS

Permission checks use the CAPS capability system:

```python
from caps.caps.gate import check_user_capability
check_user_capability("CAPS__manage_records", throw=True)
```

### API Response Format — تنسيق استجابة API

```python
from caps.api.response import success, error, paginated

@frappe.whitelist()
def get_data(page=1, page_size=20):
    frappe.has_permission("My DocType", "read", throw=True)
    return paginated(data, total, int(page), int(page_size))
```

## Dependencies — التبعيات

```
frappe (v16+)
├── frappe_visual    # UI components
├── arkan_help       # Help system
├── caps             # Permission engine
└── ... (app-specific)
```

## Database — قاعدة البيانات

- MariaDB 11.8+ with CTEs & Window Functions
- All queries use parameterized SQL
- No `frappe.db.commit()` in document events

## Security — الأمان

- All APIs have permission checks
- No raw SQL (parameterized only)
- No `eval()`/`exec()`
- No hardcoded credentials
- External APIs use timeout=30
