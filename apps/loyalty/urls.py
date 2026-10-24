from django.urls import path

from apps.loyalty.views import AccountLoyaltyView

urlpatterns = [
    path("account/loyalty/", AccountLoyaltyView.as_view(), name="account-loyalty"),
]
