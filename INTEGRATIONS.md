# 🔗 CAPS — Integrations Guide

> **Domain:** Capability-Based Access Control
> **Prefix:** CAPS

---

## Integration Map

```
CAPS
  ├── All Arkan Lab Apps
  ├── Frappe Core Permissions
```

---

## All Arkan Lab Apps

### Connection Type
- **Direction:** Bidirectional
- **Protocol:** Python API / REST
- **Authentication:** Frappe session / API key

### Data Flow
| Source | Target | Trigger | Data |
|--------|--------|---------|------|
| CAPS | All Arkan Lab Apps | On submit | Document data |
| All Arkan Lab Apps | CAPS | On change | Updated data |

### Configuration
```python
# In CAPS Settings or site_config.json
# all_arkan_lab_apps_enabled = 1
```

---

## Frappe Core Permissions

### Connection Type
- **Direction:** Bidirectional
- **Protocol:** Python API / REST
- **Authentication:** Frappe session / API key

### Data Flow
| Source | Target | Trigger | Data |
|--------|--------|---------|------|
| CAPS | Frappe Core Permissions | On submit | Document data |
| Frappe Core Permissions | CAPS | On change | Updated data |

### Configuration
```python
# In CAPS Settings or site_config.json
# frappe_core_permissions_enabled = 1
```

---

## API Endpoints

All integration APIs use the standard response format from `caps.api.response`:

```python
from caps.api.response import success, error

@frappe.whitelist()
def sync_data():
    return success(data={}, message="Sync completed")
```

---

*Part of CAPS by Arkan Lab*
