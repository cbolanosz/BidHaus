"""Tests of the publication use case (FR01)."""

import tempfile
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from auctions.exceptions import NoPhotographs, NotASeller
from auctions.models import Auction, Category
from auctions.services import publish_auction
from auctions.tests.factories import build_image, create_seller

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PublishAuctionTests(TestCase):
    def setUp(self):
        self.seller = create_seller()
        self.category = Category.objects.create(name="Coleccionables")
        self.closing_date = timezone.now() + timedelta(days=3)

    def publish(self, **overrides):
        arguments = {
            "seller": self.seller,
            "category": self.category,
            "title": "Cámara Yashica FX-3",
            "description": "Cámara analógica funcional, con estuche original.",
            "condition": Auction.Condition.USED,
            "starting_price": Decimal("250000.00"),
            "closing_date": self.closing_date,
            "images": [build_image()],
        }
        arguments.update(overrides)
        return publish_auction(**arguments)

    def test_publishes_an_open_auction(self):
        auction = self.publish()

        self.assertEqual(auction.state, Auction.State.OPEN)
        self.assertEqual(Auction.objects.count(), 1)

    def test_current_price_starts_at_the_starting_price(self):
        auction = self.publish(starting_price=Decimal("80000.00"))

        self.assertEqual(auction.current_price, Decimal("80000.00"))

    def test_stores_the_first_photographs_with_the_auction(self):
        auction = self.publish(images=[build_image(), build_image()])

        self.assertEqual(auction.photographs.count(), 2)

    def test_rejects_an_auction_without_photographs(self):
        with self.assertRaises(NoPhotographs):
            self.publish(images=[])

        self.assertEqual(Auction.objects.count(), 0)

    def test_rejects_a_closing_date_already_in_the_past(self):
        past_date = timezone.now() - timedelta(hours=1)

        with self.assertRaises(ValidationError):
            self.publish(closing_date=past_date)

        self.assertEqual(Auction.objects.count(), 0)

    def test_rejects_a_user_who_is_not_a_registered_seller(self):
        bidder = User.objects.create_user(
            email="comprador@bidhaus.co",
            password="clave-de-prueba",
            full_name="Comprador de prueba",
            role=User.Role.BIDDER,
        )

        with self.assertRaises(NotASeller):
            self.publish(seller=bidder)

        self.assertEqual(Auction.objects.count(), 0)

    def test_rejects_a_starting_price_below_the_minimum(self):
        with self.assertRaises(ValidationError):
            self.publish(starting_price=Decimal("0.00"))

        self.assertEqual(Auction.objects.count(), 0)
