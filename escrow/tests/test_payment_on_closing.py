"""Tests that closing an auction is what retains the payment (FR07, FR08, FR14)."""

from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from auctions.models import Auction
from auctions.services import close_auction, close_expired_auctions
from auctions.tests.factories import create_auction, create_bid, create_bidder
from auctions.tests.mailbox import NotificationTestCase
from escrow.models import EscrowTransaction


def expired_auction_with_a_bid(amount="500000", bidder=None):
    """An auction whose closing date has already passed, with one bid on it."""
    auction = create_auction()
    create_bid(auction, amount, bidder or create_bidder())
    Auction.objects.filter(pk=auction.pk).update(
        closing_date=timezone.now() - timezone.timedelta(minutes=1)
    )
    auction.refresh_from_db()
    return auction


class PaymentOnClosingTests(NotificationTestCase):
    def test_closing_an_auction_retains_the_payment(self):
        auction = expired_auction_with_a_bid("500000")

        self.deliver(lambda: close_auction(auction))

        escrow_transaction = EscrowTransaction.objects.get(auction=auction)
        self.assertEqual(escrow_transaction.amount, Decimal("500000.00"))
        self.assertEqual(escrow_transaction.state, EscrowTransaction.State.HELD)

    def test_the_buyer_is_the_winning_bidder(self):
        winner = create_bidder("Laura Gómez")
        auction = expired_auction_with_a_bid("500000", winner)

        self.deliver(lambda: close_auction(auction))

        self.assertEqual(EscrowTransaction.objects.get(auction=auction).buyer, winner)

    def test_an_auction_nobody_bid_on_retains_nothing(self):
        auction = create_auction()
        Auction.objects.filter(pk=auction.pk).update(
            closing_date=timezone.now() - timezone.timedelta(minutes=1)
        )
        auction.refresh_from_db()

        self.deliver(lambda: close_auction(auction))

        self.assertEqual(EscrowTransaction.objects.count(), 0)

    def test_closing_twice_retains_the_payment_only_once(self):
        """The command runs on a schedule, so running it again must change nothing."""
        auction = expired_auction_with_a_bid()

        self.deliver(lambda: close_auction(auction))
        self.deliver(lambda: close_auction(auction))

        self.assertEqual(EscrowTransaction.objects.count(), 1)

    def test_an_auction_that_has_not_expired_retains_nothing(self):
        auction = create_auction()
        create_bid(auction, "500000")

        self.deliver(close_expired_auctions)

        self.assertEqual(EscrowTransaction.objects.count(), 0)

    def test_the_batch_closing_retains_the_payment(self):
        expired_auction_with_a_bid()

        self.deliver(close_expired_auctions)

        self.assertEqual(EscrowTransaction.objects.count(), 1)

    def test_the_close_auctions_command_retains_the_payment(self):
        expired_auction_with_a_bid()

        self.deliver(lambda: call_command("close_auctions", verbosity=0))

        self.assertEqual(EscrowTransaction.objects.count(), 1)

    def test_opening_the_detail_of_an_expired_auction_retains_the_payment(self):
        """The lazy close covers what happens between two runs of the command."""
        auction = expired_auction_with_a_bid()

        self.deliver(
            lambda: self.client.get(reverse("auctions:auction_detail", args=[auction.pk]))
        )

        self.assertEqual(EscrowTransaction.objects.count(), 1)
