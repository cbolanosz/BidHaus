"""Tests of the email sent to a bidder who is outbid (FR11)."""

from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.urls import reverse

from auctions.exceptions import BidTooLow
from auctions.services import place_bid
from auctions.tests.factories import create_auction, create_bidder
from auctions.tests.mailbox import NotificationTestCase, email_to


class OutbidNotificationTests(NotificationTestCase):
    def setUp(self):
        self.auction = create_auction()
        self.first_bidder = create_bidder("Laura Gómez")
        self.second_bidder = create_bidder("Andrés Peña")

    def bid(self, bidder, amount):
        """Place a bid and let the emails it queued go out."""
        return self.deliver(
            lambda: place_bid(self.auction.pk, bidder, Decimal(amount))
        )

    def test_notifies_the_bidder_who_was_passed(self):
        self.bid(self.first_bidder, "300000")
        mail.outbox.clear()

        self.bid(self.second_bidder, "400000")

        self.assertIsNotNone(email_to(self.first_bidder.email))

    def test_the_subject_names_the_auction(self):
        self.bid(self.first_bidder, "300000")
        self.bid(self.second_bidder, "400000")

        message = email_to(self.first_bidder.email)
        self.assertIn("Superaron tu puja", message.subject)
        self.assertIn(self.auction.title, message.subject)

    def test_the_body_carries_the_old_bid_and_the_new_price(self):
        self.bid(self.first_bidder, "300000")
        self.bid(self.second_bidder, "400000")

        body = email_to(self.first_bidder.email).body
        self.assertIn("300.000", body)
        self.assertIn("400.000", body)

    def test_the_body_links_back_to_the_auction(self):
        self.bid(self.first_bidder, "300000")
        self.bid(self.second_bidder, "400000")

        self.assertIn(
            f"http://127.0.0.1:8000/auctions/{self.auction.pk}/",
            email_to(self.first_bidder.email).body,
        )

    def test_the_first_bid_of_an_auction_notifies_nobody(self):
        self.bid(self.first_bidder, "300000")

        self.assertEqual(mail.outbox, [])

    def test_the_bidder_who_took_the_lead_is_not_notified(self):
        self.bid(self.first_bidder, "300000")
        self.bid(self.second_bidder, "400000")

        self.assertIsNone(email_to(self.second_bidder.email))

    def test_the_seller_is_not_notified_of_a_bid(self):
        self.bid(self.first_bidder, "300000")
        self.bid(self.second_bidder, "400000")

        self.assertIsNone(email_to(self.auction.seller.email))

    def test_raising_your_own_highest_bid_notifies_nobody(self):
        self.bid(self.first_bidder, "300000")
        mail.outbox.clear()

        self.bid(self.first_bidder, "400000")

        self.assertEqual(mail.outbox, [])

    def test_only_the_bidder_who_held_the_lead_is_notified(self):
        early_bidder = create_bidder("Temprano")
        self.bid(early_bidder, "300000")
        self.bid(self.first_bidder, "400000")
        mail.outbox.clear()

        self.bid(self.second_bidder, "500000")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.first_bidder.email])

    def test_every_bid_notifies_the_bidder_it_displaced(self):
        self.bid(self.first_bidder, "300000")
        self.bid(self.second_bidder, "400000")
        self.bid(self.first_bidder, "500000")

        self.assertEqual(
            [message.to for message in mail.outbox],
            [[self.first_bidder.email], [self.second_bidder.email]],
        )

    def test_a_rejected_bid_notifies_nobody(self):
        self.bid(self.first_bidder, "300000")
        mail.outbox.clear()

        with self.assertRaises(BidTooLow):
            self.bid(self.second_bidder, "100000")

        self.assertEqual(mail.outbox, [])

    def test_an_unreachable_mail_server_does_not_lose_the_bid(self):
        self.bid(self.first_bidder, "300000")

        with patch(
            "auctions.notifications.EmailMessage.send",
            side_effect=OSError("connection refused"),
        ):
            # assertLogs keeps the traceback of the refused send out of the
            # output of the test run, and checks that it was recorded.
            with self.assertLogs("auctions.notifications", level="ERROR"):
                self.bid(self.second_bidder, "400000")

        self.auction.refresh_from_db()
        self.assertEqual(self.auction.current_price, Decimal("400000.00"))
        self.assertEqual(self.auction.bids.count(), 2)


class OutbidNotificationFromTheBidFormTests(NotificationTestCase):
    """The notification also goes out when the bid arrives through the page."""

    def test_bidding_from_the_detail_page_notifies_the_bidder_it_displaced(self):
        auction = create_auction()
        first_bidder = create_bidder("Laura Gómez")
        second_bidder = create_bidder("Andrés Peña")
        self.deliver(lambda: place_bid(auction.pk, first_bidder, Decimal("300000")))
        mail.outbox.clear()

        self.client.force_login(second_bidder)
        self.deliver(
            lambda: self.client.post(
                reverse("auctions:auction_bid", args=[auction.pk]),
                {"amount": "400000"},
            )
        )

        self.assertIsNotNone(email_to(first_bidder.email))
