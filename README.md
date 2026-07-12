# AI Powered Training Management System (TMS)

An enterprise Training Management System where administrators create & publish
courses, employees complete them, and **Claude AI** auto-generates quizzes from
the uploaded training material — with automatic evaluation, progress tracking,
reporting, notifications and verifiable certificates.

Built module-by-module with production-quality **layered architecture**, JWT +
RBAC security, and a modern responsive React UI (light/dark).

---

## Tech stack

| Layer     | Technology |
|-----------|------------|
| Frontend  | React 18, TypeScript, Vite, Tailwind CSS, ShadCN-style UI, React Router, React Query, Recharts |
| Backend   | Python 3.11, FastAPI, SQLAlchemy 2.0 — layered (Controller → Service → Repository → Model) |
| Database  | PostgreSQL |
| Auth      | JWT access + refresh, BCrypt hashing, role-based access control (Admin / Employee) |
| AI        | Claude API (document understanding, quiz generation, validation) + document-grounded offline fallback |
| Docs/PDF  | ReportLab (certificates & PDF reports), openpyxl (Excel), qrcode (certificate QR) |

## Feature status — all 9 phases complete ✅

| Phase | Feature | Highlights |
|-------|---------|-----------|
| 1 | **Auth & User Management** | Register → password-setup token → Set Password → Login; forgot/reset; JWT + RBAC; departments & groups |
| 2 | **Course Management** | Full CRUD; secure chunked upload (PDF/DOC/PPT/TXT/image/audio/video); publish workflow |
| 3 | **Course Assignment** | Assign to All / Department / Group / Individual(s); employees see only assigned courses; status machine |
| 4 | **AI Document Processing** | Extract & clean text from PDF/DOCX/PPTX/TXT on upload; status tracking |
| 5 | **AI Quiz Generation** | Claude-generated MCQ/True-False/Scenario questions, **grounded only in the material**; validation; balanced difficulty; offline fallback |
| 6 | **Quiz Engine** | Per-employee **random** questions, shuffled options, **same difficulty mix**; auto evaluation; pass/fail; retries; status updates |
| 7 | **Reports & Analytics** | Overview, department/employee breakdowns, completion trend chart; **Excel & PDF export** |
| 8 | **Notifications** | In-app bell + email (SMTP); triggers on assign/publish/result; due-date reminders |
| 9 | **Certificates** | PDF certificate with QR code, certificate number, public verification page |

---

## Quick start (Docker — recommended)

```bash
# from the repo root
export SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))")
export ANTHROPIC_API_KEY=sk-ant-...   # optional; offline fallback works without it
docker compose up --build
```

- Frontend: <http://localhost:8080>
- Backend API + Swagger: <http://localhost:8000/docs>
- Login: `admin` / `Admin@12345`

## Local development

### Backend
```bash
cd backend
python -m venv .venv && .venv/Scripts/activate      # Windows (use source .venv/bin/activate on *nix)
pip install -r requirements.txt
cp .env.example .env                                 # set DB creds + optional ANTHROPIC_API_KEY
psql -U postgres -c "CREATE DATABASE tms"            # once
uvicorn app.main:app --reload --port 8020
```
Tables auto-create, roles + a bootstrap admin (`admin` / `Admin@12345`) are seeded on first start.

### Frontend
```bash
cd frontend
npm install
npm run dev -- --port 5180 --strictPort            # http://localhost:5180 (proxies /api → :8020)
```

### Tests
```bash
cd backend
pytest                                              # 22 tests: unit + full end-to-end flow
```

---

## Architecture

```
Browser (React SPA)
   │  /api/v1/*  (JWT bearer)
   ▼
FastAPI app
   Controllers (api/v1/routers)   ← request/response, auth guards (RBAC)
   Services       (services/)     ← business logic, transactions, audit
   Repositories   (repositories/) ← SQLAlchemy data access
   Models         (models/)       ← ORM tables
   AI agents      (ai/)           ← document extraction, Claude client, quiz generator + validator
   Utilities      (utils/)        ← storage, email, PDF/Excel, certificate rendering
   ▼
PostgreSQL      +      local file storage (uploads, certificates)
```

### Backend layout
```
backend/app/
  core/          config, database, security, logging, bootstrap, exceptions
  models/        User, Role, Department, Group, Course, CourseDocument,
                 CourseAssignment, EmployeeCourseStatus, QuestionBank,
                 QuizAttempt, QuizAnswer, Notification, Certificate, AuditLog
  schemas/       Pydantic DTOs per domain
  repositories/  data-access layer
  services/      auth, user, course, assignment, quiz_generation, quiz,
                 report, notification, certificate, audit
  ai/            document_processor, claude_client, quiz_generator, question_validator
  api/v1/routers auth, users, departments, groups, courses, me, reports,
                 notifications, certificates
  utils/         storage, email, report_export, certificate_pdf
  tests/         unit + integration flow
```

### Frontend layout
```
frontend/src/
  components/    ui/ (ShadCN primitives), layout, dialogs, cards, NotificationBell
  context/       AuthProvider, ThemeProvider
  pages/         auth/*, admin/* (courses, employees, departments, groups, reports),
                 employee/* (my courses, viewer, quiz, certificate), VerifyPage
  lib/           api client (axios + token refresh), utils
  types/         shared TS types
```

## AI quiz generation — grounding & fallback

- Questions are generated **only** from the uploaded documents' extracted text; the
  prompt forbids inventing facts, and every question is validated (correct answer must
  be one of its options, no duplicates, correct option count, valid difficulty/type).
- With `ANTHROPIC_API_KEY` set, generation uses **Claude** (`CLAUDE_MODEL`, default
  `claude-opus-4-8`) in batches with validation + regeneration.
- Without a key, a **deterministic, document-grounded fallback** derives questions
  from sentences in the material so the whole system remains demonstrable offline.
- The **quiz engine** samples a per-employee random subset while keeping the **same
  difficulty distribution** for everyone (40% easy / 40% medium / 20% hard), and
  shuffles answer options.

## Key API surface (`/api/v1`)

```
Auth        /auth/register  /auth/set-password  /auth/login  /auth/refresh
            /auth/forgot-password  /auth/reset-password  /auth/me  /auth/change-password
Users       /users (+ activate/deactivate)   Departments /departments   Groups /groups
Courses     /courses (CRUD, publish, documents, process, generate-questions, questions,
                      assign, enrollments)
Employee    /me/courses  /me/courses/{id}  /me/courses/{id}/start  .../complete-content
            /me/courses/{id}/quiz/start   /me/quiz/{id}/submit  /me/quiz/{id}/result
            /me/notifications   /me/report
Reports     /reports/overview /departments /employees /trend  /export/excel  /export/pdf
Certificates /me/courses/{id}/certificate(/download)   /certificates/verify/{number} (public)
```
Full interactive docs at `/docs` (Swagger) and `/redoc`.

## Security
- Passwords hashed with BCrypt; JWT access + refresh tokens; silent refresh on the client.
- RBAC enforced per route; employees are isolated to their own assigned courses & data.
- Pending accounts (registered, password not set) cannot log in until Set Password.
- Audit log of auth, course, assignment and quiz events.

## Notes
- Default credentials are for development — change `FIRST_ADMIN_PASSWORD` / `SECRET_KEY`
  before any real use.
- Email requires SMTP settings; without them notifications are still recorded in-app and
  email delivery is marked `skipped`.
