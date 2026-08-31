"""URL map of the accounts app, mounted under /accounts/."""

from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.sign_up, name="sign_up"),
    path("login/", views.log_in, name="log_in"),
]
