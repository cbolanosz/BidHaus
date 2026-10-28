"""Where an administrator reads the money a closed auction holds (FR14)."""

from django.contrib import admin

from escrow.models import Dispute, EscrowTransaction, StateChange


class StateChangeInline(admin.TabularInline):
    """The history of the transaction, read-only because DBR06 is append-only."""

    model = StateChange
    extra = 0
    can_delete = False
    fields = ["previous_state", "new_state", "actor", "timestamp"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(EscrowTransaction)
class EscrowTransactionAdmin(admin.ModelAdmin):
    """Reading only: the money moves through the services, never by hand."""

    list_display = ["auction", "buyer", "seller", "amount", "commission", "state", "created_at"]
    list_filter = ["state"]
    search_fields = ["auction__title", "buyer__email", "seller__email"]
    readonly_fields = ["auction", "buyer", "seller", "amount", "commission", "state", "created_at"]
    inlines = [StateChangeInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    """Reading only: a buyer opens a dispute from the site, never from here."""

    list_display = ["transaction", "opened_by", "state", "opened_at"]
    list_filter = ["state"]
    search_fields = ["transaction__auction__title", "opened_by__email"]
    readonly_fields = ["transaction", "opened_by", "description", "state", "opened_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
