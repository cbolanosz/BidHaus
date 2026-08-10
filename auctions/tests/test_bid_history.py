"""Tests of the bid history and of the immutability of a bid (FR04, DBR04)."""

from decimal import Decimal

from django.test import TestCase

from auctions.exceptions import BidIsImmutable
from auctions.models import Bid
from auctions.services import list_bids
from auctions.tests.factories import create_auction, create_bid


class BidHistoryTests(TestCase):
    def setUp(self):
        self.auction = create_auction()

    def test_orders_the_history_from_the_highest_amount_to_the_lowest(self):
        create_bid(self.auction, "300000")
        create_bid(self.auction, "500000")
        create_bid(self.auction, "400000")

        amounts = [bid.amount for bid in list_bids(self.auction)]

        self.assertEqual(
            amounts, [Decimal("500000"), Decimal("400000"), Decimal("300000")]
        )

    def test_leaves_out_the_bids_of_other_auctions(self):
        create_bid(self.auction, "300000")
        create_bid(create_auction(title="Otra subasta"), "900000")

        self.assertEqual(list_bids(self.auction).count(), 1)

    def test_is_empty_while_nobody_has_bid(self):
        self.assertEqual(list_bids(self.auction).count(), 0)

    def test_a_registered_bid_cannot_be_modified(self):
        bid = create_bid(self.auction, "300000")

        bid.amount = Decimal("1")
        with self.assertRaises(BidIsImmutable):
            bid.save()

        self.assertEqual(Bid.objects.get(pk=bid.pk).amount, Decimal("300000"))

    def test_a_registered_bid_cannot_be_modified_in_bulk(self):
        bid = create_bid(self.auction, "300000")

        with self.assertRaises(BidIsImmutable):
            Bid.objects.filter(pk=bid.pk).update(amount=Decimal("1"))

        self.assertEqual(Bid.objects.get(pk=bid.pk).amount, Decimal("300000"))

    def test_a_registered_bid_cannot_be_deleted_in_bulk(self):
        create_bid(self.auction, "300000")

        with self.assertRaises(BidIsImmutable):
            Bid.objects.all().delete()

        self.assertEqual(Bid.objects.count(), 1)

    def test_a_registered_bid_cannot_be_deleted(self):
        bid = create_bid(self.auction, "300000")

        with self.assertRaises(BidIsImmutable):
            bid.delete()

        self.assertEqual(Bid.objects.count(), 1)
