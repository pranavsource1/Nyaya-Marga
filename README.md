# Nyaya Marga Run Instructions

This project has a FastAPI backend, PostgreSQL, Redis/Celery worker, and a Next.js frontend.

## Prerequisites

- Docker Desktop
- Node.js 18 or newer
- npm
- PowerShell

## Recommended: Run Backend With Docker

From the project root:

```powershell
cd "D:\Nyaya Marga 0.1"
docker-compose up -d --build
```

This starts:

- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`
- FastAPI backend on `http://localhost:8000`
- Celery worker for PDF/NLP/action-plan processing

Check backend health:

```powershell
Invoke-WebRequest http://localhost:8000/api/v1/health -UseBasicParsing
```

API docs:

```text
http://localhost:8000/docs
```

## Run Frontend

Open a second PowerShell window:

```powershell
cd "D:\Nyaya Marga 0.1\frontend"
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

The frontend uses this backend URL from `frontend\.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Main Pages

- Upload judgments: `http://localhost:3000`
- Dashboard: `http://localhost:3000/dashboard`
- All cases: `http://localhost:3000/cases`
- Verification queue: `http://localhost:3000/verify`
- Precedent search: `http://localhost:3000/search`
- Audit trail: `http://localhost:3000/audit`
- Users and roles: `http://localhost:3000/users`

## Verify Everything Is Running

Backend:

```powershell
Invoke-WebRequest http://localhost:8000/api/v1/health -UseBasicParsing
```

Frontend:

```powershell
Invoke-WebRequest http://localhost:3000 -UseBasicParsing
```

Build frontend:

```powershell
cd "D:\Nyaya Marga 0.1\frontend"
npm run build
```

## Stop Services

Stop frontend:

```text
Press Ctrl+C in the frontend terminal.
```

Stop backend Docker services:

```powershell
cd "D:\Nyaya Marga 0.1"
docker-compose down
```

## Useful Logs

All Docker logs:

```powershell
docker-compose logs -f
```

Backend logs:

```powershell
docker-compose logs -f backend
```

Celery worker logs:

```powershell
docker-compose logs -f celery_worker
```

## Notes

- Do not use demo data. The UI reads data from the backend endpoints.
- Upload a PDF from the upload page to create a real case.
- Processing depends on PostgreSQL, Redis, the backend, and the Celery worker all being up.
- If `localhost:3000` is busy, Next.js may choose another port. Check the terminal output for the actual URL.
