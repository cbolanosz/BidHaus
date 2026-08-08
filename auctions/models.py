"""Catalogue entities: the categories and the auctions themselves (DBR02)."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from auctions.validators import validate_photograph_size

MINIMUM_PRICE = 1
MIN_PHOTOGRAPHS = 1
MAX_PHOTOGRAPHS = 8


class Category(models.Model):
    """A group of comparable items, chosen by the seller when publishing."""

    name = models.CharField("nombre", max_length=80, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.name


class AuctionQuerySet(models.QuerySet):
    """The filters of the catalogue (FR03).

    Every filter ignores itself when it receives no value, so a search combines
    them by chaining instead of by branching.
    """

    def open(self):
        return self.filter(state=Auction.State.OPEN)

    def matching_text(self, text):
        if not text:
            return self
        return self.filter(models.Q(title__icontains=text) | models.Q(description__icontains=text))

    def in_category(self, category):
        if category is None:
            return self
        return self.filter(category=category)

    def with_condition(self, condition):
        if not condition:
            return self
        return self.filter(condition=condition)

    def priced_from(self, minimum_price):
        if minimum_price is None:
            return self
        return self.filter(current_price__gte=minimum_price)

    def priced_up_to(self, maximum_price):
        if maximum_price is None:
            return self
        return self.filter(current_price__lte=maximum_price)

    def for_catalogue(self):
        """Fetch in advance everything a catalogue card shows, to avoid N+1 queries."""
        return self.select_related("seller", "category").prefetch_related("photographs")


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

    objects = AuctionQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "subasta"
        verbose_name_plural = "subastas"

    def __str__(self):
        return self.title

    @property
    def main_photograph(self):
        """The photograph the catalogue shows: the first one in display order."""
        photographs = list(self.photographs.all())
        if not photographs:
            return None
        return photographs[0]

    def clean(self):
        """Enforce that the auction closes after it is published (DBR02)."""
        if self.closing_date and self.closing_date <= timezone.now():
            raise ValidationError(
                {"closing_date": "La fecha de cierre debe ser posterior a la publicación."}
            )


def photograph_upload_path(photograph, filename):
    """Keep every file of an auction inside its own folder under MEDIA_ROOT."""
    return f"auctions/{photograph.auction_id}/{filename}"


class Photograph(models.Model):
    """One image of the item being auctioned (DBR03).

    An auction carries between MIN_PHOTOGRAPHS and MAX_PHOTOGRAPHS of them; the
    count is enforced by the service that uploads them, because a row cannot see
    how many siblings it has.
    """

    auction = models.ForeignKey(
        Auction,
        on_delete=models.CASCADE,
        related_name="photographs",
        verbose_name="subasta",
    )
    image = models.ImageField(
        "fotografía",
        upload_to=photograph_upload_path,
        validators=[validate_photograph_size],
    )
    display_order = models.PositiveSmallIntegerField("orden de presentación")

    class Meta:
        ordering = ["display_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["auction", "display_order"],
                name="unique_display_order_per_auction",
            )
        ]
        verbose_name = "fotografía"
        verbose_name_plural = "fotografías"

    def __str__(self):
        return f"{self.auction.title} ({self.display_order})"
