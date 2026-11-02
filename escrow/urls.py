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
    path(
        "transactions/<int:transaction_id>/dispute/",
        views.transaction_open_dispute,
        name="transaction_open_dispute",
    ),
    path(
        "disputes/<int:dispute_id>/evidence/",
        views.dispute_evidence,
        name="dispute_evidence",
    ),
    path(
        "evidence/<int:evidence_id>/",
        views.evidence_file,
        name="evidence_file",
    ),
]
