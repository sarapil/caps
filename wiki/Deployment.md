# Deployment Guide — دليل النشر

## Frappe Cloud Deployment — النشر على Frappe Cloud

### 1. Prepare for Marketplace — التحضير للسوق

Ensure all [Marketplace requirements](https://docs.frappe.io/cloud/marketplace/marketplace-guidelines) are met:

- [ ] CI/CD workflows passing
- [ ] Semgrep scan clean
- [ ] `pyproject.toml` has `[tool.bench.frappe-dependencies]`
- [ ] Logo ≥200×200px PNG, square
- [ ] 5+ screenshots
- [ ] Short description 40-80 chars

### 2. Release Process — عملية الإصدار

```bash
# 1. Ensure all tests pass
bench --site dev.localhost run-tests --app caps

# 2. Update version in __init__.py
# 3. Update CHANGELOG.md  
# 4. Create release tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# The GitHub Actions release workflow will handle the rest
```

### 3. Self-Hosted Deployment — النشر الذاتي

```bash
# On production server
bench get-app caps https://github.com/sarapil/caps.git --branch main
bench --site production-site install-app caps
bench --site production-site migrate
bench build --app caps
sudo supervisorctl restart all
```

## Environment Variables — متغيرات البيئة

| Variable | Description | Required |
|----------|-------------|----------|
| `DB_HOST` | Database host | Yes |
| `REDIS_CACHE` | Redis cache URL | Yes |
| `REDIS_QUEUE` | Redis queue URL | Yes |

## Backup & Recovery — النسخ الاحتياطي والاسترداد

```bash
# Backup
bench --site production-site backup --with-files

# Restore
bench --site production-site restore <backup-file>
```

## Monitoring — المراقبة

- Check `logs/` for application logs
- Use `bench doctor` to diagnose issues
- Monitor Redis with `redis-cli info`
