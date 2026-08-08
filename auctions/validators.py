"""Field-level rules that the models and the forms share (DBR03)."""

from django.core.exceptions import ValidationError

MAX_PHOTOGRAPH_SIZE_MB = 5
MAX_PHOTOGRAPH_SIZE_BYTES = MAX_PHOTOGRAPH_SIZE_MB * 1024 * 1024


def validate_photograph_size(image):
    """Reject a photograph heavier than the limit allowed by DBR03."""
    if image.size > MAX_PHOTOGRAPH_SIZE_BYTES:
        raise ValidationError(
            f"«{image.name}» pesa más de {MAX_PHOTOGRAPH_SIZE_MB} MB."
        )
