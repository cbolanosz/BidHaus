"""Tests of the catalogue page (FR03)."""

import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from auctions.models import Auction
from auctions.services import add_photographs
from auctions.tests.factories import build_image, create_auction, create_category


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AuctionCatalogueViewTests(TestCase):
    def setUp(self):
        self.url = reverse("auctions:catalogue")
        self.cameras = create_category("Fotografía")
        self.books = create_category("Libros")

    def test_lists_the_open_auctions(self):
        create_auction(title="Cámara Yashica FX-3", category=self.cameras)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auctions/catalogue.html")
        self.assertContains(response, "Cámara Yashica FX-3")

    def test_narrows_the_list_with_the_filters_of_the_query_string(self):
        create_auction(title="Cámara Yashica FX-3", category=self.cameras)
        create_auction(title="Cien años de soledad", category=self.books)

        response = self.client.get(self.url, {"category": self.books.pk})

        self.assertContains(response, "Cien años de soledad")
        self.assertNotContains(response, "Cámara Yashica FX-3")

    def test_reports_an_inverted_price_range_without_listing_anything(self):
        create_auction(title="Cámara Yashica FX-3")

        response = self.client.get(self.url, {"minimum_price": "900000", "maximum_price": "1000"})

        self.assertContains(response, "El precio máximo debe ser mayor que el mínimo.")
        self.assertNotContains(response, "Cámara Yashica FX-3")

    def test_tells_the_visitor_when_nothing_matches(self):
        response = self.client.get(self.url, {"text": "algo que no existe"})

        self.assertContains(response, "No hay subastas que coincidan con la búsqueda.")

    def test_shows_the_first_photograph_of_each_auction(self):
        auction = create_auction(title="Cámara Yashica FX-3")
        add_photographs(auction, [build_image("primera.jpg"), build_image("segunda.jpg")])

        response = self.client.get(self.url)

        self.assertContains(response, "primera.jpg")
        self.assertNotContains(response, "segunda.jpg")

    def test_announces_an_auction_without_photographs(self):
        create_auction(title="Cámara Yashica FX-3")

        response = self.client.get(self.url)

        self.assertContains(response, "Sin fotografías")

    def test_reads_the_catalogue_with_a_fixed_number_of_queries(self):
        for number in range(5):
            auction = create_auction(title=f"Subasta {number}")
            add_photographs(auction, [build_image()])

        with self.assertNumQueries(3):
            response = self.client.get(self.url)
            self.assertEqual(len(response.context["auctions"]), 5)
