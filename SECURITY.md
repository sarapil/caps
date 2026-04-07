# Security Policy — سياسة الأمان

## Supported Versions — الإصدارات المدعومة

| Version | Supported | الحالة |
|---------|-----------|--------|
| latest (main) | ✅ Active | نشط |
| previous minor | ✅ Security fixes | إصلاحات أمنية |
| older | ❌ End of Life | نهاية الدعم |

## Reporting a Vulnerability — الإبلاغ عن ثغرة أمنية

### ⚠️ DO NOT open a public issue for security vulnerabilities — لا تفتح مشكلة عامة للثغرات الأمنية

Instead, please use one of these methods:

1. **GitHub Security Advisory** (preferred — مُفضّل):
   - Go to the [Security tab](../../security/advisories/new) of this repository
   - Click "Report a vulnerability"
   - Fill in the details

2. **Email — البريد الإلكتروني**:
   - Send to: `security@arkan.it.com`
   - Include: vulnerability description, steps to reproduce, impact assessment
   - PGP key available upon request

### What to Include — ماذا تتضمن

- **Type of vulnerability** — نوع الثغرة (e.g., SQL injection, XSS, CSRF)
- **Affected component** — المكون المتأثر (file path, API endpoint)
- **Steps to reproduce** — خطوات إعادة الإنتاج
- **Proof of concept** — إثبات المفهوم (if available)
- **Impact assessment** — تقييم التأثير
- **Suggested fix** — الإصلاح المقترح (if any)

### Response Timeline — الجدول الزمني للاستجابة

| Action | Timeline |
|--------|----------|
| Acknowledgment — الإقرار | Within 48 hours — خلال ٤٨ ساعة |
| Initial assessment — التقييم الأولي | Within 1 week — خلال أسبوع |
| Fix development — تطوير الإصلاح | Within 2 weeks — خلال أسبوعين |
| Security release — إصدار أمني | Within 30 days — خلال ٣٠ يوماً |

### Disclosure Policy — سياسة الإفصاح

- We follow **Coordinated Disclosure** — نتبع الإفصاح المنسق
- We will credit you in the security advisory (unless you prefer anonymity) — سننسب الفضل إليك
- We ask that you give us a reasonable window to fix before public disclosure — نطلب منك منحنا وقتاً معقولاً

## Security Standards — معايير الأمان

This app follows the [Arkan Lab Security Commandments](https://github.com/sarapil/frappe_docker/blob/main/.github/copilot-instructions.md):

- ✅ No `eval()`/`exec()`
- ✅ Parameterized SQL only
- ✅ Permission checks on all whitelisted APIs
- ✅ No hardcoded credentials
- ✅ No sensitive data in logs
- ✅ External API calls use timeout
- ✅ Semgrep security scanning in CI
- ✅ No `frappe.db.commit()` in document events

## Security Scanning — الفحص الأمني

Every PR and release is scanned using:
- **Semgrep** — static analysis for Python/JS vulnerabilities
- **Ruff** — Python linting including security rules
- **Custom Frappe checks** — forbidden patterns detection
