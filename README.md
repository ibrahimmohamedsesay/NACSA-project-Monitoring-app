# NaCSA Community Project Management & Monitoring System (CPMMS)

Final-year project: *Design and Evaluation of a Digital Community Project Monitoring and Verification System for NaCSA Projects in Sierra Leone* — Limkokwing University of Creative Technology.
Authors: Issa Kamara, Khadijah Kubra Bunduka, Ibrahim Mohamed Sesay.

> **Prototype.** All seeded data is FICTIONAL demo data. The system does not replace NaCSA's own MIS.

## Stack
Django 5.2 · PostgreSQL · Django REST Framework (read-only API) · vanilla JS + Chart.js (vendored, works offline) · ReportLab / openpyxl for PDF / Excel.

## Modules
Dashboard · Projects (7-stage lifecycle, registration wizard, approval workflow) · Monitoring & M&E (progress updates with photo evidence, verification review, visits, evaluations) · Results framework · Beneficiaries · Finance & payments · GRM · Documents & evidence (restricted downloads) · Reports (12 reports, print/PDF/Excel/CSV, data-quality checks) · Notifications · Audit trail · User management.

## Setup (Windows / VS Code)
1. Install Python 3.11+ and PostgreSQL 14+. In pgAdmin or `psql` create a database: `CREATE DATABASE nacsa_db;`
2. Open the project folder in VS Code, then in a terminal:
```
python -m venv venv
venv\Scripts\activate          (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env         (then edit DB_USER / DB_PASSWORD / SECRET_KEY)
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```
3. Open http://127.0.0.1:8000/ and sign in.

## Demo accounts (password for all: `Demo@12345`)
| Username | Role |
|---|---|
| admin_demo | Administrator (also Django admin at /admin/) |
| mgmt_demo | Management |
| me_demo | M&E Officer |
| pm_demo, pm2_demo | Project Manager |
| field_demo, field2_demo | Field Officer |
| finance_demo | Finance Officer |
| grm_demo | GRM Officer |
| data_demo | Data Entry Officer |
| viewer_demo | Viewer |

**Change or delete these accounts before any real use.** `python manage.py seed_demo_data --reset` rebuilds the demo data.

## Try the main workflow
1. `data_demo`: Projects → Register project → *Save & submit*.
2. `pm_demo`: open the project → *Review & decide* → Approve (a user cannot approve a project they registered themselves).
3. `pm_demo`: *Start implementation*.
4. `field_demo`: Monitoring tab → *Submit progress update* with a photo.
5. `me_demo`: Monitoring → Review → Approve; the project's official progress changes only now.
6. `finance_demo`: record a payment. `grm_demo`: register a grievance. `admin_demo`: Audit trail.

## Role matrix
Defined in one place: `core/permissions.py`. Views, templates and the API all call `can(user, module, action)`.

## Tests
`python manage.py test` — 44 tests covering login/lockout, role permissions, project workflow, monitoring review, beneficiaries, payments, GRM, document access, reports/exports, notifications, audit, XSS/CSRF and API roles.

## Security notes
Role-based access on every view; CSRF on all forms; login lockout after 5 failures (10 min); open-redirect protection; upload type and size checks; restricted documents only through a permission-checked download view; CSV/Excel formula-injection guard; audit log is read-only; secrets in `.env`. For production set `DEBUG=False`, a strong `SECRET_KEY`, `ALLOWED_HOSTS`, HTTPS, configure SMTP (`EMAIL_BACKEND`) and serve media through the web server with the same restrictions.

## Known limits
No SMS/email delivery by default (in-system notifications only; reset links print to the console). No offline data capture (the UI warns when the connection drops). No GPS map view. Single-language (English).
