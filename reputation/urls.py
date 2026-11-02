"""URL map of the reputation app, mounted under /reputation/."""

from django.urls import path

from reputation import views

app_name = "reputation"

urlpatterns = [
    path("pending/", views.sales_to_rate, name="sales_to_rate"),
    path("sales/<int:transaction_id>/rate/", views.rate, name="rate"),
]
