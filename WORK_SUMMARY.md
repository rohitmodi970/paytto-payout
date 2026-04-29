# Work Summary (as of 2026-04-28)

## What we did (explained)

### Backend architecture
- Built the payout engine in Django + DRF with Celery and Redis for background processing.
- Modeled money as integer paise using BigIntegerField to avoid floating-point issues.
- Implemented a ledger-based balance model: balance is derived by aggregating ledger rows (credits and debits), not stored as a mutable field.

### Payout flow
- Added POST /api/v1/payouts/ to create a payout.
- Added idempotency handling via Idempotency-Key, scoped per merchant, to ensure repeat requests return the same stored response (no duplicate payouts).
- Protected concurrency with select_for_update on the Merchant row inside transaction.atomic so only one payout can pass balance check and hold per merchant at a time.
- Enforced a payout state machine in the model to block invalid transitions.

### Background processing
- Added Celery task to move payouts from pending -> processing -> completed/failed (70/20/10 simulation).
- Added retry logic with exponential backoff for stuck processing payouts.
- On failure, refund is credited back to the ledger within the same transaction as the failure transition.

### Seed + tests
- Added seed data for 3 merchants and historical ledger entries (apps/api/seed.py).
- Added two tests:
  - idempotency replay behavior
  - concurrent payout race protection

## Do we need to create tables?

Yes. The database tables are created by Django migrations. The initial migration already exists. You still need to run migrations against your local or deployed database to create the tables.

### Table creation steps

```bash
cd apps/api
python manage.py migrate
```

If models change later, run:

```bash
python manage.py makemigrations
python manage.py migrate
```

## What is left to finish

### Backend/API
- Add a payout history endpoint for the frontend table (e.g., GET /api/v1/payouts/?merchant_id=...).
- Decide whether merchant identity should come from auth instead of request body.
- End-to-end verification with Redis + Celery worker + Postgres.

### Frontend
- Build the dashboard to show balance, payout form, and payout table.
- Poll or refresh payout status updates.

### Docs and deployment
- Update README with final setup + run steps.
- Deploy API + Celery + Redis + Postgres (Railway/Render/Fly/Koyeb).
- Smoke test deployment and capture URL.

## Quick run commands

From apps/api:

```bash
python manage.py migrate
python seed.py
python manage.py runserver
celery -A core worker -l info
```

From repo root:

```bash
pnpm install
pnpm --filter web dev
```
