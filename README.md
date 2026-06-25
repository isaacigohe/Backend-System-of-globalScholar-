# GlobalScholar — Academic Study Abroad Management System (Backend)

## A. Contributor

* **Isaac Emmanuel Igohe**

---

## B. Overview

**GlobalScholar** is a production-grade REST API backend for managing international academic study abroad applications, built with Django and Django REST Framework, connected to a PostgreSQL database and deployed on Render.

The system supports three distinct user roles — Student, Home Administrator, and Host Coordinator — each with permissions tailored to their responsibilities within the study abroad workflow.

Students can browse universities, apply to programs, track their application pipeline, and upload compliance documents. Home Administrators review applications, advance them through a strict six-stage pipeline, and verify submitted documents. Host Coordinators manage credit transfer logs after a student completes their semester abroad.

---

## C. Requirements

The following software should be installed before running the project locally:

1. Python 3.11+
2. Django 5.2.3
3. PostgreSQL
4. Postman (for testing the API endpoints)
5. Git Bash (for running terminal commands on Windows)

---

## D. Installation

### 1. Clone the Repository

```bash
git clone https://github.com/isaacigohe/Backend-System-of-globalScholar-
cd Backend-System-of-globalScholar-
```

### 2. Create a Virtual Environment

```bash
# Windows (Git Bash)
python -m venv venv
source venv/Scripts/activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root and set the following:

```bash
SECRET_KEY=your_django_secret_key

DB_NAME=globalscholar_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

DJANGO_SETTINGS_MODULE=core_backend.settings.development
```

### 5. Create the PostgreSQL Database

```bash
psql -U postgres -c "CREATE DATABASE globalscholar_db;"
```

### 6. Run Migrations

```bash
python manage.py makemigrations users
python manage.py makemigrations universities
python manage.py makemigrations applications
python manage.py migrate
```

### 7. Create a Superuser

```bash
python manage.py createsuperuser
```

### 8. Start the Development Server

```bash
python manage.py runserver
```

---

## E. Usage

### 1. Student Registration & Login
Students register with their GPA, major, and home institution. Upon login, a JWT token is issued containing their role and identity.

### 2. Browse Universities
Students and visitors can browse the university catalog, filter by country, GPA requirement, or language — no login required.

### 3. Apply to a Program
Students apply to a specific university program. The system automatically checks their GPA against the university's minimum requirement before creating the application.

### 4. Application Pipeline
The Home Administrator advances the application through six stages — DRAFT → SUBMITTED → UNDER_REVIEW → COMPLIANCE_PHASE → APPROVED / REJECTED.

### 5. Document Compliance
When an application enters COMPLIANCE_PHASE, the system automatically generates a document checklist for the student. Students upload required files; admins review and approve or flag them with mandatory written feedback.

### 6. Credit Transfer
After a student completes their semester abroad, the Host Coordinator logs each course taken and maps it to an equivalent at the student's home institution.

---

## F. Features

### 1. Role-Based Access Control (RBAC)
Three roles with distinct permissions: Student, Home Administrator, Host Coordinator. Every endpoint is protected by role-specific permission classes.

### 2. JWT Authentication (SimpleJWT)
Secure token-based authentication with 60-minute access tokens and 7-day refresh tokens. Tokens carry the user's role, email, and full name. Refresh tokens are blacklisted on logout.

### 3. Six-Stage Application Pipeline
Applications move through a strict, enforced pipeline: DRAFT → SUBMITTED → UNDER_REVIEW → COMPLIANCE_PHASE → APPROVED → REJECTED. Illegal stage jumps are blocked by the backend.

### 4. GPA Eligibility Guardrail
When a student applies to a university, the backend checks their GPA against the university's minimum requirement using explicit if/else validation. Ineligible applications are rejected before any database write occurs.

### 5. Automatic Document Checklist Generation
A Django post_save signal fires the moment an application enters COMPLIANCE_PHASE, automatically generating all required document checklist rows for the student in a single bulk database operation.

### 6. Mandatory Comment Enforcement
Admins cannot flag a document as ACTION_REQUIRED or reject an application without providing a written explanation. This is enforced at the serializer level and returns HTTP 400 if violated.

### 7. Travel Advisory Scraper
A dedicated scraping utility (`universities/scraper.py`) uses Python `requests` and `BeautifulSoup4` to fetch travel advisory data from the US State Department and update the `travel_advisory_level` field on University records. Triggered via `python manage.py run_scraper`.

### 8. Pagination & Filtering
All list views return exactly 10 items per page. Filtering is available by country, GPA requirement, application status, and destination country using `django-filter`.

### 9. Rate Limiting (Throttling)
Login endpoint is limited to 5 requests per minute. Document upload endpoint is limited to 3 requests per minute per user using DRF ScopedRateThrottle.

### 10. Django Admin Panel
All models — Users, Universities, Programs, Applications, Document Checklist Items, Credit Transfer Logs — are fully registered and visible in the Django admin panel with search, filtering, and inline views.

---

## G. API Endpoints

**Base URL (Production):** `https://backend-system-of-globalscholar-1.onrender.com/api/v1`

