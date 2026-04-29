import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from payouts.models import IdempotencyKey, LedgerEntry, Merchant, Payout
from payouts.tasks import process_payout


class PayoutCreateView(APIView):
    def post(self, request):
        idempotency_header = request.headers.get("Idempotency-Key")
        if not idempotency_header:
            return Response(
                {"detail": "Idempotency-Key header is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            idempotency_uuid = uuid.UUID(idempotency_header)
        except ValueError:
            return Response(
                {"detail": "Idempotency-Key must be a valid UUID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        merchant_id = request.data.get("merchant_id")
        amount_paise = request.data.get("amount_paise")
        bank_account_id = request.data.get("bank_account_id")

        if not merchant_id or not bank_account_id or amount_paise is None:
            return Response(
                {
                    "detail": "merchant_id, amount_paise, and bank_account_id are required"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount_paise = int(amount_paise)
        except (TypeError, ValueError):
            return Response(
                {"detail": "amount_paise must be an integer in paise"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount_paise <= 0:
            return Response(
                {"detail": "amount_paise must be greater than zero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            merchant = (
                Merchant.objects.select_for_update()
                .filter(id=merchant_id)
                .first()
            )

            if merchant is None:
                return Response(
                    {"detail": "Merchant not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            existing_key = (
                IdempotencyKey.objects.select_for_update()
                .filter(merchant=merchant, key=idempotency_uuid)
                .first()
            )

            if existing_key:
                if existing_key.created_at >= timezone.now() - timedelta(hours=24):
                    stored_response = existing_key.response_body
                    return Response(
                        stored_response.get("data", stored_response),
                        status=stored_response.get("status_code", status.HTTP_200_OK),
                    )
                existing_key.delete()

            available_balance = int(
                LedgerEntry.objects.filter(merchant=merchant).aggregate(
                    total=Coalesce(Sum("amount_paise"), 0)
                )["total"]
            )
            if available_balance < amount_paise:
                return Response(
                    {"detail": "Insufficient balance"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payout = Payout.objects.create(
                merchant=merchant,
                amount_paise=amount_paise,
                status=Payout.Status.PENDING,
                bank_account_id=bank_account_id,
                idempotency_key=idempotency_uuid,
            )

            LedgerEntry.objects.create(
                merchant=merchant,
                amount_paise=-amount_paise,
                entry_type=LedgerEntry.EntryType.DEBIT,
                description=f"Payout hold for payout_id={payout.id}",
            )

            response_data = {
                "payout_id": payout.id,
                "merchant_id": merchant.id,
                "amount_paise": payout.amount_paise,
                "status": payout.status,
                "bank_account_id": payout.bank_account_id,
                "attempts": payout.attempts,
            }

            IdempotencyKey.objects.create(
                merchant=merchant,
                key=idempotency_uuid,
                response_body={
                    "status_code": status.HTTP_201_CREATED,
                    "data": response_data,
                },
            )

        process_payout.delay(payout.id)
        return Response(response_data, status=status.HTTP_201_CREATED)


class MerchantBalanceView(APIView):
    def get(self, request, merchant_id: int):
        merchant = get_object_or_404(Merchant, id=merchant_id)

        available_balance = int(
            LedgerEntry.objects.filter(merchant=merchant).aggregate(
                total=Coalesce(Sum("amount_paise"), 0)
            )["total"]
        )
        held_balance = int(
            Payout.objects.filter(
                merchant=merchant,
                status__in=[Payout.Status.PENDING, Payout.Status.PROCESSING],
            ).aggregate(total=Coalesce(Sum("amount_paise"), 0))["total"]
        )
        recent_entries = list(
            LedgerEntry.objects.filter(merchant=merchant)
            .order_by("-created_at")[:10]
            .values("id", "amount_paise", "entry_type", "description", "created_at")
        )

        return Response(
            {
                "merchant_id": merchant.id,
                "available_balance": available_balance,
                "held_balance": held_balance,
                "recent_ledger_entries": recent_entries,
            },
            status=status.HTTP_200_OK,
        )

