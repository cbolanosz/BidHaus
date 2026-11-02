"""Field-level rules of the escrow app (DBR07)."""

from django.core.exceptions import ValidationError

MAX_EVIDENCE_SIZE_MB = 5
MAX_EVIDENCE_SIZE_BYTES = MAX_EVIDENCE_SIZE_MB * 1024 * 1024

EVIDENCE_EXTENSIONS = ["pdf", "jpg", "jpeg", "png"]


def validate_evidence_size(evidence_file):
    """Reject a piece of evidence heavier than the limit."""
    if evidence_file.size > MAX_EVIDENCE_SIZE_BYTES:
        raise ValidationError(
            f"«{evidence_file.name}» pesa más de {MAX_EVIDENCE_SIZE_MB} MB."
        )
