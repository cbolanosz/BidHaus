"""The person behind every auction and every bid (DBR01, DBR08)."""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.db import models

from accounts.managers import UserManager
from accounts.validators import DOCUMENT_EXTENSIONS, validate_document_size


class User(AbstractUser):
    """A BidHaus account, identified by its email address.

    Django's own user is extended instead of replaced, so password hashing,
    permissions and the admin keep working untouched.
    """

    class Role(models.TextChoices):
        BIDDER = "bidder", "Comprador"
        SELLER = "seller", "Vendedor"
        ADMINISTRATOR = "administrator", "Administrador"

    username = None
    first_name = None
    last_name = None

    email = models.EmailField("correo electrónico", unique=True)
    full_name = models.CharField("nombre completo", max_length=150)
    role = models.CharField("rol", max_length=20, choices=Role.choices, default=Role.BIDDER)
    is_verified = models.BooleanField("identidad verificada", default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return self.full_name or self.email


def identity_document_storage():
    """Store identity documents outside MEDIA_ROOT, where no URL reaches them.

    A callable, not an instance, so the migration records this function by
    name instead of freezing one machine's absolute path into the repository.
    """
    return FileSystemStorage(location=settings.IDENTITY_DOCUMENT_ROOT)


def identity_document_path(verification_request, filename):
    """Keep the document of each seller inside its own folder."""
    return f"verification/{verification_request.seller_id}/{filename}"


class VerificationRequest(models.Model):
    """A user asking to be trusted as a seller, with proof of identity (DBR08).

    The document is what an administrator reads to decide, and nothing else.
    Once the request is resolved the file is deleted and only the outcome is
    kept, because holding somebody's identity document longer than the
    decision needs it has no justification.
    """

    class State(models.TextChoices):
        PENDING = "pending", "Pendiente"
        APPROVED = "approved", "Aprobada"
        REJECTED = "rejected", "Rechazada"

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_requests",
        verbose_name="vendedor",
    )
    identity_document = models.FileField(
        "documento de identidad",
        storage=identity_document_storage,
        upload_to=identity_document_path,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(DOCUMENT_EXTENSIONS),
            validate_document_size,
        ],
    )
    state = models.CharField("estado", max_length=20, choices=State.choices, default=State.PENDING)
    submitted_at = models.DateTimeField("fecha de envío", auto_now_add=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="resolved_verification_requests",
        null=True,
        blank=True,
        verbose_name="resuelta por",
    )
    resolved_at = models.DateTimeField("fecha de resolución", null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["seller"],
                condition=models.Q(state="pending"),
                name="one_pending_request_per_seller",
            )
        ]
        verbose_name = "solicitud de verificación"
        verbose_name_plural = "solicitudes de verificación"

    def __str__(self):
        return f"{self.seller} · {self.get_state_display()}"

    @property
    def is_pending(self):
        """Whether an administrator has yet to decide on this request."""
        return self.state == self.State.PENDING
