"""Tests of the last filter FR03 asks for: the rating of the seller."""

from django.test import TestCase
from django.urls import reverse

from auctions.services import search_auctions
from auctions.tests.factories import create_auction, create_seller
from reputation.services import rate_counterpart
from reputation.tests.factories import create_completed_sale


def rate(seller, *scores):
    """Give that seller those scores, each one through a sale of its own."""
    for score in scores:
        sale = create_completed_sale(seller=seller)
        rate_counterpart(sale, sale.buyer, score)
    return seller


class FilterBySellerRatingTests(TestCase):
    def setUp(self):
        self.excellent = rate(create_seller(), 5, 5, 4)
        self.poor = rate(create_seller(), 3, 1)  # averages exactly 2
        self.unrated = create_seller()

        self.of_the_excellent = create_auction(seller=self.excellent, title="De la buena")
        self.of_the_poor = create_auction(seller=self.poor, title="De la regular")
        self.of_the_unrated = create_auction(seller=self.unrated, title="De la nueva")

    def found(self, minimum):
        return {auction.title for auction in search_auctions(minimum_seller_rating=minimum)}

    def test_without_the_filter_every_open_lot_is_listed(self):
        self.assertEqual(
            self.found(None),
            {"De la buena", "De la regular", "De la nueva"},
        )

    def test_keeps_only_the_sellers_at_or_above_the_score(self):
        self.assertEqual(self.found(4), {"De la buena"})

    def test_a_lower_bar_lets_more_through(self):
        """Three and one average exactly two, and the bar is «two or more»."""
        self.assertEqual(self.found(2), {"De la buena", "De la regular"})

    def test_a_seller_below_the_bar_is_left_out(self):
        self.assertNotIn("De la regular", self.found(3))

    def test_leaves_out_a_seller_nobody_has_rated(self):
        """They have no average, so they cannot be above a bar."""
        self.assertNotIn("De la nueva", self.found(2))

    def test_the_average_is_what_counts_and_not_a_single_score(self):
        """Four, five and five average 4.67, which clears a bar of four."""
        self.assertIn("De la buena", self.found(4))

    def test_combines_with_the_other_filters(self):
        found = {
            auction.title
            for auction in search_auctions(text="buena", minimum_seller_rating=4)
        }

        self.assertEqual(found, {"De la buena"})


class WhatTheCatalogueShowsTests(TestCase):
    def setUp(self):
        self.seller = rate(create_seller(), 5, 4)
        self.auction = create_auction(seller=self.seller, title="Lote calificado")

    def test_carries_the_average_without_asking_for_it_again(self):
        found = search_auctions().get(pk=self.auction.pk)

        self.assertEqual(found.seller_rating, 4.5)

    def test_carries_how_many_scores_the_average_rests_on(self):
        found = search_auctions().get(pk=self.auction.pk)

        self.assertEqual(found.seller_rating_count, 2)

    def test_the_two_figures_do_not_multiply_the_rows(self):
        """Both annotations come from one join, so the list keeps its length."""
        self.assertEqual(search_auctions().filter(pk=self.auction.pk).count(), 1)

    def test_the_card_says_how_many_scores_it_rests_on(self):
        response = self.client.get(reverse("auctions:catalogue"))

        self.assertContains(response, "(2)")

    def test_the_detail_says_how_many_scores_it_rests_on(self):
        response = self.client.get(
            reverse("auctions:auction_detail", args=[self.auction.pk])
        )

        self.assertContains(response, "(2)")
        self.assertContains(response, "Promedio de 2 calificaciones recibidas")

    def test_one_single_score_is_named_in_the_singular(self):
        seller = rate(create_seller(), 1)
        auction = create_auction(seller=seller, title="Una sola reseña")

        response = self.client.get(
            reverse("auctions:auction_detail", args=[auction.pk])
        )

        self.assertContains(response, "Promedio de 1 calificación recibida")

    def test_the_card_shows_it(self):
        response = self.client.get(reverse("auctions:catalogue"))

        # Spanish writes the decimal with a comma, and so does the page.
        self.assertContains(response, "4,5")

    def test_the_detail_shows_it(self):
        response = self.client.get(
            reverse("auctions:auction_detail", args=[self.auction.pk])
        )

        self.assertContains(response, "4,5")

    def test_the_form_offers_the_filter(self):
        response = self.client.get(reverse("auctions:catalogue"))

        self.assertContains(response, "Calificación del vendedor")
        self.assertContains(response, "4 estrellas o más")

    def test_a_lot_of_an_unrated_seller_shows_no_average(self):
        auction = create_auction(seller=create_seller(), title="Sin calificar")

        response = self.client.get(
            reverse("auctions:auction_detail", args=[auction.pk])
        )

        self.assertNotContains(response, "rating-stars")
