"""Tests of the authenticated user's own bid history (FR13)."""

from decimal import Decimal
from time import perf_counter

from django.test import TestCase
from django.urls import reverse

from auctions.models import Auction, Bid
from auctions.services import place_bid
from auctions.tests.factories import create_auction, create_bid, create_bidder


class MyBidsViewTests(TestCase):
    def setUp(self):
        self.bidder = create_bidder("Laura Gómez")
        self.other_bidder = create_bidder("Otra persona")
        self.auction = create_auction(title="Cámara Yashica FX-3")
        self.other_auction = create_auction(title="Reloj antiguo")
        self.url = reverse("auctions:my_bids")
        self.client.force_login(self.bidder)

    def test_requires_login(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:log_in')}?next={self.url}")

    def test_lists_only_the_authenticated_users_bids(self):
        create_bid(self.auction, "300000", self.bidder)
        create_bid(self.other_auction, "400000", self.other_bidder)

        response = self.client.get(self.url)

        self.assertContains(response, "Cámara Yashica FX-3")
        self.assertNotContains(response, "Reloj antiguo")

    def test_shows_the_auction_link_and_orders_newest_first(self):
        first = create_bid(self.auction, "300000", self.bidder)
        second = create_bid(self.other_auction, "400000", self.bidder)

        response = self.client.get(self.url)
        body = response.content.decode()

        self.assertContains(
            response,
            reverse("auctions:auction_detail", args=[first.auction_id]),
        )
        self.assertLess(body.index("Reloj antiguo"), body.index("Cámara Yashica FX-3"))
        self.assertEqual(response.context["bids"].object_list[0].pk, second.pk)

    def test_paginates_the_list(self):
        for index in range(21):
            create_bid(
                create_auction(title=f"Lote {index}"),
                Decimal(200000 + index),
                self.bidder,
            )

        first_page = self.client.get(self.url)
        second_page = self.client.get(self.url, {"page": 2})

        self.assertContains(first_page, "Página 1 de 2")
        self.assertContains(first_page, "Siguiente")
        self.assertContains(second_page, "Página 2 de 2")
        self.assertContains(second_page, "Anterior")

    def test_shows_an_empty_state(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Aún no has realizado ninguna puja")

    def test_fetches_auction_data_without_a_query_per_bid(self):
        for index in range(3):
            create_bid(
                create_auction(title=f"Lote {index}"),
                Decimal(200000 + index),
                self.bidder,
            )

        with self.assertNumQueries(7):
            self.client.get(self.url)

    def test_returns_a_page_within_three_seconds(self):
        for index in range(100):
            create_bid(
                create_auction(title=f"Lote {index}"),
                Decimal(200000 + index),
                self.bidder,
            )

        started = perf_counter()
        response = self.client.get(self.url)
        elapsed = perf_counter() - started

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 3)


class WhatEachBidSaysAboutItselfTests(TestCase):
    """A list of amounts says nothing; a bidder wants to know how each one went.

    These go through place_bid and not through the factory, because what a bid
    is worth is read from the current price of its auction, and only the
    service keeps that price up to date (FR06).
    """

    def setUp(self):
        self.bidder = create_bidder("Laura Gómez")
        self.url = reverse("auctions:my_bids")
        self.client.force_login(self.bidder)

    def close(self, auction):
        """Close an auction on its highest bid, the way the closing does."""
        auction.state = Auction.State.CLOSED
        auction.winning_bid = auction.bids.order_by("-amount").first()
        auction.save(update_fields=["state", "winning_bid"])
        return auction

    def test_a_bid_that_still_leads_an_open_auction(self):
        place_bid(create_auction().pk, self.bidder, Decimal("500000"))

        self.assertContains(self.client.get(self.url), "Vas liderando")

    def test_a_bid_somebody_else_has_passed(self):
        auction = create_auction()
        place_bid(auction.pk, self.bidder, Decimal("500000"))
        place_bid(auction.pk, create_bidder("Otra"), Decimal("600000"))

        response = self.client.get(self.url)

        self.assertContains(response, "Te superaron")
        self.assertNotContains(response, "Vas liderando")

    def test_a_bid_that_won_its_auction(self):
        auction = create_auction()
        place_bid(auction.pk, self.bidder, Decimal("500000"))
        self.close(auction)

        self.assertContains(self.client.get(self.url), "Ganaste")

    def test_a_bid_that_lost_the_auction_it_was_in(self):
        auction = create_auction()
        place_bid(auction.pk, self.bidder, Decimal("500000"))
        place_bid(auction.pk, create_bidder("Otra"), Decimal("600000"))
        self.close(auction)

        response = self.client.get(self.url)

        self.assertContains(response, "No ganaste")
        self.assertNotContains(response, ">Ganaste<")

    def test_the_standing_costs_no_query_per_row(self):
        """Five bids must not mean five extra questions to the database."""
        for _ in range(5):
            place_bid(create_auction().pk, self.bidder, Decimal("500000"))

        # session, user, the three header cells, count and page of bids.
        with self.assertNumQueries(7):
            self.client.get(self.url)
