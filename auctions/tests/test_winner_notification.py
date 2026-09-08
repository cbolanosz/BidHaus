"""Tests of the email the winner receives when an auction closes (FR09)."""

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

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


class WinnerNotificationTests(NotificationTestCase):
    def setUp(self):
        self.auction = create_auction()
        self.winner = create_bidder("Laura Gómez")

    def close_with_a_winner(self):
        """Close the auction after two bids, the higher one from the winner."""
        create_bid(self.auction, "300000")
        winning_bid = create_bid(self.auction, "500000", self.winner)
        self.deliver(lambda: close_auction(self.auction))
        return winning_bid

    def test_notifies_the_winner(self):
        self.close_with_a_winner()

        self.assertIsNotNone(email_to(self.winner.email))

    def test_the_winner_is_told_which_auction_they_won(self):
        self.close_with_a_winner()

        message = email_to(self.winner.email)
        self.assertIn("Ganaste la subasta", message.subject)
        self.assertIn(self.auction.title, message.subject)

    def test_the_winner_is_told_the_winning_amount(self):
        self.close_with_a_winner()

        self.assertIn("500.000", email_to(self.winner.email).body)

    def test_the_winner_receives_a_link_to_the_auction(self):
        self.close_with_a_winner()

        self.assertIn(
            f"http://127.0.0.1:8000/auctions/{self.auction.pk}/",
            email_to(self.winner.email).body,
        )

    def test_the_bidders_who_lost_are_not_written_to(self):
        loser = create_bidder("Perdedor")
        create_bid(self.auction, "300000", loser)
        create_bid(self.auction, "500000", self.winner)

        self.deliver(lambda: close_auction(self.auction))

        self.assertIsNone(email_to(loser.email))

    def test_an_auction_nobody_bid_on_writes_to_no_bidder(self):
        bystander = create_bidder("Curioso")

        self.deliver(lambda: close_auction(self.auction))

        self.assertIsNone(email_to(bystander.email))

    def test_closing_an_auction_twice_notifies_the_winner_only_once(self):
        self.close_with_a_winner()

        self.deliver(lambda: close_auction(self.auction))

        self.assertEqual(len(emails_to(self.winner.email)), 1)

    def test_an_auction_that_has_not_expired_notifies_nobody(self):
        create_bid(self.auction, "500000", self.winner)

        self.deliver(close_expired_auctions)

        self.assertIsNone(email_to(self.winner.email))


class WinnerNotificationOnEveryClosingPathTests(NotificationTestCase):
    """The winner hears about it however the auction was closed (FR07 closes it three ways)."""

    def setUp(self):
        self.auction = create_auction()
        self.winner = create_bidder("Laura Gómez")
        create_bid(self.auction, "500000", self.winner)
        expire(self.auction)

    def test_the_batch_closing_notifies_the_winner(self):
        self.deliver(close_expired_auctions)

        self.assertIsNotNone(email_to(self.winner.email))

    def test_the_close_auctions_command_notifies_the_winner(self):
        self.deliver(lambda: call_command("close_auctions", stdout=StringIO()))

        self.assertIsNotNone(email_to(self.winner.email))

    def test_closing_the_auction_by_opening_its_page_notifies_the_winner(self):
        self.deliver(
            lambda: self.client.get(
                reverse("auctions:auction_detail", args=[self.auction.pk])
            )
        )

        self.assertIsNotNone(email_to(self.winner.email))


class UnreachableMailServerTests(NotificationTestCase):
    """A mail server that is down must not undo what the notification describes."""

    def close_with_no_mail_server(self, auction):
        """Close the auction while every attempt to send is refused.

        assertLogs both checks that the failure is recorded and keeps the
        traceback out of the output of the test run.
        """
        with patch(
            "auctions.notifications.EmailMessage.send",
            side_effect=OSError("connection refused"),
        ):
            with self.assertLogs("auctions.notifications", level="ERROR") as log:
                self.deliver(lambda: close_auction(auction))
        return log

    def test_the_auction_still_closes(self):
        auction = create_auction()
        create_bid(auction, "500000")

        self.close_with_no_mail_server(auction)

        auction.refresh_from_db()
        self.assertEqual(auction.state, Auction.State.CLOSED)

    def test_the_undelivered_message_is_written_to_the_log(self):
        auction = create_auction()
        winner = create_bidder("Laura Gómez")
        create_bid(auction, "500000", winner)

        log = self.close_with_no_mail_server(auction)

        self.assertIn(winner.email, str(log.output))
