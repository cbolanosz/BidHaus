"""Tests of the payment retained when an auction closes (FR14)."""

from decimal import Decimal

from django.test import TestCase

from auctions.models import Auction
from auctions.tests.factories import create_auction, create_bid, create_bidder, create_seller
from escrow.exceptions import (
    AuctionHasNoWinner,
    AuctionIsNotClosed,
    TransactionAlreadyExists,
)
from escrow.models import EscrowTransaction, StateChange
from escrow.services import find_transaction_for_auction, hold_payment, list_state_changes
from escrow.tests.factories import create_closed_auction, create_closed_auction_without_bids


class HoldPaymentTests(TestCase):
    def test_retains_the_amount_of_the_winning_bid(self):
        auction = create_closed_auction(amount="400000")

        escrow_transaction = hold_payment(auction)

        self.assertEqual(escrow_transaction.amount, Decimal("400000.00"))

    def test_the_buyer_is_the_winning_bidder(self):
        winner = create_bidder("Laura Gómez")
        auction = create_closed_auction(bidder=winner)

        escrow_transaction = hold_payment(auction)

        self.assertEqual(escrow_transaction.buyer, winner)

    def test_the_seller_is_the_seller_of_the_auction(self):
        seller = create_seller()
        auction = create_closed_auction(seller=seller)

        escrow_transaction = hold_payment(auction)

        self.assertEqual(escrow_transaction.seller, seller)

    def test_the_money_starts_retained(self):
        escrow_transaction = hold_payment(create_closed_auction())

        self.assertEqual(escrow_transaction.state, EscrowTransaction.State.HELD)
        self.assertTrue(escrow_transaction.is_held)

    def test_no_commission_is_deducted_yet(self):
        """FR20 deducts it when the funds are released, not when they arrive."""
        escrow_transaction = hold_payment(create_closed_auction())

        self.assertEqual(escrow_transaction.commission, Decimal("0.00"))

    def test_records_the_first_entry_of_the_history(self):
        escrow_transaction = hold_payment(create_closed_auction())

        changes = list(list_state_changes(escrow_transaction))
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].previous_state, "")
        self.assertEqual(changes[0].new_state, EscrowTransaction.State.HELD)

    def test_the_first_entry_has_no_actor_because_the_system_made_it(self):
        escrow_transaction = hold_payment(create_closed_auction())

        self.assertIsNone(escrow_transaction.state_changes.first().actor)

    def test_refuses_an_auction_that_is_still_open(self):
        auction = create_auction()
        create_bid(auction, "400000")

        with self.assertRaises(AuctionIsNotClosed):
            hold_payment(auction)

        self.assertEqual(EscrowTransaction.objects.count(), 0)

    def test_refuses_an_auction_that_closed_without_bids(self):
        auction = create_closed_auction_without_bids()

        with self.assertRaises(AuctionHasNoWinner):
            hold_payment(auction)

        self.assertEqual(EscrowTransaction.objects.count(), 0)

    def test_refuses_to_retain_the_same_auction_twice(self):
        auction = create_closed_auction()
        hold_payment(auction)

        with self.assertRaises(TransactionAlreadyExists):
            hold_payment(auction)

        self.assertEqual(EscrowTransaction.objects.count(), 1)

    def test_leaves_nothing_behind_when_it_refuses(self):
        """The transaction and its first entry are written together or not at all."""
        auction = create_closed_auction_without_bids()

        with self.assertRaises(AuctionHasNoWinner):
            hold_payment(auction)

        self.assertEqual(StateChange.objects.count(), 0)

    def test_finds_the_transaction_of_an_auction(self):
        auction = create_closed_auction()
        escrow_transaction = hold_payment(auction)

        self.assertEqual(find_transaction_for_auction(auction), escrow_transaction)

    def test_finds_nothing_for_an_auction_that_has_no_transaction(self):
        self.assertIsNone(find_transaction_for_auction(create_auction()))


class StateChangeIsAppendOnlyTests(TestCase):
    """DBR06: once written, a change is never modified nor deleted."""

    def setUp(self):
        self.escrow_transaction = hold_payment(create_closed_auction())
        self.change = self.escrow_transaction.state_changes.first()

    def test_refuses_to_modify_a_change(self):
        self.change.new_state = EscrowTransaction.State.RELEASED

        with self.assertRaises(Exception):
            self.change.save()

    def test_refuses_to_update_changes_in_bulk(self):
        with self.assertRaises(Exception):
            StateChange.objects.all().update(new_state=EscrowTransaction.State.REFUNDED)

    def test_refuses_to_delete_changes_in_bulk(self):
        with self.assertRaises(Exception):
            StateChange.objects.all().delete()


class AuctionKeepsItsTransactionTests(TestCase):
    def test_an_auction_with_money_retained_cannot_be_deleted(self):
        """PROTECT: deleting the auction would orphan the money it holds."""
        auction = create_closed_auction()
        hold_payment(auction)

        with self.assertRaises(Exception):
            auction.delete()

    def test_an_auction_has_at_most_one_transaction(self):
        auction = create_closed_auction()
        hold_payment(auction)

        self.assertEqual(Auction.objects.get(pk=auction.pk).escrow_transaction.amount,
                         Decimal("400000.00"))
