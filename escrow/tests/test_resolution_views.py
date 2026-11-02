"""Tests of the pages where an administrator settles a dispute (FR19)."""

import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.tests.factories import create_administrator
from auctions.tests.factories import create_bidder
from escrow.models import Dispute, EscrowTransaction
from escrow.services import (
    attach_evidence,
    hold_payment,
    open_dispute,
    resolve_dispute,
)
from escrow.tests.factories import build_evidence, create_closed_auction

COMPLAINT = "La cámara llegó con el obturador trabado."
VERDICT = "Las fotografías muestran el daño y el vendedor no respondió."
RELEASED = EscrowTransaction.State.RELEASED
REFUNDED = EscrowTransaction.State.REFUNDED


@override_settings(DISPUTE_EVIDENCE_ROOT=tempfile.mkdtemp())
class DisputeQueueTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.auction = create_closed_auction(bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.dispute = open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.administrator = create_administrator()
        self.url = reverse("escrow:dispute_queue")

    def test_lists_what_is_waiting_for_a_decision(self):
        self.client.force_login(self.administrator)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.auction.title)
        self.assertContains(
            response, reverse("escrow:dispute_resolve", args=[self.dispute.pk])
        )

    def test_says_so_when_there_is_nothing_waiting(self):
        resolve_dispute(self.dispute, self.administrator, RELEASED, VERDICT)
        self.client.force_login(self.administrator)

        response = self.client.get(self.url)

        self.assertContains(response, "Nada pendiente")

    def test_closes_the_queue_to_the_buyer_and_to_the_seller(self):
        for user in (self.buyer, self.auction.seller):
            self.client.force_login(user)

            self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_sends_a_visitor_who_is_not_logged_in_to_the_login_page(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")

    def test_the_header_offers_it_to_an_administrator(self):
        self.client.force_login(self.administrator)

        response = self.client.get(reverse("auctions:catalogue"))

        # The whole href, because the buyer's own cell starts with this address.
        self.assertContains(response, f'href="{self.url}"')

    def test_the_header_does_not_offer_it_to_anybody_else(self):
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("auctions:catalogue"))

        self.assertNotContains(response, f'href="{self.url}"')


@override_settings(DISPUTE_EVIDENCE_ROOT=tempfile.mkdtemp())
class ResolveDisputeViewTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.auction = create_closed_auction(amount="400000", bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.dispute = open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.evidence = attach_evidence(self.dispute, self.buyer, [build_evidence()])[0]
        self.administrator = create_administrator()
        self.url = reverse("escrow:dispute_resolve", args=[self.dispute.pk])
        self.client.force_login(self.administrator)

    def test_shows_the_claim_and_its_evidence_before_deciding(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, COMPLAINT)
        self.assertContains(
            response, reverse("escrow:evidence_file", args=[self.evidence.pk])
        )

    def test_resolving_for_the_seller_releases_and_returns_to_the_payment(self):
        response = self.client.post(
            self.url, {"outcome": RELEASED, "resolution": VERDICT}
        )

        self.assertRedirects(
            response,
            reverse("escrow:transaction_detail", args=[self.transaction.pk]),
        )
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, RELEASED)

    def test_resolving_for_the_buyer_refunds(self):
        self.client.post(self.url, {"outcome": REFUNDED, "resolution": VERDICT})

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, REFUNDED)

    def test_refuses_a_decision_with_no_reason(self):
        response = self.client.post(self.url, {"outcome": RELEASED, "resolution": "  "})

        self.assertEqual(response.status_code, 200)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, EscrowTransaction.State.IN_DISPUTE)

    def test_refuses_a_decision_with_no_outcome(self):
        response = self.client.post(self.url, {"resolution": VERDICT})

        self.assertContains(response, "Elige a favor de quién se resuelve.")

    def test_closes_the_page_to_the_buyer_and_to_the_seller(self):
        for user in (self.buyer, self.auction.seller):
            self.client.force_login(user)

            self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_answers_404_for_a_dispute_that_does_not_exist(self):
        response = self.client.get(reverse("escrow:dispute_resolve", args=[9999]))

        self.assertEqual(response.status_code, 404)

    def test_says_so_when_it_was_already_resolved(self):
        resolve_dispute(self.dispute, self.administrator, RELEASED, VERDICT)

        response = self.client.get(self.url)

        self.assertContains(response, "Ya resuelta")
        self.assertContains(response, VERDICT)


@override_settings(DISPUTE_EVIDENCE_ROOT=tempfile.mkdtemp())
class WhatThePaymentPageShowsAfterwardsTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.auction = create_closed_auction(amount="400000", bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.dispute = open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.administrator = create_administrator()
        self.url = reverse("escrow:transaction_detail", args=[self.transaction.pk])

    def test_offers_the_administrator_to_resolve_it(self):
        self.client.force_login(self.administrator)

        response = self.client.get(self.url)

        self.assertContains(
            response, reverse("escrow:dispute_resolve", args=[self.dispute.pk])
        )

    def test_does_not_offer_that_to_the_buyer(self):
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertNotContains(
            response, reverse("escrow:dispute_resolve", args=[self.dispute.pk])
        )

    def test_shows_the_decision_to_both_sides(self):
        resolve_dispute(self.dispute, self.administrator, REFUNDED, VERDICT)

        for user in (self.buyer, self.auction.seller):
            self.client.force_login(user)

            self.assertContains(self.client.get(self.url), VERDICT)

    def test_a_refund_reads_as_a_refund_and_not_as_a_payout(self):
        resolve_dispute(self.dispute, self.administrator, REFUNDED, VERDICT)
        self.client.force_login(self.auction.seller)

        response = self.client.get(self.url)

        self.assertContains(response, "Reembolsado al comprador")
        self.assertNotContains(response, "Recibió el vendedor")

    def test_the_buyer_loses_the_header_cell_once_it_is_decided(self):
        resolve_dispute(self.dispute, self.administrator, RELEASED, VERDICT)
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("auctions:catalogue"))

        self.assertNotContains(response, "en disputa")
