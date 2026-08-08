"""The person behind every auction and every bid (DBR01)."""

from django.contrib.auth.models import AbstractUser
from django.db import models

from accounts.managers import UserManager


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
