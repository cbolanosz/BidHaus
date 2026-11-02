"""Where an administrator reads what the two sides said about each other (FR24)."""

from django.contrib import admin

from reputation.models import Rating


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    """Reading only: a score is given from the site and never edited."""

    list_display = ["rated", "score", "rater", "transaction", "created_at"]
    list_filter = ["score"]
    search_fields = ["rated__email", "rater__email", "transaction__auction__title"]
    readonly_fields = ["transaction", "rater", "rated", "score", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
