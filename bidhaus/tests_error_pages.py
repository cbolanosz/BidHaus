"""Tests of the pages a visitor sees when a request cannot be served."""

from django.test import TestCase
from django.urls import reverse

from auctions.tests.factories import create_bidder, create_seller
from escrow.services import hold_payment
from escrow.tests.factories import create_closed_auction


class NotFoundPageTests(TestCase):
    def test_an_address_that_does_not_exist_gets_the_page(self):
        response = self.client.get("/esto-no-existe/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Esta página no existe", status_code=404)

    def test_an_auction_that_does_not_exist_gets_the_page(self):
        response = self.client.get(reverse("auctions:auction_detail", args=[9999]))

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")

    def test_it_offers_the_way_back(self):
        response = self.client.get("/esto-no-existe/")

        self.assertContains(response, reverse("auctions:catalogue"), status_code=404)


class ForbiddenPageTests(TestCase):
    def setUp(self):
        self.transaction = hold_payment(
            create_closed_auction(seller=create_seller(), bidder=create_bidder())
        )

    def test_somebody_outside_a_sale_gets_the_page(self):
        self.client.force_login(create_bidder())

        response = self.client.get(
            reverse("escrow:transaction_detail", args=[self.transaction.pk])
        )

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")
        self.assertContains(response, "No puedes ver esto", status_code=403)

    def test_it_explains_why_instead_of_showing_a_traceback(self):
        """UR04: the message names the cause, it does not dump Python at the visitor."""
        self.client.force_login(create_bidder())

        response = self.client.get(
            reverse("escrow:transaction_detail", args=[self.transaction.pk])
        )

        self.assertContains(response, "su comprador y su vendedor", status_code=403)
        self.assertNotContains(response, "Traceback", status_code=403)
