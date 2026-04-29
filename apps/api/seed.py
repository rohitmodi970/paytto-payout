import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from payouts.models import LedgerEntry, Merchant


def seed():
    merchants = [
        {"name": "Aarav Exports", "email": "aarav@example.com"},
        {"name": "Maya Crafts", "email": "maya@example.com"},
        {"name": "Rohan Foods", "email": "rohan@example.com"},
    ]

    for merchant_data in merchants:
        merchant, _ = Merchant.objects.get_or_create(
            email=merchant_data["email"],
            defaults={"name": merchant_data["name"]},
        )

        if not LedgerEntry.objects.filter(merchant=merchant).exists():
            LedgerEntry.objects.bulk_create(
                [
                    LedgerEntry(
                        merchant=merchant,
                        amount_paise=250000,
                        entry_type=LedgerEntry.EntryType.CREDIT,
                        description="Initial deposit",
                    ),
                    LedgerEntry(
                        merchant=merchant,
                        amount_paise=125000,
                        entry_type=LedgerEntry.EntryType.CREDIT,
                        description="Weekly settlement",
                    ),
                    LedgerEntry(
                        merchant=merchant,
                        amount_paise=-25000,
                        entry_type=LedgerEntry.EntryType.DEBIT,
                        description="Payout hold demo",
                    ),
                ]
            )

    print("Seed complete: 3 merchants ensured with ledger history")


if __name__ == "__main__":
    seed()
