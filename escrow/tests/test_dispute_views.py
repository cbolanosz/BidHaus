"""Tests of the page where a buyer opens a dispute (FR17)."""

from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import create_administrator
from auctions.tests.factories import create_bidder
from escrow.models import Dispute, EscrowTransaction
from escrow.services import confirm_reception, hold_payment, open_dispute
from escrow.tests.factories import create_closed_auction

COMPLAINT = "La cámara llegó con el obturador trabado y la publicación decía que funcionaba."


class OpenDisputeViewTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.auction = create_closed_auction(bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.url = reverse(
            "escrow:transaction_open_dispute", args=[self.transaction.pk]
        )
        self.client.force_login(self.buyer)

    def test_sends_a_visitor_who_is_not_logged_in_to_the_login_page(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")

    def test_shows_the_form_to_the_buyer(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "escrow/dispute_form.html")
        self.assertContains(response, "Abrir una disputa")

    def test_registers_the_claim_and_returns_to_the_payment(self):
        response = self.client.post(self.url, {"description": COMPLAINT})

        self.assertRedirects(
            response,
            reverse("escrow:transaction_detail", args=[self.transaction.pk]),
        )
        self.assertEqual(Dispute.objects.count(), 1)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, EscrowTransaction.State.IN_DISPUTE)

    def test_refuses_a_claim_with_no_description(self):
        response = self.client.post(self.url, {"description": "   "})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Dispute.objects.count(), 0)

    def test_closes_the_page_to_the_seller(self):
        self.client.force_login(self.auction.seller)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_closes_the_page_to_an_administrator_too(self):
        """Reading the dispute is one thing; opening it belongs to the buyer alone."""
        self.client.force_login(create_administrator())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_answers_404_for_a_payment_that_does_not_exist(self):
        response = self.client.get(
            reverse("escrow:transaction_open_dispute", args=[9999])
        )

        self.assertEqual(response.status_code, 404)

    def test_explains_why_a_released_payment_cannot_be_disputed(self):
        confirm_reception(self.transaction, self.buyer)

        response = self.client.post(self.url, {"description": COMPLAINT})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "mientras el dinero está en custodia")
        self.assertEqual(Dispute.objects.count(), 0)


class WhatThePaymentPageShowsTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.auction = create_closed_auction(bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.url = reverse("escrow:transaction_detail", args=[self.transaction.pk])

    def test_offers_the_dispute_to_the_buyer_while_the_money_is_held(self):
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertContains(
            response,
            reverse("escrow:transaction_open_dispute", args=[self.transaction.pk]),
        )

    def test_does_not_offer_it_to_the_seller(self):
        self.client.force_login(self.auction.seller)

        response = self.client.get(self.url)

        self.assertNotContains(
            response,
            reverse("escrow:transaction_open_dispute", args=[self.transaction.pk]),
        )

    def test_shows_the_claim_to_the_seller_once_it_is_open(self):
        open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.client.force_login(self.auction.seller)

        response = self.client.get(self.url)

        self.assertContains(response, COMPLAINT)
        self.assertContains(response, "Laura Gómez")

    def test_no_longer_offers_to_confirm_once_the_sale_is_argued(self):
        open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertNotContains(response, "Confirmar que lo recibí")
