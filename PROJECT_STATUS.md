# Playto Payout Engine - Project Status

## Current Snapshot (as of 2026-04-27)

### Completed

1. Backend foundation is set up in Django + DRF + Celery with PostgreSQL-ready settings.
2. Money model is implemented with integer paise values using BigIntegerField.
3. Ledger-based balance model is implemented (credits and debits only, no float arithmetic).
4. Payout API endpoint exists at POST /api/v1/payouts/.
5. Idempotency storage exists with merchant-scoped unique key and 24h expiry logic.
6. Concurrency protection exists using transaction.atomic() + select_for_update() on Merchant.
7. Payout state machine checks are enforced in the Payout model save() logic.
8. Background task exists for pending -> processing -> completed/failed with 70/20/10 simulation.
9. Retry flow for stuck processing payouts exists with exponential backoff and max attempts.
10. Failed payout refunds are credited back in the same transaction as status failure transition.
11. Balance endpoint exists at GET /api/v1/merchants/<id>/balance/.
12. Seed script exists at apps/api/seed.py for 3 merchants and ledger history.
13. Initial migration for payout models is present.
14. Two meaningful tests were added:
   - idempotency behavior test
   - concurrent payout overdraft prevention test

### In Progress / Not Done Yet

1. Frontend dashboard in apps/web is still template-level and does not yet show balance/payout data.
2. Payout history endpoint is not implemented as a dedicated API yet.
3. README is still template-level and needs submission-ready setup instructions.
4. EXPLAINER.md did not exist earlier and is now required for submission quality.
5. Live deployment (Railway/Render/Fly/Koyeb) is not complete yet.
6. End-to-end verification with running Redis + Celery worker against live Postgres is pending.

## What Has Been Shipped in Code

- Core settings and env wiring:
  - apps/api/core/settings.py
  - apps/api/.env
- Celery integration:
  - apps/api/core/celery.py
  - apps/api/core/__init__.py
- Domain models and invariants:
  - apps/api/payouts/models.py
- API views:
  - apps/api/payouts/views.py
  - apps/api/payouts/urls.py
  - apps/api/core/urls.py
- Worker logic:
  - apps/api/payouts/tasks.py
- Seed data:
  - apps/api/seed.py
- Tests:
  - apps/api/payouts/tests.py

## Known Gaps and Risks

1. API currently expects merchant_id in payout request body (auth-scoped merchant resolution is not implemented).
2. Idempotency key row is locked after merchant lock, which is acceptable for single merchant scope but should be load-tested under high contention.
3. There is no dedicated endpoint for payout history table consumption in frontend yet.
4. Deployment/ops files (Procfile/docker-compose and release commands) are not finalized.

## Tomorrow Completion Plan (Fast Track)

1. Update README for full local setup and run commands.
2. Add EXPLAINER.md with exact references to lock, idempotency, state checks, and AI audit.
3. Build minimal frontend dashboard:
   - balance cards
   - payout form
   - payout table
   - polling for status refresh
4. Add payout history API endpoint for frontend table.
5. Deploy API + Celery + Redis + Postgres to Railway.
6. Smoke test with seeded merchant and capture working URL.
7. Final submission polish and form submission.

## Quick Run Commands

From apps/api:

- python manage.py migrate
- python seed.py
- python manage.py runserver
- celery -A core worker -l info

From repo root:

- pnpm install
- pnpm --filter web dev
