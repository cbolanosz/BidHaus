from django.apps import AppConfig


class EscrowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "escrow"
    verbose_name = "Custodia"

    def ready(self):
        """Subscribe to the auction signals this app reacts to (FR14)."""
        from escrow import receivers  # noqa: F401
