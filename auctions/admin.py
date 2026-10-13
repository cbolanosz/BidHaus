"""Seeding of categories and inspection of auctions from the Django admin."""

from django.contrib import admin, messages

from auctions.exceptions import AuctionError
from auctions.models import MAX_PHOTOGRAPHS, Auction, Bid, Category, Photograph
from auctions.services import approve_auction_publication, reject_auction_publication


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
    readonly_fields = [
        "published_at",
        "winning_bid",
        "state",
        "resolved_by",
        "resolved_at",
    ]
    actions = ["approve", "reject"]

    @admin.action(description="Aprobar la publicación de las subastas")
    def approve(self, request, queryset):
        """Approve every selected pending publication request."""
        self._resolve_each(request, queryset, approve_auction_publication, "aprobaron")

    @admin.action(description="Rechazar la publicación de las subastas")
    def reject(self, request, queryset):
        """Reject every selected pending publication request."""
        self._resolve_each(request, queryset, reject_auction_publication, "rechazaron")

    def _resolve_each(self, request, queryset, resolve, past_tense):
        """Resolve selected rows and report already-decided requests."""
        resolved = 0
        for auction in queryset:
            try:
                resolve(auction, request.user)
            except AuctionError:
                self.message_user(
                    request,
                    f"«{auction.title}» ya tenía una decisión.",
                    messages.WARNING,
                )
            else:
                resolved += 1

        if resolved:
            self.message_user(request, f"Se {past_tense} {resolved} subastas.")


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
