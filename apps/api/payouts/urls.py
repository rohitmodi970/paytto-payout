from django.urls import path

from payouts.views import MerchantBalanceView, PayoutCreateView

urlpatterns = [
    path("payouts/", PayoutCreateView.as_view(), name="create-payout"),
    path(
        "merchants/<int:merchant_id>/balance/",
        MerchantBalanceView.as_view(),
        name="merchant-balance",
    ),
]
