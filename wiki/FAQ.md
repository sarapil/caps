# FAQ — الأسئلة الشائعة

## Installation — التثبيت

### Q: What are the minimum requirements? — ما المتطلبات الدنيا؟

**A:** Python 3.12+, Node.js 20+, MariaDB 11.8+, Redis, Frappe v16+

### Q: How do I install in Codespaces? — كيف أثبت في Codespaces؟

```bash
bench get-app caps
bench --site dev.localhost install-app caps
bench --site dev.localhost migrate
bench build --app caps
```

### Q: Port 8000 is not working? — المنفذ 8000 لا يعمل؟

**A:** Arkan Lab uses port **8001**, not 8000. Navigate to `http://dev.localhost:8001/desk`

---

## Usage — الاستخدام

### Q: Where are the settings? — أين الإعدادات؟

**A:** Search for "CAPS Settings" in the Awesome Bar (Ctrl+K)

### Q: How do I reset my configuration? — كيف أعيد ضبط الإعدادات؟

```bash
bench --site dev.localhost clear-cache
bench --site dev.localhost migrate
```

---

## Development — التطوير

### Q: How do I run tests? — كيف أشغل الاختبارات؟

```bash
bench --site dev.localhost run-tests --app caps
```

### Q: How do I contribute? — كيف أساهم؟

1. Fork the repo
2. Create a feature branch from `develop`
3. Make changes following [Arkan Lab Standards](Architecture)
4. Submit a PR using the PR template

### Q: JS changes not showing? — تغييرات JS لا تظهر؟

```bash
bench --site dev.localhost clear-cache
bench build --app caps
```

---

## Troubleshooting — استكشاف الأخطاء

### Q: "Unknown column" error — خطأ "عمود غير معروف"

**A:** Run migration: `bench --site dev.localhost migrate`

### Q: Permission denied on API — رفض الصلاحية في API

**A:** Ensure the API has `@frappe.whitelist()` decorator and proper permission checks.

### Q: Database connection refused — رفض اتصال قاعدة البيانات

**A:** In Codespaces, use `--no-mariadb-socket --db-host mariadb`

---

## Need More Help? — تحتاج مساعدة إضافية؟

- 📖 [Full Documentation](Home)
- 🐛 [Report Bug](https://github.com/sarapil/caps/issues/new?template=bug_report.yml)
- 💬 [Discussions](https://github.com/orgs/sarapil/discussions)
