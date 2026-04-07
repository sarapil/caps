# Threat Model

## Threat Categories

Based on OWASP Top 10:

| # | Threat | Mitigation |
|---|--------|-----------|
| 1 | Broken Access Control | CAPS capability checks on all APIs |
| 2 | Injection (SQL/XSS) | Parameterized queries, output encoding |
| 3 | Insecure Design | Thin controller + service layer pattern |
| 4 | Security Misconfiguration | Frappe framework defaults |
| 5 | SSRF | Timeout + allowlist for external APIs |
