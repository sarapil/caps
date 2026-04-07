## الوصف | Description
<!-- وصف مختصر للتغييرات — Brief description of changes -->


## نوع التغيير | Type of Change
- [ ] 🐛 Bug fix — إصلاح خطأ
- [ ] ✨ New feature — ميزة جديدة
- [ ] 💥 Breaking change — تغيير كسري
- [ ] 📝 Documentation — توثيق
- [ ] 🧪 Tests — اختبارات
- [ ] 🔧 Refactoring — إعادة هيكلة
- [ ] 🎨 UI/UX — واجهة المستخدم
- [ ] ⚡ Performance — أداء
- [ ] 🔒 Security — أمان
- [ ] 🌐 Translation / i18n — ترجمة

## المشكلات المرتبطة | Related Issues
<!-- Fixes #123, Relates to #456 -->

## التغييرات الرئيسية | Key Changes
<!-- قائمة بالتغييرات الرئيسية — List the key changes -->
-
-

## لقطات الشاشة | Screenshots
<!-- إذا كان التغيير مرئياً — If the change is visual -->

## خطة الاختبار | Test Plan
<!-- كيف تم اختبار هذا التغيير — How was this change tested? -->
- [ ] Unit tests pass — اختبارات الوحدة ناجحة
- [ ] Integration tests pass — اختبارات التكامل ناجحة
- [ ] Manual testing done — الاختبار اليدوي تم

## قائمة التحقق | Checklist

### الكود | Code
- [ ] Follows [Arkan Lab Standards](/.github/copilot-instructions.md) — يتبع معايير أركان لاب
- [ ] Self-reviewed the code — راجعت الكود ذاتياً
- [ ] No `frappe.db.commit()` inside document events — لا `commit` داخل أحداث المستندات
- [ ] No raw SQL without parameterization — لا SQL خام بدون معاملات
- [ ] All `@frappe.whitelist()` APIs have permission checks — كل APIs لديها فحص صلاحيات
- [ ] No hardcoded credentials — لا بيانات اعتماد مضمنة
- [ ] Uses `extend_doctype_class` NOT `override_doctype_class` — يستخدم extend وليس override
- [ ] Thin Controller pattern (logic in services/) — نمط المتحكم الخفيف

### الاختبارات | Tests
- [ ] Tests added/updated for changes — اختبارات مضافة/محدثة
- [ ] All existing tests pass — كل الاختبارات الموجودة تمرّ

### التوثيق والترجمة | Docs & Translation
- [ ] New user-facing strings wrapped in `__()` — النصوص الجديدة ملفوفة في `__()`
- [ ] Arabic translation added for new strings — ترجمة عربية مضافة
- [ ] Help files updated (if DocType changed) — ملفات المساعدة محدّثة
- [ ] CHANGELOG updated — سجل التغييرات محدّث

### الأمان | Security
- [ ] No SQL injection vectors — لا ثغرات حقن SQL
- [ ] No XSS vectors — لا ثغرات XSS
- [ ] External API calls use timeout — استدعاءات API خارجية تستخدم timeout
- [ ] Sensitive data not logged — البيانات الحساسة لا تُسجّل

### Visual (if UI changes) — المرئيات
- [ ] Uses `frappe.visual` components — يستخدم مكونات frappe_visual
- [ ] CSS Logical Properties (RTL support) — خصائص CSS المنطقية
- [ ] Icons via `frappe.visual.icons` — الأيقونات عبر frappe.visual.icons
- [ ] Responsive (320px to 4K) — متجاوب
- [ ] Dark mode compatible — متوافق مع الوضع الداكن
