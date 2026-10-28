"""Tests of the dispute a buyer opens over a retained payment (FR17)."""

from django.db import IntegrityError, transaction
from django.test import TestCase

from auctions.tests.factories import create_bidder, create_seller
from escrow.exceptions import NotTheBuyer, TransactionIsNotHeld
from escrow.models import Dispute, EscrowTransaction
from escrow.services import (
    confirm_reception,
    find_dispute,
    hold_payment,
    list_state_changes,
    open_dispute,
)
from escrow.tests.factories import create_closed_auction

COMPLAINT = "La cámara llegó con el obturador trabado y la publicación decía que funcionaba."


class OpenDisputeTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.auction = create_closed_auction(bidder=self.buyer)
        self.transaction = hold_payment(self.auction)

    def test_registers_the_claim_of_the_buyer(self):
        dispute = open_dispute(self.transaction, self.buyer, COMPLAINT)

        self.assertEqual(dispute.transaction, self.transaction)
        self.assertEqual(dispute.opened_by, self.buyer)
        self.assertEqual(dispute.description, COMPLAINT)
        self.assertTrue(dispute.is_open)

    def test_leaves_the_money_in_dispute(self):
        open_dispute(self.transaction, self.buyer, COMPLAINT)

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, EscrowTransaction.State.IN_DISPUTE)

    def test_writes_the_transition_to_the_history(self):
        open_dispute(self.transaction, self.buyer, COMPLAINT)

        last_change = list_state_changes(self.transaction).last()
        self.assertEqual(last_change.previous_state, EscrowTransaction.State.HELD)
        self.assertEqual(last_change.new_state, EscrowTransaction.State.IN_DISPUTE)
        self.assertEqual(last_change.actor, self.buyer)

    def test_refuses_anyone_who_is_not_the_buyer(self):
        with self.assertRaises(NotTheBuyer):
            open_dispute(self.transaction, self.auction.seller, COMPLAINT)

        self.assertEqual(Dispute.objects.count(), 0)

    def test_refuses_a_second_dispute_over_the_same_payment(self):
        """The first dispute leaves the money no longer held, which closes the door."""
        open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.transaction.refresh_from_db()

        with self.assertRaises(TransactionIsNotHeld):
            open_dispute(self.transaction, self.buyer, "Otra queja distinta.")

        self.assertEqual(Dispute.objects.count(), 1)

    def test_the_database_itself_refuses_two_disputes_on_one_payment(self):
        """DBR07 rests on the column, not on a service somebody could bypass."""
        open_dispute(self.transaction, self.buyer, COMPLAINT)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Dispute.objects.create(
                    transaction=self.transaction,
                    opened_by=self.buyer,
                    description="Otra queja distinta.",
                )

    def test_refuses_a_payment_that_already_reached_the_seller(self):
        """Once the money is gone there is nothing left for BidHaus to hold back."""
        confirm_reception(self.transaction, self.buyer)

        with self.assertRaises(TransactionIsNotHeld):
            open_dispute(self.transaction, self.buyer, COMPLAINT)

    def test_the_funds_can_no_longer_be_released_while_it_is_open(self):
        open_dispute(self.transaction, self.buyer, COMPLAINT)
        self.transaction.refresh_from_db()

        with self.assertRaises(TransactionIsNotHeld):
            confirm_reception(self.transaction, self.buyer)

    def test_finds_the_dispute_of_a_transaction(self):
        dispute = open_dispute(self.transaction, self.buyer, COMPLAINT)

        self.assertEqual(find_dispute(self.transaction), dispute)

    def test_finds_nothing_for_a_payment_nobody_argued(self):
        self.assertIsNone(find_dispute(self.transaction))

    def test_a_dispute_of_one_sale_does_not_touch_another(self):
        other = hold_payment(create_closed_auction(bidder=self.buyer, seller=create_seller()))
        open_dispute(self.transaction, self.buyer, COMPLAINT)

        other.refresh_from_db()
        self.assertEqual(other.state, EscrowTransaction.State.HELD)
