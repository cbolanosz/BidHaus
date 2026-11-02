"""Tests of how an administrator settles a dispute (FR19)."""

from decimal import Decimal

from django.test import TestCase

from accounts.tests.factories import create_administrator
from auctions.tests.factories import create_bidder
from escrow.commission import calculate_commission
from escrow.exceptions import (
    DisputeIsResolved,
    NotAnAdministrator,
    TransactionIsNotHeld,
    UnknownOutcome,
)
from escrow.models import Dispute, EscrowTransaction
from escrow.services import (
    confirm_reception,
    hold_payment,
    list_open_disputes,
    list_state_changes,
    open_dispute,
    refund_buyer,
    resolve_dispute,
)
from escrow.tests.factories import create_closed_auction

COMPLAINT = "La cámara llegó con el obturador trabado."
VERDICT = "Las fotografías muestran el daño y el vendedor no respondió."
RELEASED = EscrowTransaction.State.RELEASED
REFUNDED = EscrowTransaction.State.REFUNDED


class ResolveDisputeTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.auction = create_closed_auction(amount="400000", bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.dispute = open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.administrator = create_administrator()

    def resolve(self, outcome):
        return resolve_dispute(self.dispute, self.administrator, outcome, VERDICT)

    def test_closes_the_dispute_with_its_reason(self):
        dispute = self.resolve(RELEASED)

        self.assertFalse(dispute.is_open)
        self.assertEqual(dispute.resolution, VERDICT)

    def test_in_favour_of_the_seller_releases_the_money(self):
        self.resolve(RELEASED)

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, RELEASED)

    def test_in_favour_of_the_seller_charges_the_commission(self):
        self.resolve(RELEASED)

        self.transaction.refresh_from_db()
        self.assertEqual(
            self.transaction.commission, calculate_commission(Decimal("400000"))
        )

    def test_in_favour_of_the_buyer_refunds_the_whole_amount(self):
        self.resolve(REFUNDED)

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, REFUNDED)
        self.assertEqual(self.transaction.commission, Decimal("0.00"))
        self.assertEqual(self.transaction.payout, self.transaction.amount)

    def test_writes_the_transition_with_the_administrator_as_its_actor(self):
        self.resolve(REFUNDED)

        last_change = list_state_changes(self.transaction).last()
        self.assertEqual(last_change.previous_state, EscrowTransaction.State.IN_DISPUTE)
        self.assertEqual(last_change.new_state, REFUNDED)
        self.assertEqual(last_change.actor, self.administrator)

    def test_refuses_anyone_who_is_not_an_administrator(self):
        for impostor in (self.buyer, self.auction.seller):
            with self.assertRaises(NotAnAdministrator):
                resolve_dispute(self.dispute, impostor, RELEASED, VERDICT)

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, EscrowTransaction.State.IN_DISPUTE)

    def test_refuses_to_resolve_the_same_dispute_twice(self):
        self.resolve(RELEASED)

        with self.assertRaises(DisputeIsResolved):
            resolve_dispute(self.dispute, self.administrator, REFUNDED, "Me arrepentí.")

    def test_refuses_an_outcome_that_is_not_one_of_the_two(self):
        with self.assertRaises(UnknownOutcome):
            resolve_dispute(self.dispute, self.administrator, "held", VERDICT)

    def test_lists_the_disputes_waiting_for_a_decision(self):
        self.assertEqual(list(list_open_disputes()), [self.dispute])

        self.resolve(RELEASED)

        self.assertEqual(list(list_open_disputes()), [])


class RefundBuyerTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder()
        self.auction = create_closed_auction(amount="400000", bidder=self.buyer)
        self.transaction = hold_payment(self.auction)
        self.administrator = create_administrator()

    def test_refuses_a_sale_whose_money_already_moved(self):
        confirm_reception(self.transaction, self.buyer)

        with self.assertRaises(TransactionIsNotHeld):
            refund_buyer(self.transaction, self.administrator)

    def test_a_refunded_sale_cannot_be_refunded_again(self):
        refund_buyer(self.transaction, self.administrator)
        self.transaction.refresh_from_db()

        with self.assertRaises(TransactionIsNotHeld):
            refund_buyer(self.transaction, self.administrator)


class WhatConfirmingStillRefusesTests(TestCase):
    """Resolving a dispute releases money, but the buyer still cannot while it lasts."""

    def setUp(self):
        self.buyer = create_bidder()
        self.transaction = hold_payment(create_closed_auction(bidder=self.buyer))
        open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.transaction.refresh_from_db()

    def test_the_buyer_cannot_confirm_reception_while_it_is_argued(self):
        with self.assertRaises(TransactionIsNotHeld):
            confirm_reception(self.transaction, self.buyer)

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, EscrowTransaction.State.IN_DISPUTE)
