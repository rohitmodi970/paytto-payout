import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone


class Merchant(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    def available_balance_paise(self) -> int:
        # Balance is always derived from ledger entries in a single DB query.
        return int(
            LedgerEntry.objects.filter(merchant=self).aggregate(
                total=Coalesce(Sum("amount_paise"), 0)
            )["total"]
        )

    def held_balance_paise(self) -> int:
        return int(
            Payout.objects.filter(
                merchant=self,
                status__in=[Payout.Status.PENDING, Payout.Status.PROCESSING],
            ).aggregate(total=Coalesce(Sum("amount_paise"), 0))["total"]
        )

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    amount_paise = models.BigIntegerField()
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self) -> None:
        if self.amount_paise == 0:
            raise ValidationError("amount_paise must be non-zero")

        if self.entry_type == self.EntryType.CREDIT and self.amount_paise < 0:
            raise ValidationError("credit ledger entries must have positive amount_paise")

        if self.entry_type == self.EntryType.DEBIT and self.amount_paise > 0:
            raise ValidationError("debit ledger entries must have negative amount_paise")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.merchant_id}:{self.entry_type}:{self.amount_paise}"


class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    VALID_STATUS_TRANSITIONS = {
        Status.PENDING: {Status.PROCESSING, Status.FAILED},
        Status.PROCESSING: {Status.COMPLETED, Status.FAILED},
        Status.COMPLETED: set(),
        Status.FAILED: set(),
    }

    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="payouts",
    )
    amount_paise = models.BigIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    bank_account_id = models.CharField(max_length=255)
    idempotency_key = models.UUIDField()
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "idempotency_key"],
                name="unique_payout_idempotency_per_merchant",
            )
        ]

    def clean(self) -> None:
        if self.amount_paise <= 0:
            raise ValidationError("amount_paise must be greater than zero")

    def save(self, *args, **kwargs):
        if self.pk:
            previous = Payout.objects.only("status").get(pk=self.pk)
            if self.status != previous.status:
                valid_targets = self.VALID_STATUS_TRANSITIONS.get(previous.status, set())
                if self.status not in valid_targets:
                    raise ValidationError(
                        f"Illegal status transition {previous.status} -> {self.status}"
                    )

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Payout<{self.id}>:{self.status}:{self.amount_paise}"


class IdempotencyKey(models.Model):
    key = models.UUIDField(default=uuid.uuid4)
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name="idempotency_keys",
    )
    response_body = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "key"],
                name="unique_idempotency_key_per_merchant",
            )
        ]

    @property
    def expires_at(self):
        return self.created_at + timedelta(hours=24)

    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    def __str__(self) -> str:
        return f"IdempotencyKey<{self.merchant_id}:{self.key}>"

