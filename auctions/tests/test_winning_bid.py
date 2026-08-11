"""Tests of the winning bid of a closed auction (FR08)."""

from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from auctions.models import Auction, Bid
from auctions.services import close_auction, close_expired_auctions
from auctions.tests.factories import create_auction, create_bid, create_bidder


def expire(auction, minutes_ago=1):
    """Push the closing date of an auction into the past, bypassing validation."""
    Auction.objects.filter(pk=auction.pk).update(
        closing_date=timezone.now() - timedelta(minutes=minutes_ago)
    )
    auction.refresh_from_db()
    return auction


class WinningBidTests(TestCase):
    def setUp(self):
        self.auction = create_auction()

    def test_marks_the_highest_bid_as_the_winner(self):
        create_bid(self.auction, "300000")
        highest_bid = create_bid(self.auction, "500000")
        create_bid(self.auction, "400000")

        close_auction(self.auction)

        self.assertEqual(self.auction.winning_bid, highest_bid)

    def test_an_auction_nobody_bid_on_closes_without_a_winner(self):
        close_auction(self.auction)

        self.assertIsNone(self.auction.winning_bid)
        self.assertEqual(self.auction.state, Auction.State.CLOSED)

    def test_on_a_tie_the_earliest_bid_wins(self):
        first_bid = create_bid(self.auction, "500000")
        Bid.objects.create(
            auction=self.auction, bidder=create_bidder(), amount=Decimal("500000")
        )

        close_auction(self.auction)

        self.assertEqual(self.auction.winning_bid, first_bid)

    def test_does_not_change_the_winner_of_an_auction_already_closed(self):
        winning_bid = create_bid(self.auction, "500000")
        close_auction(self.auction)

        close_auction(self.auction)

        self.auction.refresh_from_db()
        self.assertEqual(self.auction.winning_bid, winning_bid)

    def test_the_command_marks_the_winner_of_every_expired_auction(self):
        winning_bid = create_bid(self.auction, "500000")
        expire(self.auction)

        call_command("close_auctions", stdout=None)

        self.auction.refresh_from_db()
        self.assertEqual(self.auction.winning_bid, winning_bid)

    def test_closing_by_batch_marks_the_winner(self):
        winning_bid = create_bid(self.auction, "500000")
        expire(self.auction)

        close_expired_auctions()

        self.auction.refresh_from_db()
        self.assertEqual(self.auction.winning_bid, winning_bid)

    def test_the_winning_bid_stays_in_the_history(self):
        create_bid(self.auction, "300000")
        create_bid(self.auction, "500000")

        close_auction(self.auction)

        self.assertEqual(self.auction.bids.count(), 2)


class WinningBidOnTheDetailPageTests(TestCase):
    def test_announces_the_winner_of_a_closed_auction(self):
        auction = create_auction()
        create_bid(auction, "300000")
        create_bid(auction, "500000", create_bidder("Laura Gómez"))
        expire(auction)

        response = self.client.get(reverse("auctions:auction_detail", args=[auction.pk]))

        self.assertContains(response, "Ganó Laura Gómez")
        self.assertContains(response, "500.000")
        self.assertContains(response, "puja ganadora")

    def test_announces_a_closed_auction_that_had_no_bids(self):
        auction = expire(create_auction())

        response = self.client.get(reverse("auctions:auction_detail", args=[auction.pk]))

        self.assertContains(response, "Cerró sin pujas.")

    def test_an_open_auction_shows_no_winner(self):
        auction = create_auction()
        create_bid(auction, "500000")

        response = self.client.get(reverse("auctions:auction_detail", args=[auction.pk]))

        self.assertNotContains(response, "puja ganadora")
        self.assertContains(response, "puja más alta")
