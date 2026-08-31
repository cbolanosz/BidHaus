"""Tests of the publication page (FR01)."""

import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from auctions.forms import DATETIME_LOCAL_FORMAT
from auctions.models import MAX_PHOTOGRAPHS, Auction, Category
from auctions.tests.factories import build_image, create_bidder, create_seller

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AuctionCreateViewTests(TestCase):
    def setUp(self):
        self.seller = create_seller()
        self.category = Category.objects.create(name="Fotografía")
        self.url = reverse("auctions:auction_create")
        self.client.force_login(self.seller)

    def post(self, **overrides):
        closing_date = timezone.localtime(timezone.now() + timedelta(days=2))
        payload = {
            "category": self.category.pk,
            "title": "Cámara Yashica FX-3",
            "description": "Cámara analógica funcional, con estuche original.",
            "condition": Auction.Condition.USED,
            "starting_price": "250000",
            "closing_date": closing_date.strftime(DATETIME_LOCAL_FORMAT),
            "images": [build_image()],
        }
        payload.update(overrides)
        return self.client.post(self.url, payload)

    def test_shows_the_empty_form(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auctions/auction_form.html")

    def test_publishes_the_auction_and_sends_the_seller_to_its_photographs(self):
        response = self.post()

        auction = Auction.objects.get()
        self.assertRedirects(
            response, reverse("auctions:auction_photographs", args=[auction.pk])
        )

    def test_stores_the_photograph_that_came_with_the_form(self):
        self.post(images=[build_image(), build_image()])

        self.assertEqual(Auction.objects.get().photographs.count(), 2)

    def test_requires_at_least_one_photograph(self):
        response = self.post(images=[])

        self.assertEqual(Auction.objects.count(), 0)
        self.assertContains(response, "Este campo es obligatorio.")

    def test_reports_more_photographs_than_an_auction_admits(self):
        images = [build_image() for _ in range(MAX_PHOTOGRAPHS + 1)]

        response = self.post(images=images)

        self.assertEqual(Auction.objects.count(), 0)
        self.assertContains(response, "admite 8 fotografías como máximo")

    def test_publishes_the_auction_in_the_name_of_the_user_in_session(self):
        self.post()

        self.assertEqual(Auction.objects.get().seller, self.seller)

    def test_sends_a_visitor_who_is_not_logged_in_to_the_login_page(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")
        self.assertEqual(Auction.objects.count(), 0)

    def test_refuses_a_user_whose_role_is_not_seller(self):
        self.client.force_login(create_bidder())

        response = self.post()

        self.assertEqual(Auction.objects.count(), 0)
        self.assertContains(response, "no tiene el rol de vendedor")

    def test_reports_an_invalid_closing_date_in_spanish(self):
        past_date = timezone.localtime(timezone.now() - timedelta(days=1))

        response = self.post(closing_date=past_date.strftime(DATETIME_LOCAL_FORMAT))

        self.assertEqual(Auction.objects.count(), 0)
        self.assertContains(response, "La fecha de cierre debe ser posterior a la publicación.")
