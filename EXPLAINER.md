# EXPLAINER

## 1. The Ledger

Balance is always derived via DB aggregation on ledger rows:

```python
LedgerEntry.objects.filter(merchant=merchant).aggregate(
    total=Coalesce(Sum("amount_paise"), 0)
)["total"]
```

Why this model:

- Credits and debits are immutable accounting events.
- Merchant balance is not stored as a mutable field, so drift from failed writes is avoided.
- All amounts are integer paise (BigIntegerField), avoiding floating-point precision risk.

## 2. The Lock

The overdraft race is prevented here:

```python
with transaction.atomic():
    merchant = (
        Merchant.objects.select_for_update()
        .filter(id=merchant_id)
        .first()
    )
```

This uses PostgreSQL row-level locking (FOR UPDATE) on the merchant row. Concurrent payout requests for the same merchant serialize at this lock boundary, so only one request can pass balance check + hold at a time.

## 3. The Idempotency

How repeat detection works:

- Request key is read from Idempotency-Key header.
- System checks IdempotencyKey table scoped by merchant and key.
- If found and within 24h, it returns the stored response payload.

Current key lookup:

```python
existing_key = (
    IdempotencyKey.objects.select_for_update()
    .filter(merchant=merchant, key=idempotency_uuid)
    .first()
)
```

In-flight second request behavior:

- Because merchant row is locked first, second request waits.
- After first request commits, second sees the persisted idempotency record and replays exact response without creating duplicate payout.

## 4. The State Machine

Illegal transitions are blocked in Payout.save():

```python
if self.pk:
    previous = Payout.objects.only("status").get(pk=self.pk)
    if self.status != previous.status:
        valid_targets = self.VALID_STATUS_TRANSITIONS.get(previous.status, set())
        if self.status not in valid_targets:
            raise ValidationError(
                f"Illegal status transition {previous.status} -> {self.status}"
            )
```

So failed -> completed, completed -> pending, and all backward transitions raise ValidationError.

## 5. The AI Audit

Subtle issue caught:

- AI-first draft could have performed balance check before select_for_update, which creates a classic check-then-act race.
- Under two concurrent 60 INR payouts on 100 INR balance, both could pass pre-lock balance check and both debit.

What was corrected:

- Merchant row lock was moved to occur before balance computation and before payout/ledger write.
- Entire read-check-create sequence is inside one transaction.atomic block.

Result:

- Exactly one payout succeeds in concurrent insufficient-balance scenario.
- Concurrency test was added to verify this behavior.
