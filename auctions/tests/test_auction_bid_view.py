"""Tests of the bid form on the detail page (FR05)."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from auctions.models import Auction, Bid
from auctions.tests.factories import create_auction, create_bidder, create_seller


class AuctionBidViewTests(TestCase):
    def setUp(self):
        self.seller = create_seller()
        self.auction = create_auction(seller=self.seller, current_price=Decimal("250000.00"))
        self.bidder = create_bidder("Laura Gómez")
        self.url = reverse("auctions:auction_bid", args=[self.auction.pk])
        self.detail_url = reverse("auctions:auction_detail", args=[self.auction.pk])
        self.client.force_login(self.bidder)

    def post(self, **overrides):
        payload = {"amount": "300000"}
        payload.update(overrides)
        return self.client.post(self.url, payload)

    def test_the_detail_page_offers_the_bid_form(self):
        response = self.client.get(self.detail_url)

        self.assertContains(response, "Tu puja (COP)")

    def test_registers_the_bid_and_returns_to_the_auction(self):
        response = self.post()

        self.assertRedirects(response, self.detail_url)
        self.assertEqual(Bid.objects.count(), 1)

    def test_shows_the_new_bid_in_the_history(self):
        self.post()

        response = self.client.get(self.detail_url)

        self.assertContains(response, "300.000")
        self.assertContains(response, "Laura Gómez")

    def test_reports_an_amount_that_does_not_beat_the_current_price(self):
        response = self.post(amount="100000")

        self.assertEqual(Bid.objects.count(), 0)
        self.assertContains(response, "Tu puja debe superar el precio actual")

    def test_reports_a_closed_auction(self):
        Auction.objects.filter(pk=self.auction.pk).update(state=Auction.State.CLOSED)

        response = self.post()

        self.assertEqual(Bid.objects.count(), 0)
        self.assertContains(response, "ya está cerrada")

    def test_registers_the_bid_in_the_name_of_the_user_in_session(self):
        self.post()

        self.assertEqual(Bid.objects.get().bidder, self.bidder)

    def test_sends_a_visitor_who_is_not_logged_in_to_the_login_page(self):
        self.client.logout()

        response = self.post()

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")
        self.assertEqual(Bid.objects.count(), 0)

    def test_invites_a_visitor_who_is_not_logged_in_to_sign_in(self):
        self.client.logout()

        response = self.client.get(self.detail_url)

        self.assertContains(response, "Inicia sesión para pujar")
        self.assertNotContains(response, "Tu puja (COP)")

    def test_refuses_a_user_whose_role_is_not_bidder(self):
        self.client.force_login(self.seller)

        response = self.post()

        self.assertEqual(Bid.objects.count(), 0)
        self.assertContains(response, "no tiene el rol de comprador")

    def test_refuses_the_owner_of_the_auction(self):
        own_auction = create_auction(seller=self.bidder)

        response = self.client.post(
            reverse("auctions:auction_bid", args=[own_auction.pk]), {"amount": "300000"}
        )

        self.assertEqual(Bid.objects.count(), 0)
        self.assertContains(response, "no puede pujar en su propia subasta")

    def test_hides_the_bid_form_on_an_auction_that_is_not_open(self):
        Auction.objects.filter(pk=self.auction.pk).update(state=Auction.State.CLOSED)

        response = self.client.get(self.detail_url)

        self.assertNotContains(response, "Tu puja (COP)")

    def test_ignores_a_visit_to_the_bid_url_without_a_bid(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, self.detail_url)

    def test_answers_not_found_for_an_auction_that_does_not_exist(self):
        response = self.client.post(reverse("auctions:auction_bid", args=[9999]), {})

        self.assertEqual(response.status_code, 404)

    def test_reports_an_auction_whose_closing_date_already_passed(self):
        Auction.objects.filter(pk=self.auction.pk).update(
            closing_date=timezone.now() - timedelta(minutes=1)
        )

        response = self.post()

        self.assertEqual(Bid.objects.count(), 0)
        self.assertContains(response, "ya está cerrada")
