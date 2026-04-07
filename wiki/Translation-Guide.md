# Translation Guide — دليل الترجمة

## Language Tiers — مستويات اللغات

| Tier | Languages | Priority |
|------|-----------|----------|
| **T1 — Mandatory** | Arabic (ar), English (en) | Must have |
| **T2 — High** | Turkish (tr), French (fr), Urdu (ur), Hindi (hi), Persian (fa) | Should have |
| **T3 — Marketplace** | Spanish (es), German (de), Portuguese (pt), Indonesian (id), Chinese (zh) | Nice to have |

## Adding Translations — إضافة الترجمات

### 1. Extract untranslated strings — استخراج النصوص غير المترجمة

```bash
bench --site dev.localhost get-untranslated ar --app caps
```

### 2. Translation file format — تنسيق ملف الترجمة

File: `caps/translations/ar.csv`

```csv
Source (English),Translated (Arabic),Context
"Hello","مرحباً",
"Save","حفظ",
"Customer Name","اسم العميل",DocType: Sales Order
```

### 3. Import translations — استيراد الترجمات

```bash
bench update-translations ar source.csv translated.csv
```

### 4. Verify completeness — التحقق من الاكتمال

```bash
# Should output 0 for complete translation
bench --site dev.localhost get-untranslated ar --app caps | wc -l
```

## Rules — القواعد

1. **All user-facing strings** must be wrapped in `__()` for Python or `__()` for JS
2. **Arabic is mandatory** (T1) — no release without Arabic translation
3. **RTL support** — use CSS Logical Properties (`margin-inline-start` not `margin-left`)
4. **`dir="auto"`** for user-generated content
5. **No hardcoded text** in templates — always use translation functions

## Contributing Translations — المساهمة في الترجمة

1. Fork the repository
2. Edit/create the CSV file in `caps/translations/`
3. Submit a PR with label `translation`
