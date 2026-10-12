"""Where an administrator reads why an auction scored what it scored."""

from django.contrib import admin

from analytics.models import TrustScore


@admin.register(TrustScore)
class TrustScoreAdmin(admin.ModelAdmin):
    """Reading only: the score is calculated, never typed in."""

    list_display = ["auction", "score", "calculated_at"]
    list_filter = ["calculated_at"]
    search_fields = ["auction__title"]
    readonly_fields = ["auction", "score", "factors", "calculated_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
