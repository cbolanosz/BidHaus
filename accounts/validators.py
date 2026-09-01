"""Field-level rules of the accounts app (DBR08)."""

from django.core.exceptions import ValidationError

MAX_DOCUMENT_SIZE_MB = 5
MAX_DOCUMENT_SIZE_BYTES = MAX_DOCUMENT_SIZE_MB * 1024 * 1024

DOCUMENT_EXTENSIONS = ["pdf", "jpg", "jpeg", "png"]


def validate_document_size(document):
    """Reject an identity document heavier than the limit."""
    if document.size > MAX_DOCUMENT_SIZE_BYTES:
        raise ValidationError(
            f"«{document.name}» pesa más de {MAX_DOCUMENT_SIZE_MB} MB."
        )
