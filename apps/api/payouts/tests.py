import threading
import uuid
from unittest.mock import patch

from django.test import TransactionTestCase
from rest_framework import status
from rest_framework.test import APIClient

from payouts.models import LedgerEntry, Merchant, Payout


class PayoutApiTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            email="merchant@example.com",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=10000,
            entry_type=LedgerEntry.EntryType.CREDIT,
            description="Initial credit",
        )
        self.payout_url = "/api/v1/payouts/"

    @patch("payouts.views.process_payout.delay")
    def test_idempotent_payout_request_returns_same_response(self, mock_delay):
        client = APIClient()
        idem_key = str(uuid.uuid4())
        payload = {
            "merchant_id": self.merchant.id,
            "amount_paise": 2500,
            "bank_account_id": "bank_acc_001",
        }
        headers = {"HTTP_IDEMPOTENCY_KEY": idem_key}

        first = client.post(self.payout_url, payload, format="json", **headers)
        second = client.post(self.payout_url, payload, format="json", **headers)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, first.status_code)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)
        self.assertEqual(mock_delay.call_count, 1)

    @patch("payouts.views.process_payout.delay")
    def test_concurrent_payouts_only_one_succeeds_when_balance_insufficient(self, mock_delay):
        barrier = threading.Barrier(2)
        results = []

        def call_payout(amount, key):
            client = APIClient()
            payload = {
                "merchant_id": self.merchant.id,
                "amount_paise": amount,
                "bank_account_id": "bank_acc_001",
            }
            headers = {"HTTP_IDEMPOTENCY_KEY": key}
            barrier.wait()
            response = client.post(self.payout_url, payload, format="json", **headers)
            results.append(response.status_code)

        t1 = threading.Thread(target=call_payout, args=(6000, str(uuid.uuid4())))
        t2 = threading.Thread(target=call_payout, args=(6000, str(uuid.uuid4())))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        success_count = sum(1 for code in results if code == status.HTTP_201_CREATED)
        failed_count = sum(1 for code in results if code == status.HTTP_400_BAD_REQUEST)

        self.assertEqual(success_count, 1)
        self.assertEqual(failed_count, 1)
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)
        self.assertEqual(mock_delay.call_count, 1)

