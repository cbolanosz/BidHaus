"""Tests of the authenticated user's own bid history (FR13)."""

from decimal import Decimal
from time import perf_counter

from django.test import TestCase
from django.urls import reverse

from auctions.models import Bid
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
