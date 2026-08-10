"""URL map of the auctions app."""

from django.urls import path

from auctions import views

app_name = "auctions"

urlpatterns = [
    path("", views.auction_catalogue, name="catalogue"),
    path("auctions/new/", views.auction_create, name="auction_create"),
    path("auctions/<int:auction_id>/", views.auction_detail, name="auction_detail"),
    path(
        "auctions/<int:auction_id>/photographs/",
        views.auction_photographs,
        name="auction_photographs",
    ),
]
