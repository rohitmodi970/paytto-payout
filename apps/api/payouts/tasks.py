import random

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from payouts.models import LedgerEntry, Payout


@shared_task(bind=True)
def process_payout(self, payout_id: int):
    with transaction.atomic():
        payout = Payout.objects.select_for_update().select_related("merchant").get(id=payout_id)

        if payout.status in {Payout.Status.COMPLETED, Payout.Status.FAILED}:
            return {"detail": "already-finalized", "payout_id": payout.id}

        if payout.status == Payout.Status.PENDING:
            payout.status = Payout.Status.PROCESSING
            payout.attempts += 1
            payout.save(update_fields=["status", "attempts", "updated_at"])
        elif payout.status == Payout.Status.PROCESSING:
            if (timezone.now() - payout.updated_at).total_seconds() <= 30:
                return {"detail": "still-processing", "payout_id": payout.id}

            if payout.attempts >= 3:
                _fail_and_return_funds(payout)
                return {"detail": "max-attempts-reached", "payout_id": payout.id}

            payout.attempts += 1
            payout.save(update_fields=["attempts", "updated_at"])

        if payout.attempts > 3:
            _fail_and_return_funds(payout)
            return {"detail": "max-attempts-reached", "payout_id": payout.id}

        outcome = random.random()
        if outcome < 0.7:
            payout.status = Payout.Status.COMPLETED
            payout.save(update_fields=["status", "updated_at"])
            return {"detail": "completed", "payout_id": payout.id}

        if outcome < 0.9:
            _fail_and_return_funds(payout)
            return {"detail": "failed", "payout_id": payout.id}

        retry_stuck_payout.apply_async(args=[payout.id], countdown=30)
        return {"detail": "processing-hang-simulated", "payout_id": payout.id}


@shared_task
def retry_stuck_payout(payout_id: int):
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if payout.status != Payout.Status.PROCESSING:
            return {"detail": "not-processing", "payout_id": payout.id}

        if (timezone.now() - payout.updated_at).total_seconds() <= 30:
            return {"detail": "not-stuck", "payout_id": payout.id}

        if payout.attempts >= 3:
            _fail_and_return_funds(payout)
            return {"detail": "max-attempts-reached", "payout_id": payout.id}

        backoff_seconds = 2 ** payout.attempts
        process_payout.apply_async(args=[payout.id], countdown=backoff_seconds)
        return {
            "detail": "retry-scheduled",
            "payout_id": payout.id,
            "countdown_seconds": backoff_seconds,
        }


def _fail_and_return_funds(payout: Payout):
    payout.status = Payout.Status.FAILED
    payout.save(update_fields=["status", "updated_at"])

    LedgerEntry.objects.create(
        merchant=payout.merchant,
        amount_paise=payout.amount_paise,
        entry_type=LedgerEntry.EntryType.CREDIT,
        description=f"Payout refund for payout_id={payout.id}",
    )
