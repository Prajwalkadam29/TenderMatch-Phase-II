# TenderMatch API Documentation (v4.0)

## Table of Contents
1. [Overview](#1-overview)
2. [Authentication & RBAC](#2-authentication--rbac)
3. [Users & Organizations](#3-users--organizations)
4. [Vendor Profiles (Phase II)](#4-vendor-profiles)
5. [Documents & Uploads](#5-documents--uploads)
6. [Matching Engine](#6-matching-engine)
7. [Dashboard & Activity](#7-dashboard--activity)
8. [Notifications](#8-notifications)
9. [Health & Monitoring](#9-health--monitoring)

---

## 1. Overview

**Base URL:** `http://localhost:8000`
**Spec:** OpenAPI 3.0 (Swagger)
**Authentication:** JWT Bearer Token + HTTPOnly Refresh Cookie.

---

## 2. Authentication & RBAC

### Register User (`POST /auth/register`)
Create a new account.
- **Roles:** `USER`, `ADMIN1` (creates organization).
- **Body:**
```json
{
  "name": "Prajwal",
  "email": "prajwal@example.com",
  "password": "Password123!",
  "role": "ADMIN1",
  "org_name": "TenderCorp"
}
```

### Login (`POST /auth/login`)
Authenticate and receive a JWT.
- **Returns:** `{ "access_token": "...", "user": { ... } }`
- **Side Effect:** Sets `refresh_token` HTTPOnly cookie.

### Logout (`POST /auth/logout`)
Blacklists the active JWT and clears the refresh cookie.

### Get My Profile (`GET /auth/me`)
Returns the authenticated user's profile and organizational context.

---

## 3. Users & Organizations

### List Organization Users (`GET /users/`)
- **Auth Required:** Yes (Role: `ADMIN1`)
- **Returns:** Array of user objects within the organization.

### Invite Sub-User (`POST /users/`)
- **Auth Required:** Yes (Role: `ADMIN1`)
- **Body:** `{"name": "...", "email": "...", "password": "...", "role": "USER"}`

---

## 4. Vendor Profiles (Phase II)

### Create Vendor Profile (`POST /vendor-profiles/`)
Submit a complete 3-phase vendor profile.
- **Auth Required:** Yes
- **Body Structure:**
```json
{
  "identity": { "company_legal_name": "...", "cin_llpin": "...", "msme_category": "..." },
  "geography": { "headquarters_address": "...", "operation_regions": ["Global"] },
  "business_domain": { "primary_domains": [], "capability_description_freetext": "..." },
  "financials": { "turnover_by_year": { "2023": 1000000 }, "profitable_last_3_years": true },
  "certifications": { "iso_certifications": [], "mnre_empanelment": false },
  "compliance": { "gst_returns_compliant": true, "active_litigation": false },
  "notification_preferences": { "email": "...", "minimum_match_score_threshold": 0.65 }
}
```

### List My Profiles (`GET /vendor-profiles/`)
- **Returns:** Profiles with calculated `profile_completeness_pct` and section breakdown.

### Soft Delete Profile (`DELETE /vendor-profiles/{id}`)
Sets `is_active = false`. Data is preserved for audit trails.

---

## 5. Documents & Uploads

### Upload Tender (`POST /upload/tender`)
Upload a PDF tender. Triggers background Celery task for:
1. Text extraction.
2. Structured requirement parsing via Groq.
3. 384D Vector generation and PostgreSQL indexing.

### Upload Vendor Capability (`POST /upload/vendor`)
Extracts structured capability metadata from a vendor's technical dossier.

### Get Document Status (`GET /upload/documents/{doc_id}`)
- **Returns:** `{"status": "processing" | "completed" | "failed", "metadata": { ... }}`

---

## 6. Matching Engine

### Semantic Matching (`GET /match/{vendor_id}`)
Executes high-speed cosine similarity search in `pgvector`.
- **Params:** `k` (limit, default 10), `explain` (boolean).
- **Explanation:** If `explain=true`, the Groq LLM generates a natural language justification for the match.

### Batch Structured Matching (`POST /match/structured/run/{vendor_id}`)
Hard-filter matching against the entire tender database.
- **Criteria:** Industry alignment, turnover requirements, and geographic eligibility.

---

## 7. Dashboard & Activity

### Dashboard Summary (`GET /activity/summary`)
The primary endpoint for the frontend dashboard.
- **Data Points:** Total Tenders, Total Docs, Profile Count, Overall Completeness Score.

### Activity Feed (`GET /activity/organization`)
- **Auth Required:** `ADMIN1`
- **Data:** Chronological audit log of organization events (Logins, Uploads, Edits).

---

## 8. Notifications

### Test Match Alert (`POST /notify/test-email`)
Triggers an immediate match notification email via Celery and SMTP.

---

## 9. Health & Monitoring

### Deep Health Check (`GET /health`)
Verifies readiness of all microservices:
- **MongoDB**: Connection and write latency.
- **PostgreSQL**: Connection and migration status.
- **Redis**: Latency and task queue status.

---

**API Documentation Version 4.0.0** · *Production Grade Documentation*
