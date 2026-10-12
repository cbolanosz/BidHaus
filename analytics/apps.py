from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "analytics"
    verbose_name = "Análisis"

    def ready(self):
        """Subscribe to the auction signals this app reacts to (FR25)."""
        from analytics import receivers  # noqa: F401
