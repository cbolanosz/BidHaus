"""Tests of the automatic closing of an auction (FR07)."""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from auctions.models import Auction
from auctions.services import close_auction_if_expired, close_expired_auctions
from auctions.tests.factories import create_auction


def expire(auction, minutes_ago=1):
    """Push the closing date of an auction into the past, bypassing validation."""
    Auction.objects.filter(pk=auction.pk).update(
        closing_date=timezone.now() - timedelta(minutes=minutes_ago)
    )
    auction.refresh_from_db()
    return auction


class CloseExpiredAuctionsTests(TestCase):
    def test_closes_an_auction_whose_date_has_passed(self):
        auction = expire(create_auction())

        close_expired_auctions()

        auction.refresh_from_db()
        self.assertEqual(auction.state, Auction.State.CLOSED)

    def test_leaves_an_auction_that_has_not_expired_open(self):
        auction = create_auction()

        close_expired_auctions()

        auction.refresh_from_db()
        self.assertEqual(auction.state, Auction.State.OPEN)

    def test_returns_the_auctions_it_closed(self):
        expired_auction = expire(create_auction(title="Vencida"))
        create_auction(title="Vigente")

        closed_auctions = close_expired_auctions()

        self.assertEqual([auction.pk for auction in closed_auctions], [expired_auction.pk])

    def test_running_it_twice_closes_nothing_the_second_time(self):
        expire(create_auction())

        close_expired_auctions()
        closed_on_the_second_run = close_expired_auctions()

        self.assertEqual(closed_on_the_second_run, [])

    def test_does_not_touch_a_cancelled_auction(self):
        auction = expire(create_auction())
        Auction.objects.filter(pk=auction.pk).update(state=Auction.State.CANCELLED)

        close_expired_auctions()

        auction.refresh_from_db()
        self.assertEqual(auction.state, Auction.State.CANCELLED)

    def test_closes_every_expired_auction_at_once(self):
        for number in range(3):
            expire(create_auction(title=f"Vencida {number}"))

        close_expired_auctions()

        self.assertEqual(Auction.objects.expired().count(), 0)


class CloseAuctionIfExpiredTests(TestCase):
    def test_closes_the_auction_when_its_date_has_passed(self):
        auction = expire(create_auction())

        close_auction_if_expired(auction)

        self.assertEqual(auction.state, Auction.State.CLOSED)

    def test_leaves_an_auction_that_is_still_running(self):
        auction = create_auction()

        close_auction_if_expired(auction)

        self.assertEqual(auction.state, Auction.State.OPEN)


class CloseAuctionsCommandTests(TestCase):
    def run_command(self):
        output = StringIO()
        call_command("close_auctions", stdout=output)
        return output.getvalue()

    def test_closes_the_expired_auctions(self):
        auction = expire(create_auction())

        self.run_command()

        auction.refresh_from_db()
        self.assertEqual(auction.state, Auction.State.CLOSED)

    def test_reports_what_it_closed(self):
        expire(create_auction(title="Cámara Yashica FX-3"))

        output = self.run_command()

        self.assertIn("Cámara Yashica FX-3", output)
        self.assertIn("1 auction(s) closed.", output)

    def test_reports_nothing_to_close(self):
        create_auction()

        output = self.run_command()

        self.assertIn("0 auction(s) closed.", output)


class ExpiredAuctionOnTheDetailPageTests(TestCase):
    def test_the_page_closes_an_auction_that_is_already_over(self):
        auction = expire(create_auction())

        response = self.client.get(reverse("auctions:auction_detail", args=[auction.pk]))

        auction.refresh_from_db()
        self.assertEqual(auction.state, Auction.State.CLOSED)
        self.assertNotContains(response, "Tu puja (COP)")
        self.assertContains(response, "Subasta cerrada")
