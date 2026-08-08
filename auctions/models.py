"""Catalogue entities: the categories and the auctions themselves (DBR02)."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

MINIMUM_PRICE = 1


class Category(models.Model):
    """A group of comparable items, chosen by the seller when publishing."""

    name = models.CharField("nombre", max_length=80, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.name


class Auction(models.Model):
    """An item offered by a seller until its closing date is reached."""

    class State(models.TextChoices):
        OPEN = "open", "Abierta"
        CLOSED = "closed", "Cerrada"
        CANCELLED = "cancelled", "Cancelada"

    class Condition(models.TextChoices):
        NEW = "new", "Nuevo"
        REFURBISHED = "refurbished", "Reacondicionado"
        USED = "used", "Usado"
        FOR_PARTS = "for_parts", "Para repuestos"

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="auctions",
        verbose_name="vendedor",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="auctions",
        verbose_name="categoría",
    )
    title = models.CharField("título", max_length=120)
    description = models.TextField("descripción")
    condition = models.CharField("estado del artículo", max_length=20, choices=Condition.choices)
    starting_price = models.DecimalField(
        "precio inicial",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(MINIMUM_PRICE)],
    )
    current_price = models.DecimalField("precio actual", max_digits=12, decimal_places=2)
    closing_date = models.DateTimeField("fecha de cierre")
    state = models.CharField("estado", max_length=20, choices=State.choices, default=State.OPEN)
    published_at = models.DateTimeField("fecha de publicación", auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "subasta"
        verbose_name_plural = "subastas"

    def __str__(self):
        return self.title

    def clean(self):
        """Enforce that the auction closes after it is published (DBR02)."""
        if self.closing_date and self.closing_date <= timezone.now():
            raise ValidationError(
                {"closing_date": "La fecha de cierre debe ser posterior a la publicación."}
            )
