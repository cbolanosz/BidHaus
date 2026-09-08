"""Tests of the email the seller receives when their auction closes (FR10)."""

from datetime import timedelta
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from auctions.models import Auction
from auctions.services import close_auction, close_expired_auctions
from auctions.tests.factories import create_auction, create_bid, create_bidder
from auctions.tests.mailbox import NotificationTestCase, email_to, emails_to


def expire(auction, minutes_ago=1):
    """Push the closing date of an auction into the past, bypassing validation."""
    Auction.objects.filter(pk=auction.pk).update(
        closing_date=timezone.now() - timedelta(minutes=minutes_ago)
    )
    auction.refresh_from_db()
    return auction


class SellerNotificationTests(NotificationTestCase):
    def setUp(self):
        self.auction = create_auction()
        self.seller = self.auction.seller
        self.winner = create_bidder("Laura Gómez")

    def close_with_a_winner(self):
        """Close the auction after a bid from the winner."""
        create_bid(self.auction, "500000", self.winner)
        self.deliver(lambda: close_auction(self.auction))

    def test_notifies_the_seller(self):
        self.close_with_a_winner()

        self.assertIsNotNone(email_to(self.seller.email))

    def test_the_seller_is_told_which_auction_closed(self):
        self.close_with_a_winner()

        message = email_to(self.seller.email)
        self.assertIn("Cerró tu subasta", message.subject)
        self.assertIn(self.auction.title, message.subject)

    def test_the_seller_is_told_who_won_and_with_how_much(self):
        self.close_with_a_winner()

        body = email_to(self.seller.email).body
        self.assertIn("Laura Gómez", body)
        self.assertIn("500.000", body)

    def test_the_seller_receives_a_link_to_the_auction(self):
        self.close_with_a_winner()

        self.assertIn(
            f"http://127.0.0.1:8000/auctions/{self.auction.pk}/",
            email_to(self.seller.email).body,
        )

    def test_an_auction_nobody_bid_on_still_notifies_the_seller(self):
        self.deliver(lambda: close_auction(self.auction))

        self.assertIsNotNone(email_to(self.seller.email))

    def test_the_seller_of_an_auction_nobody_bid_on_is_told_so(self):
        self.deliver(lambda: close_auction(self.auction))

        self.assertIn("sin pujas", email_to(self.seller.email).body)

    def test_a_closing_with_a_winner_writes_to_the_winner_and_the_seller_only(self):
        self.close_with_a_winner()

        self.assertEqual(
            sorted(message.to[0] for message in mail.outbox),
            sorted([self.seller.email, self.winner.email]),
        )

    def test_closing_an_auction_twice_notifies_the_seller_only_once(self):
        self.close_with_a_winner()

        self.deliver(lambda: close_auction(self.auction))

        self.assertEqual(len(emails_to(self.seller.email)), 1)

    def test_an_auction_that_has_not_expired_notifies_nobody(self):
        create_bid(self.auction, "500000", self.winner)

        self.deliver(close_expired_auctions)

        self.assertIsNone(email_to(self.seller.email))


class SellerNotificationOnEveryClosingPathTests(NotificationTestCase):
    """The seller hears about it however the auction was closed (FR07 closes it three ways)."""

    def setUp(self):
        self.auction = create_auction()
        create_bid(self.auction, "500000")
        expire(self.auction)

    def test_the_batch_closing_notifies_the_seller(self):
        self.deliver(close_expired_auctions)

        self.assertIsNotNone(email_to(self.auction.seller.email))

    def test_the_close_auctions_command_notifies_the_seller(self):
        self.deliver(lambda: call_command("close_auctions", stdout=StringIO()))

        self.assertIsNotNone(email_to(self.auction.seller.email))

    def test_closing_the_auction_by_opening_its_page_notifies_the_seller(self):
        self.deliver(
            lambda: self.client.get(
                reverse("auctions:auction_detail", args=[self.auction.pk])
            )
        )

        self.assertIsNotNone(email_to(self.auction.seller.email))
