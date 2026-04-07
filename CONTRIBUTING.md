# Contributing to CAPS — المساهمة في CAPS

شكراً لاهتمامك بالمساهمة! — Thank you for your interest in contributing!

## 📋 Code of Conduct — قواعد السلوك

This project follows the [Arkan Lab Code of Conduct](https://github.com/sarapil/frappe_docker/blob/main/CODE_OF_CONDUCT.md).

## 🚀 Getting Started — البدء

### 1. Fork & Clone — التفريع والنسخ

```bash
git clone https://github.com/YOUR_USERNAME/caps.git
cd caps
```

### 2. Setup Development Environment — إعداد بيئة التطوير

```bash
bench get-app caps /path/to/your/fork
bench --site dev.localhost install-app caps
bench --site dev.localhost migrate
```

### 3. Create a Branch — إنشاء فرع

```bash
# For features — للميزات
git checkout -b feat/my-feature

# For bug fixes — لإصلاح الأخطاء
git checkout -b fix/bug-description

# For documentation — للتوثيق
git checkout -b docs/topic
```

## 📐 Development Standards — معايير التطوير

### Python
- **Style:** Ruff linter + formatter
- **Type hints:** Required on all functions
- **Pattern:** Thin Controller — logic in `services/`
- **SQL:** Parameterized only — NEVER f-strings
- **Tests:** Required for new features

### JavaScript
- **Style:** ESLint
- **Components:** Use `frappe.visual` components
- **Icons:** `frappe.visual.icons` — NEVER Font Awesome
- **RTL:** CSS Logical Properties

### Translations
- **Arabic is mandatory** for all user-facing strings
- Wrap strings in `__()` (Python and JS)

## 🔒 Security Rules — قواعد الأمان

- ❌ No `eval()`/`exec()`
- ❌ No `override_doctype_class`
- ❌ No `frappe.db.commit()` in document events
- ❌ No hardcoded credentials
- ✅ Permission checks on all `@frappe.whitelist()` APIs
- ✅ Parameterized SQL only

## 🧪 Testing — الاختبارات

```bash
# Run all tests — تشغيل كل الاختبارات
bench --site dev.localhost run-tests --app caps

# Run specific test — تشغيل اختبار محدد
bench --site dev.localhost run-tests --app caps --module caps.tests.unit.test_my_service
```

## 📝 Commit Convention — اتفاقية الالتزامات

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new reservation type
fix: correct date validation
docs: update API reference
perf: optimize query performance
security: fix SQL injection in API
refactor: extract service layer
test: add unit tests for booking
i18n: add Arabic translations
```

## 🔄 Pull Request Process — عملية طلب الدمج

1. **Update your branch** with latest `main`
2. **Run tests** locally
3. **Run linters:** `ruff check . && ruff format --check .`
4. **Create PR** using the [PR template](/.github/PULL_REQUEST_TEMPLATE.md)
5. **Wait for CI** — all checks must pass
6. **Request review** from code owners
7. **Address feedback** promptly

## 🏷️ Issue Labels — تصنيفات المشكلات

When creating issues, use the templates provided. Labels are auto-assigned based on content.

Key labels:
- `good first issue` — مناسب للمبتدئين
- `help wanted` — يحتاج مساعدة
- `priority: critical` — أولوية حرجة

## 📖 Documentation — التوثيق

- Update help files in `caps/help/` for DocType changes
- Both English and Arabic versions required
- Update wiki pages for architectural changes

## 💬 Questions? — أسئلة؟

- [GitHub Discussions](https://github.com/orgs/sarapil/discussions)
- [Wiki](../../wiki)
