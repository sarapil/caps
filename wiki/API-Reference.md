# API Reference — مرجع الواجهة البرمجية

## Overview — نظرة عامة

All CAPS APIs follow the Arkan Lab API standards.

## Base URL — الرابط الأساسي

```
POST /api/method/caps.api.v1.<module>.<function>
```

## Response Format — تنسيق الاستجابة

### Success — نجاح
```json
{
  "status": "success",
  "data": { ... },
  "message": "Operation completed"
}
```

### Error — خطأ
```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid input"
}
```

### Paginated — مُرقّم
```json
{
  "status": "success",
  "data": [ ... ],
  "meta": {
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  }
}
```

## Authentication — المصادقة

All API calls require authentication via:
- Session cookie (from login)
- API key + secret in Authorization header
- OAuth 2.0 Bearer token

## Endpoints — نقاط النهاية

<!-- Document each API endpoint here -->

### Example: List Records

```bash
curl -X POST 'https://site.example.com/api/method/caps.api.v1.records.get_list' \
  -H 'Authorization: token api_key:api_secret' \
  -H 'Content-Type: application/json' \
  -d '{"page": 1, "page_size": 20}'
```

## Rate Limiting — تحديد المعدل

- Standard APIs: 100 requests/minute
- Heavy APIs: 10 requests/minute
- Guest APIs: 5 requests/minute

## Error Codes — رموز الخطأ

| Code | HTTP | Description (EN) | الوصف (AR) |
|------|------|-------------------|------------|
| `VALIDATION_ERROR` | 400 | Invalid input | مدخل غير صالح |
| `PERMISSION_DENIED` | 403 | Insufficient permissions | صلاحيات غير كافية |
| `NOT_FOUND` | 404 | Resource not found | المورد غير موجود |
| `RATE_LIMITED` | 429 | Too many requests | طلبات كثيرة جداً |
| `INTERNAL_ERROR` | 500 | Server error | خطأ في الخادم |
