"""Objects the tests need in order to exercise a use case."""

from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from itertools import count

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from auctions.models import Auction, Bid, Category
from auctions.validators import MAX_PHOTOGRAPH_SIZE_BYTES

User = get_user_model()

_seller_numbers = count(1)
_bidder_numbers = count(1)


def create_seller(email=None):
    """Create a user registered with the seller role, with a unique email."""
    return User.objects.create_user(
        email=email or f"vendedora{next(_seller_numbers)}@bidhaus.co",
        password="clave-de-prueba",
        full_name="Vendedora de prueba",
        role=User.Role.SELLER,
    )


def create_bidder(full_name="Pujador de prueba"):
    """Create a user registered with the bidder role, with a unique email."""
    return User.objects.create_user(
        email=f"pujador{next(_bidder_numbers)}@bidhaus.co",
        password="clave-de-prueba",
        full_name=full_name,
        role=User.Role.BIDDER,
    )


def create_bid(auction, amount, bidder=None):
    """Register a bid directly, without the rules that FR05 will add."""
    return Bid.objects.create(
        auction=auction, bidder=bidder or create_bidder(), amount=Decimal(amount)
    )


def create_category(name="Fotografía"):
    """Return the category with that name, creating it the first time."""
    category, _ = Category.objects.get_or_create(name=name)
    return category


def create_auction(seller=None, **overrides):
    """Create an open auction that closes in two days."""
    fields = {
        "seller": seller or create_seller(),
        "category": create_category(),
        "title": "Cámara Yashica FX-3",
        "description": "Cámara analógica funcional, con estuche original.",
        "condition": Auction.Condition.USED,
        "starting_price": Decimal("250000.00"),
        "current_price": Decimal("250000.00"),
        "closing_date": timezone.now() + timedelta(days=2),
    }
    fields.update(overrides)
    return Auction.objects.create(**fields)


def build_image(name="foto.jpg"):
    """Build a small real JPEG, ready to be posted as an upload."""
    return SimpleUploadedFile(name, _jpeg_bytes(), content_type="image/jpeg")


def build_oversized_image(name="pesada.jpg"):
    """Build a real JPEG padded past the size limit of DBR03."""
    padding = b"\x00" * (MAX_PHOTOGRAPH_SIZE_BYTES + 1)
    return SimpleUploadedFile(name, _jpeg_bytes() + padding, content_type="image/jpeg")


def _jpeg_bytes():
    """Return the bytes of a 20x20 JPEG that Pillow can open."""
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "navy").save(buffer, format="JPEG")
    return buffer.getvalue()
