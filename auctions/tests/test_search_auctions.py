"""Tests of the catalogue search (FR03)."""

from decimal import Decimal

from django.test import TestCase

from auctions.models import Auction
from auctions.services import search_auctions
from auctions.tests.factories import create_auction, create_category


class SearchAuctionsTests(TestCase):
    def setUp(self):
        self.cameras = create_category("Fotografía")
        self.books = create_category("Libros")
        self.camera = create_auction(
            title="Cámara Yashica FX-3",
            description="Analógica, con estuche.",
            category=self.cameras,
            condition=Auction.Condition.USED,
            current_price=Decimal("250000.00"),
        )
        self.book = create_auction(
            title="Cien años de soledad, primera edición",
            description="Ejemplar de coleccionista.",
            category=self.books,
            condition=Auction.Condition.NEW,
            current_price=Decimal("900000.00"),
        )

    def test_without_filters_returns_every_open_auction(self):
        results = search_auctions()

        self.assertCountEqual(results, [self.camera, self.book])

    def test_leaves_out_auctions_that_are_not_open(self):
        create_auction(title="Subasta cerrada", state=Auction.State.CLOSED)

        results = search_auctions()

        self.assertCountEqual(results, [self.camera, self.book])

    def test_filters_by_category(self):
        results = search_auctions(category=self.books)

        self.assertCountEqual(results, [self.book])

    def test_filters_by_condition(self):
        results = search_auctions(condition=Auction.Condition.USED)

        self.assertCountEqual(results, [self.camera])

    def test_filters_by_price_range(self):
        results = search_auctions(
            minimum_price=Decimal("200000"), maximum_price=Decimal("300000")
        )

        self.assertCountEqual(results, [self.camera])

    def test_includes_the_ends_of_the_price_range(self):
        results = search_auctions(
            minimum_price=Decimal("250000.00"), maximum_price=Decimal("250000.00")
        )

        self.assertCountEqual(results, [self.camera])

    def test_matches_text_in_the_title_ignoring_case(self):
        results = search_auctions(text="yashica")

        self.assertCountEqual(results, [self.camera])

    def test_matches_text_in_the_description(self):
        results = search_auctions(text="coleccionista")

        self.assertCountEqual(results, [self.book])

    def test_combines_every_filter(self):
        results = search_auctions(
            text="cámara",
            category=self.cameras,
            condition=Auction.Condition.USED,
            minimum_price=Decimal("100000"),
            maximum_price=Decimal("500000"),
        )

        self.assertCountEqual(results, [self.camera])

    def test_returns_nothing_when_no_auction_matches(self):
        results = search_auctions(category=self.books, condition=Auction.Condition.USED)

        self.assertCountEqual(results, [])
