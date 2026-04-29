# Playto Payout Engine

Minimal payout engine for Indian merchants receiving international payments.

## Live URLs

- Frontend (Vercel): https://paytto-payout-web.vercel.app/
- API (Render): https://paytto-payout-1.onrender.com/api/
- Repo: https://github.com/rohitmodi970/paytto-payout

## Stack

- Backend: Django + DRF + Celery + Redis
- Frontend: Next.js + Tailwind + shadcn
- Database: PostgreSQL (Neon-compatible)
- Monorepo: pnpm + turbo

## What This Project Does

This service models a payout engine where:

- Merchants have a ledger of credits and debits (paise only).
- A payout request holds funds immediately and creates a payout record.
- Background processing moves payouts through pending -> processing -> completed/failed.
- Failed payouts return funds through a compensating ledger entry.
- Idempotency keys prevent duplicate payouts on retries.

## Repository Layout

- apps/api: Django backend and payout engine
- apps/web: Next.js frontend dashboard
- packages/ui: shared UI components

## Key Features

- Ledger-based balances (no stored mutable balance column).
- Concurrency protection using PostgreSQL row locks (select_for_update).
- Idempotency keyed per merchant with 24h expiry.
- Explicit payout state machine enforcement.
- Celery background worker simulates settlement outcomes (70/20/10).
- Retry logic for stuck payouts with exponential backoff and max attempts.
- Seed script for demo merchants and ledger history.

## API Endpoints

- POST /api/v1/payouts/
	- Headers: Idempotency-Key: <uuid>
	- Body: { merchant_id, amount_paise, bank_account_id }
- GET /api/v1/merchants/<merchant_id>/balance/

## Local Setup

### 1) Install dependencies

From repo root:

```bash
pnpm install
```

From API app (Python deps):

```bash
cd apps/api
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Configure environment

Create or update apps/api/.env:

```env
DATABASE_URL=postgresql://<user>:<password>@<host>/<database>?sslmode=require
SECRET_KEY=some-random-secret
DEBUG=True
REDIS_URL=redis://localhost:6379/0
```

Create or update apps/web/.env.local:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

### 3) Run migrations and seed data

```bash
cd apps/api
python manage.py migrate
python seed.py
```

### 4) Start services

Start Django API:

```bash
cd apps/api
python manage.py runserver
```

Start Celery worker:

```bash
cd apps/api
celery -A core worker -l info
```

Start frontend:

```bash
cd <repo-root>
pnpm --filter web dev
```

## Tests

Run backend tests:

```bash
cd apps/api
python manage.py test payouts
```

Included tests:

- Idempotency replay behavior
- Concurrent payout race protection

## Deployment Notes

Backend (Render):

- Root directory: apps/api
- Build command: pip install -r requirements.txt
- Start command: gunicorn core.wsgi:application --bind 0.0.0.0:$PORT

Required env vars (Render):

- DATABASE_URL
- SECRET_KEY
- DEBUG=False
- REDIS_URL
- CORS_ALLOWED_ORIGINS=https://paytto-payout-web.vercel.app

Frontend (Vercel):

- NEXT_PUBLIC_API_BASE_URL=https://paytto-payout-1.onrender.com/api/v1

## Design Notes

- All money stored in paise (BigIntegerField).
- Balance is derived from ledger aggregation in the DB (no floating math).
- Payout status transitions are validated by explicit state machine rules.
- Idempotency returns the exact same response on retries.

## Submission Docs

- EXPLAINER.md: detailed reasoning + diagrams
