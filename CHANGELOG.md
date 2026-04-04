# Changelog — CAPS

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-04-04

### Added
- Capability-Based Access Control System for Frappe Framework
- 22 DocTypes for fine-grained permission management
- 54+ API endpoints for capability CRUD and queries
- 286 unit tests with full coverage
- Capability → Role mapping with visual interface
- Field-level restrictions (hide, mask, read-only)
- Permission Groups for bulk capability assignment
- Capability Policies with time-boxing and expiry
- Rate limiting per capability
- Policy Engine with automatic enforcement
- Permission simulator for testing access patterns
- Analytics dashboard for usage patterns
- CI/CD workflows (ci.yml, linters.yml, release.yml)
- About page (`/caps-about`) and onboarding page (`/caps-onboarding`)
- Arabic + 10 language translations (456 strings)
- File-based contextual help (`help/en/`, `help/ar/`)
- Desktop Icon fixture for workspace
