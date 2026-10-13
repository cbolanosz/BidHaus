"""Tests of the auction detail page (FR04)."""

import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from analytics.models import TrustScore
from auctions.models import Auction
from auctions.services import add_photographs
from auctions.services import approve_auction_publication
from auctions.tests.factories import (
    build_image,
    create_auction,
    create_bid,
    create_bidder,
    create_seller,
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AuctionDetailViewTests(TestCase):
    def setUp(self):
        self.auction = create_auction(title="Cámara Yashica FX-3")
        self.url = reverse("auctions:auction_detail", args=[self.auction.pk])

    def test_shows_the_auction_with_its_current_price(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auctions/auction_detail.html")
        self.assertContains(response, "Cámara Yashica FX-3")
        self.assertContains(response, "250.000")

    def test_answers_not_found_for_an_auction_that_does_not_exist(self):
        response = self.client.get(reverse("auctions:auction_detail", args=[9999]))

        self.assertEqual(response.status_code, 404)

    def test_shows_the_photographs_of_the_auction(self):
        add_photographs(self.auction, [build_image("frontal.jpg")])

        response = self.client.get(self.url)

        self.assertContains(response, "frontal.jpg")

    def test_shows_the_history_from_the_highest_bid_to_the_lowest(self):
        create_bid(self.auction, "300000", create_bidder("Ana Pujadora"))
        create_bid(self.auction, "500000", create_bidder("Beto Pujador"))

        response = self.client.get(self.url)
        body = response.content.decode()

        self.assertLess(body.index("500.000"), body.index("300.000"))
        self.assertContains(response, "Ana Pujadora")
        self.assertContains(response, "Beto Pujador")

    def test_tells_the_visitor_when_there_are_no_bids_yet(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Todavía nadie ha pujado")

    def test_reads_the_page_with_a_fixed_number_of_queries(self):
        """The auction and score do not add queries beyond its collections."""
        for amount in range(300000, 310000, 1000):
            create_bid(self.auction, str(amount))

        with self.assertNumQueries(3):
            self.client.get(self.url)

    def test_hides_a_pending_publication_request(self):
        self.auction.state = Auction.State.PENDING
        self.auction.save(update_fields=["state"])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_displays_the_stored_trust_score_and_factors(self):
        pending_auction = create_auction(
            seller=create_seller(), state=Auction.State.PENDING
        )
        administrator = create_seller()
        administrator.role = administrator.Role.ADMINISTRATOR
        administrator.save(update_fields=["role"])
        approve_auction_publication(pending_auction, administrator)

        response = self.client.get(
            reverse("auctions:auction_detail", args=[pending_auction.pk])
        )

        score = TrustScore.objects.get(auction=pending_auction).score
        self.assertContains(response, f'aria-label="Puntaje de confianza: {score} de 100"')
        self.assertContains(response, f"<strong>{score}</strong>")
        self.assertContains(response, "El vendedor tiene su identidad verificada")
