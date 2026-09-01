"""URL map of the accounts app, mounted under /accounts/."""

from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.sign_up, name="sign_up"),
    path("login/", views.log_in, name="log_in"),
    path("logout/", views.log_out, name="log_out"),
    path("verification/", views.verification_request_create, name="verification_request"),
    path(
        "verification/<int:request_id>/document/",
        views.identity_document,
        name="identity_document",
    ),
]
