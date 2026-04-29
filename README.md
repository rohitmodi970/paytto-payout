# Playto Payout Engine

Minimal payout engine for Indian merchants receiving international payments.

## Stack

- Backend: Django + DRF + Celery + Redis
- Frontend: Next.js + Tailwind + shadcn
- Database: PostgreSQL (Neon-compatible)
- Monorepo: pnpm + turbo

## Repository Layout

- apps/api: Django backend and payout engine
- apps/web: Next.js frontend dashboard (in progress)
- packages/ui: shared UI components

## Backend Features Implemented

- Ledger-based merchant balance with integer paise storage only
- Payout creation endpoint with idempotency key handling
- Merchant-level concurrency protection using select_for_update
- Payout state machine enforcement
- Celery background payout processor with 70/20/10 simulation
- Retry for stuck processing payouts with exponential backoff and max attempts
- Atomic refund to ledger on payout failure
- Seed script for demo merchants and ledger history

## API Endpoints

- POST /api/v1/payouts/
- GET /api/v1/merchants/<merchant_id>/balance/

## Local Setup

### 1. Install dependencies

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

### 2. Configure environment

Create or update apps/api/.env:

```env
DATABASE_URL=postgresql://<user>:<password>@<host>/<database>?sslmode=require
SECRET_KEY=some-random-secret
DEBUG=True
REDIS_URL=redis://localhost:6379/0
```

### 3. Run database migrations and seed data

```bash
cd apps/api
python manage.py migrate
python seed.py
```

### 4. Start services

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

- idempotency replay behavior
- concurrent payout race protection

## Important Design Notes

- All money uses BigIntegerField in paise.
- Balance is computed from ledger aggregates at query time.
- No float-based money math.
- Payout transitions are validated by explicit state-machine rules.

## Submission Docs

- EXPLAINER.md: answers the 5 challenge questions
- PROJECT_STATUS.md: what is done and what remains
