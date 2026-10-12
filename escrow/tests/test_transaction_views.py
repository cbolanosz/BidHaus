"""Tests of the page where a buyer confirms the reception (FR15, UR03)."""

from django.test import TestCase
from django.urls import reverse

from accounts.tests.factories import create_administrator
from auctions.tests.factories import create_bidder, create_seller
from escrow.models import EscrowTransaction
from escrow.services import hold_payment
from escrow.tests.factories import create_closed_auction


class TransactionDetailViewTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.seller = create_seller()
        self.transaction = hold_payment(
            create_closed_auction(seller=self.seller, bidder=self.buyer)
        )
        self.url = reverse("escrow:transaction_detail", args=[self.transaction.pk])

    def test_sends_a_visitor_who_is_not_logged_in_to_the_login_page(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")

    def test_shows_the_state_of_the_money_to_the_buyer(self):
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "escrow/transaction_detail.html")
        self.assertContains(response, "Retenido")

    def test_shows_it_to_the_seller_too(self):
        self.client.force_login(self.seller)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_shows_it_to_an_administrator(self):
        self.client.force_login(create_administrator())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_refuses_anybody_else(self):
        self.client.force_login(create_bidder())

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_answers_not_found_for_a_transaction_that_does_not_exist(self):
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("escrow:transaction_detail", args=[9999]))

        self.assertEqual(response.status_code, 404)

    def test_offers_the_button_only_to_the_buyer(self):
        self.client.force_login(self.buyer)
        self.assertContains(self.client.get(self.url), "Confirmar que lo recibí")

        self.client.force_login(self.seller)
        self.assertNotContains(self.client.get(self.url), "Confirmar que lo recibí")

    def test_hides_the_button_once_the_money_was_released(self):
        self.client.force_login(self.buyer)
        self.client.post(
            reverse("escrow:transaction_confirm_reception", args=[self.transaction.pk])
        )

        self.assertNotContains(self.client.get(self.url), "Confirmar que lo recibí")

    def test_shows_the_history_of_the_payment(self):
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertContains(response, "automático")


class ConfirmReceptionViewTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder()
        self.seller = create_seller()
        self.transaction = hold_payment(
            create_closed_auction(seller=self.seller, bidder=self.buyer)
        )
        self.url = reverse(
            "escrow:transaction_confirm_reception", args=[self.transaction.pk]
        )

    def test_releases_the_money_and_says_so(self):
        self.client.force_login(self.buyer)

        response = self.client.post(self.url, follow=True)

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, EscrowTransaction.State.RELEASED)
        self.assertContains(response, "El pago se liberó")

    def test_refuses_the_seller(self):
        self.client.force_login(self.seller)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)
        self.transaction.refresh_from_db()
        self.assertTrue(self.transaction.is_held)

    def test_refuses_a_get(self):
        """Confirming releases money, so no address a browser follows may do it."""
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)
        self.transaction.refresh_from_db()
        self.assertTrue(self.transaction.is_held)

    def test_warns_instead_of_failing_when_it_was_already_confirmed(self):
        self.client.force_login(self.buyer)
        self.client.post(self.url)

        response = self.client.post(self.url, follow=True)

        self.assertContains(response, "ya no está retenido")


class AuctionDetailOffersThePaymentTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder()
        self.seller = create_seller()
        self.auction = create_closed_auction(seller=self.seller, bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.url = reverse("auctions:auction_detail", args=[self.auction.pk])

    def test_the_buyer_is_offered_the_link(self):
        self.client.force_login(self.buyer)

        self.assertContains(self.client.get(self.url), "Ver el pago en custodia")

    def test_the_seller_is_offered_the_link(self):
        self.client.force_login(self.seller)

        self.assertContains(self.client.get(self.url), "Ver el pago en custodia")

    def test_nobody_else_is(self):
        self.client.force_login(create_bidder())

        self.assertNotContains(self.client.get(self.url), "Ver el pago en custodia")

    def test_a_visitor_who_is_not_logged_in_is_not(self):
        self.assertNotContains(self.client.get(self.url), "Ver el pago en custodia")


class HeaderOffersThePendingPaymentsTests(TestCase):
    """A closed auction leaves the catalogue, so the header is the way back."""

    def setUp(self):
        self.buyer = create_bidder()
        self.seller = create_seller()
        self.transaction = hold_payment(
            create_closed_auction(seller=self.seller, bidder=self.buyer)
        )
        self.catalogue = reverse("auctions:catalogue")

    def test_offers_the_buyer_the_payment_they_owe_a_confirmation(self):
        self.client.force_login(self.buyer)

        response = self.client.get(self.catalogue)

        self.assertContains(response, "1 pago por confirmar")
        self.assertContains(
            response,
            reverse("escrow:transaction_detail", args=[self.transaction.pk]),
        )

    def test_counts_every_payment_still_waiting(self):
        hold_payment(create_closed_auction(bidder=self.buyer))
        self.client.force_login(self.buyer)

        response = self.client.get(self.catalogue)

        self.assertContains(response, "2 pagos por confirmar")

    def test_offers_nothing_to_the_seller(self):
        self.client.force_login(self.seller)

        self.assertNotContains(self.client.get(self.catalogue), "por confirmar")

    def test_offers_nothing_once_the_buyer_confirmed(self):
        self.client.force_login(self.buyer)
        self.client.post(
            reverse("escrow:transaction_confirm_reception", args=[self.transaction.pk])
        )

        self.assertNotContains(self.client.get(self.catalogue), "por confirmar")

    def test_offers_nothing_to_a_visitor_who_is_not_logged_in(self):
        self.assertNotContains(self.client.get(self.catalogue), "por confirmar")
