"""Seeding of categories and inspection of auctions from the Django admin."""

from django.contrib import admin

from auctions.models import MAX_PHOTOGRAPHS, Auction, Bid, Category, Photograph


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


class PhotographInline(admin.TabularInline):
    model = Photograph
    extra = 0
    max_num = MAX_PHOTOGRAPHS


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    inlines = [PhotographInline]
    list_display = ["title", "seller", "category", "condition", "current_price", "closing_date", "state"]
    list_filter = ["state", "condition", "category"]
    search_fields = ["title", "description"]
    readonly_fields = ["published_at"]


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    """A bid is append-only (DBR04), so the admin only reads it."""

    list_display = ["auction", "bidder", "amount", "timestamp"]
    list_filter = ["auction"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