### Authentication Endpoints

```http
POST   /api/v1/auth/register/
POST   /api/v1/auth/login/
POST   /api/v1/auth/logout/
POST   /api/v1/auth/token/refresh/
GET    /api/v1/users/me/
PATCH  /api/v1/users/me/
```

### University Endpoints (Public — No Auth Required)

```http
GET    /api/v1/universities/
POST   /api/v1/universities/
GET    /api/v1/universities/{id}/
PATCH  /api/v1/universities/{id}/
```

### Program Endpoints (Public — No Auth Required)

```http
GET    /api/v1/universities/{id}/programs/
POST   /api/v1/universities/{id}/programs/
GET    /api/v1/programs/{id}/
PATCH  /api/v1/programs/{id}/
```

### Application Endpoints

```http
GET    /api/v1/applications/
POST   /api/v1/applications/
GET    /api/v1/applications/{id}/
PATCH  /api/v1/applications/{id}/
POST   /api/v1/applications/{id}/submit/
POST   /api/v1/applications/{id}/advance/
```

### Document Endpoints

```http
GET    /api/v1/applications/{id}/documents/
PATCH  /api/v1/documents/{id}/upload/
PATCH  /api/v1/documents/{id}/review/
```

### Credit Transfer Endpoints

```http
GET    /api/v1/applications/{id}/credits/
POST   /api/v1/applications/{id}/credits/
GET    /api/v1/credits/{id}/
PATCH  /api/v1/credits/{id}/
```

---

## H. Application Pipeline

```
DRAFT → SUBMITTED → UNDER_REVIEW → COMPLIANCE_PHASE → APPROVED
                                                     ↘ REJECTED
```

| Stage | Triggered By | What Happens |
|---|---|---|
| DRAFT | Student creates application | GPA guardrail check runs |
| SUBMITTED | Student submits | GPA frozen on record permanently |
| UNDER_REVIEW | Admin advances | Reviewer and timestamp stamped |
| COMPLIANCE_PHASE | Admin advances | Document checklist auto-generated by signal |
| APPROVED | Admin advances | Final decision timestamped |
| REJECTED | Admin advances | Mandatory rejection reason required |

---

## I. Role Permission Matrix

| Action | Student | Home Admin | Host Coordinator |
|---|---|---|---|
| Browse Universities | ✅ | ✅ | ✅ |
| Create University | ❌ | ✅ | ✅ |
| Create Application | ✅ | ❌ | ❌ |
| Submit Application | ✅ | ❌ | ❌ |
| Advance Pipeline | ❌ | ✅ | ✅ |
| Upload Document | ✅ | ❌ | ❌ |
| Review Document | ❌ | ✅ | ✅ |
| Log Credit Transfer | ❌ | ❌ | ✅ |

---

## J. Tech Stack

| Layer | Technology |
|---|---|
| Programming Language | Python 3.11+ |
| Web Framework | Django 5.2.3 |
| API Framework | Django REST Framework 3.17.1 |
| Database | PostgreSQL |
| Authentication | SimpleJWT |
| Filtering | django-filter |
| Web Scraping | requests + BeautifulSoup4 |
| Production Server | Gunicorn |
| Static Files | WhiteNoise |
| CORS | django-cors-headers |
| Deployment | Render |

---

## K. Deployment

**Live API:** https://backend-system-of-globalscholar-1.onrender.com

**Admin Panel:** https://backend-system-of-globalscholar-1.onrender.com/admin/

**Note:** This project is hosted on Render's free tier. The server may take 30–60 seconds to respond after a period of inactivity as the instance spins back up.

To run the travel advisory scraper manually:
```bash
python manage.py run_scraper
python manage.py run_scraper --country "Germany"
python manage.py run_scraper --dry-run
```

---

## L. Project Structure

```
backend/
├── core_backend/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   └── urls.py
├── users/
│   ├── models.py
│   ├── serializers.py
│   ├── permissions.py
│   ├── throttles.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── universities/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── scraper.py
│   ├── admin.py
│   └── management/
│       └── commands/
│           └── run_scraper.py
├── applications/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── signals.py
│   ├── apps.py
│   └── admin.py
├── requirements.txt
├── build.sh
└── manage.py
```
