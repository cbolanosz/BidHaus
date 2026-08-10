"""Tests of the bidding use case (FR05)."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal

from django.db import connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from auctions.exceptions import AuctionClosed, BidTooLow, NotABidder, SellerCannotBid
from auctions.models import Auction, Bid
from auctions.services import place_bid
from auctions.tests.factories import create_auction, create_bidder, create_seller

CONCURRENT_BIDDERS = 20


class PlaceBidTests(TestCase):
    def setUp(self):
        self.seller = create_seller()
        self.auction = create_auction(seller=self.seller, current_price=Decimal("250000.00"))
        self.bidder = create_bidder()

    def bid(self, amount, bidder=None):
        return place_bid(self.auction.pk, bidder or self.bidder, Decimal(amount))

    def test_registers_a_bid_that_beats_the_current_price(self):
        bid = self.bid("300000")

        self.assertEqual(bid.amount, Decimal("300000"))
        self.assertEqual(Bid.objects.count(), 1)

    def test_updates_the_current_price_of_the_auction(self):
        self.bid("300000")

        self.auction.refresh_from_db()
        self.assertEqual(self.auction.current_price, Decimal("300000"))

    def test_rejects_an_amount_equal_to_the_current_price(self):
        with self.assertRaises(BidTooLow):
            self.bid("250000")

        self.assertEqual(Bid.objects.count(), 0)

    def test_rejects_an_amount_below_the_current_price(self):
        with self.assertRaises(BidTooLow):
            self.bid("100000")

        self.assertEqual(Bid.objects.count(), 0)

    def test_reports_the_price_the_bid_had_to_beat(self):
        with self.assertRaises(BidTooLow) as error:
            self.bid("100000")

        self.assertEqual(error.exception.current_price, Decimal("250000.00"))

    def test_compares_against_the_price_left_by_the_previous_bid(self):
        self.bid("300000")

        with self.assertRaises(BidTooLow):
            self.bid("280000", create_bidder())

        self.assertEqual(Bid.objects.count(), 1)

    def test_rejects_the_seller_of_the_auction(self):
        former_seller = self.seller
        former_seller.role = former_seller.Role.BIDDER
        former_seller.save(update_fields=["role"])

        with self.assertRaises(SellerCannotBid):
            self.bid("300000", former_seller)

        self.assertEqual(Bid.objects.count(), 0)

    def test_rejects_a_user_who_is_not_a_registered_bidder(self):
        with self.assertRaises(NotABidder):
            self.bid("300000", create_seller())

        self.assertEqual(Bid.objects.count(), 0)

    def test_rejects_a_bid_on_an_auction_that_is_not_open(self):
        self.auction.state = Auction.State.CLOSED
        self.auction.save(update_fields=["state"])

        with self.assertRaises(AuctionClosed):
            self.bid("300000")

        self.assertEqual(Bid.objects.count(), 0)

    def test_rejects_a_bid_after_the_closing_date(self):
        Auction.objects.filter(pk=self.auction.pk).update(
            closing_date=timezone.now() - timedelta(minutes=1)
        )

        with self.assertRaises(AuctionClosed):
            self.bid("300000")

        self.assertEqual(Bid.objects.count(), 0)

    def test_keeps_the_price_untouched_when_the_bid_is_rejected(self):
        with self.assertRaises(BidTooLow):
            self.bid("100000")

        self.auction.refresh_from_db()
        self.assertEqual(self.auction.current_price, Decimal("250000.00"))

    def test_records_who_bid_and_when(self):
        bid = self.bid("300000")

        self.assertEqual(bid.bidder, self.bidder)
        self.assertIsNotNone(bid.timestamp)


class ConcurrentBidTests(TransactionTestCase):
    """Bids that arrive at the same time (CLAUDE.md 4.1, DBR04).

    TransactionTestCase is needed because each thread opens its own connection
    and must see what the others committed.
    """

    def setUp(self):
        self.auction = create_auction(current_price=Decimal("100000.00"))

    def bid_from_every_bidder_at_once(self):
        """Let CONCURRENT_BIDDERS bid on the same auction from their own threads."""
        bidders = [create_bidder() for _ in range(CONCURRENT_BIDDERS)]

        def bid(index):
            try:
                place_bid(self.auction.pk, bidders[index], Decimal(200000 + index * 1000))
            except BidTooLow:
                return
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=CONCURRENT_BIDDERS) as pool:
            list(pool.map(bid, range(CONCURRENT_BIDDERS)))

    def test_every_registered_bid_beat_the_price_it_found(self):
        self.bid_from_every_bidder_at_once()

        amounts = list(
            self.auction.bids.order_by("timestamp").values_list("amount", flat=True)
        )
        self.assertTrue(all(later > earlier for earlier, later in zip(amounts, amounts[1:])))

    def test_the_current_price_ends_equal_to_the_highest_bid(self):
        self.bid_from_every_bidder_at_once()

        self.auction.refresh_from_db()
        highest_bid = self.auction.bids.order_by("-amount").first()
        self.assertEqual(self.auction.current_price, highest_bid.amount)
