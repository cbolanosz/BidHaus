"""URL map of the escrow app, mounted under /escrow/."""

from django.urls import path

from escrow import views

app_name = "escrow"

urlpatterns = [
    path(
        "transactions/<int:transaction_id>/",
        views.transaction_detail,
        name="transaction_detail",
    ),
    path(
        "transactions/<int:transaction_id>/confirm/",
        views.transaction_confirm_reception,
        name="transaction_confirm_reception",
    ),
]
