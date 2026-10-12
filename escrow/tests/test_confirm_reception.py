"""Tests of the buyer confirming that the item arrived (FR15)."""

from django.test import TestCase

from auctions.tests.factories import create_bidder, create_seller
from escrow.exceptions import NotAParticipant, NotTheBuyer, TransactionIsNotHeld
from escrow.models import EscrowTransaction
from escrow.services import (
    assert_may_read,
    confirm_reception,
    hold_payment,
    list_state_changes,
)
from escrow.tests.factories import create_closed_auction


def retained_payment(seller=None, bidder=None):
    """A closed auction whose payment is already in escrow."""
    return hold_payment(create_closed_auction(seller=seller, bidder=bidder))


class ConfirmReceptionTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.seller = create_seller()
        self.transaction = retained_payment(seller=self.seller, bidder=self.buyer)

    def test_releases_the_money_towards_the_seller(self):
        confirm_reception(self.transaction, self.buyer)

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.state, EscrowTransaction.State.RELEASED)
        self.assertFalse(self.transaction.is_held)

    def test_records_who_confirmed_and_what_changed(self):
        confirm_reception(self.transaction, self.buyer)

        last_change = list(list_state_changes(self.transaction))[-1]
        self.assertEqual(last_change.previous_state, EscrowTransaction.State.HELD)
        self.assertEqual(last_change.new_state, EscrowTransaction.State.RELEASED)
        self.assertEqual(last_change.actor, self.buyer)

    def test_keeps_the_entry_that_retained_the_money(self):
        """DBR06 is append-only: confirming adds a line, it does not replace one."""
        confirm_reception(self.transaction, self.buyer)

        self.assertEqual(self.transaction.state_changes.count(), 2)

    def test_refuses_the_seller(self):
        with self.assertRaises(NotTheBuyer):
            confirm_reception(self.transaction, self.seller)

        self.transaction.refresh_from_db()
        self.assertTrue(self.transaction.is_held)

    def test_refuses_somebody_unrelated_to_the_sale(self):
        with self.assertRaises(NotTheBuyer):
            confirm_reception(self.transaction, create_bidder())

    def test_refuses_to_confirm_twice(self):
        confirm_reception(self.transaction, self.buyer)

        with self.assertRaises(TransactionIsNotHeld):
            confirm_reception(self.transaction, self.buyer)

        self.assertEqual(self.transaction.state_changes.count(), 2)

    def test_leaves_the_money_retained_when_it_refuses(self):
        with self.assertRaises(NotTheBuyer):
            confirm_reception(self.transaction, self.seller)

        self.assertEqual(self.transaction.state_changes.count(), 1)


class WhoMayReadATransactionTests(TestCase):
    """Money is not public the way the catalogue is."""

    def setUp(self):
        self.buyer = create_bidder()
        self.seller = create_seller()
        self.transaction = retained_payment(seller=self.seller, bidder=self.buyer)

    def test_the_buyer_may_read_it(self):
        assert_may_read(self.transaction, self.buyer)

    def test_the_seller_may_read_it(self):
        assert_may_read(self.transaction, self.seller)

    def test_an_administrator_may_read_it(self):
        from accounts.tests.factories import create_administrator

        assert_may_read(self.transaction, create_administrator())

    def test_anybody_else_may_not(self):
        with self.assertRaises(NotAParticipant):
            assert_may_read(self.transaction, create_bidder())
