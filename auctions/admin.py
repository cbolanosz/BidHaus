"""Seeding of categories and inspection of auctions from the Django admin."""

from django.contrib import admin

from auctions.models import Auction, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ["title", "seller", "category", "condition", "current_price", "closing_date", "state"]
    list_filter = ["state", "condition", "category"]
    search_fields = ["title", "description"]
    readonly_fields = ["published_at"]
