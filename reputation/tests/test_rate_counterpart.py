"""Tests of the score each side gives the other after a sale (FR24)."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from auctions.tests.factories import create_bidder
from escrow.services import hold_payment, open_dispute
from escrow.tests.factories import create_closed_auction
from reputation.exceptions import AlreadyRated, NotAParticipant, SaleIsNotCompleted
from reputation.models import MAXIMUM_SCORE, MINIMUM_SCORE, Rating
from reputation.services import (
    average_rating_of,
    find_rating,
    list_ratings_of,
    list_sales_to_rate,
    rate_counterpart,
)
from reputation.tests.factories import create_completed_sale


class RateCounterpartTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder("Laura Gómez")
        self.sale = create_completed_sale(bidder=self.buyer)
        self.seller = self.sale.seller

    def test_the_buyer_scores_the_seller(self):
        rating = rate_counterpart(self.sale, self.buyer, 5)

        self.assertEqual(rating.rater, self.buyer)
        self.assertEqual(rating.rated, self.seller)
        self.assertEqual(rating.score, 5)

    def test_the_seller_scores_the_buyer(self):
        rating = rate_counterpart(self.sale, self.seller, 4)

        self.assertEqual(rating.rated, self.buyer)

    def test_both_sides_score_the_same_sale(self):
        rate_counterpart(self.sale, self.buyer, 5)
        rate_counterpart(self.sale, self.seller, 3)

        self.assertEqual(Rating.objects.count(), 2)

    def test_refuses_a_second_score_from_the_same_side(self):
        rate_counterpart(self.sale, self.buyer, 5)

        with self.assertRaises(AlreadyRated):
            rate_counterpart(self.sale, self.buyer, 1)

        self.assertEqual(Rating.objects.count(), 1)

    def test_refuses_somebody_outside_the_sale(self):
        with self.assertRaises(NotAParticipant):
            rate_counterpart(self.sale, create_bidder("Alguien más"), 5)

    def test_refuses_a_sale_whose_money_is_still_retained(self):
        retained = hold_payment(create_closed_auction(bidder=self.buyer))

        with self.assertRaises(SaleIsNotCompleted):
            rate_counterpart(retained, self.buyer, 5)

    def test_refuses_a_sale_that_ended_in_a_dispute(self):
        """An administrator already judged it; a score would judge it twice."""
        argued = hold_payment(create_closed_auction(bidder=self.buyer))
        open_dispute(argued, self.buyer, "No llegó.")
        argued.refresh_from_db()

        with self.assertRaises(SaleIsNotCompleted):
            rate_counterpart(argued, self.buyer, 5)

    def test_refuses_a_score_outside_the_range(self):
        for score in (MINIMUM_SCORE - 1, MAXIMUM_SCORE + 1):
            with self.assertRaises(ValidationError):
                rate_counterpart(self.sale, self.buyer, score)

        self.assertEqual(Rating.objects.count(), 0)

    def test_accepts_both_ends_of_the_range(self):
        rate_counterpart(self.sale, self.buyer, MINIMUM_SCORE)
        rate_counterpart(self.sale, self.seller, MAXIMUM_SCORE)

        self.assertEqual(Rating.objects.count(), 2)


class WhatTheDatabaseItselfRefusesTests(TestCase):
    """DBR09 rests on the columns, not on a service somebody could bypass."""

    def setUp(self):
        self.buyer = create_bidder()
        self.sale = create_completed_sale(bidder=self.buyer)

    def test_nobody_rates_themselves(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Rating.objects.create(
                    transaction=self.sale, rater=self.buyer, rated=self.buyer, score=5
                )

    def test_one_rating_per_participant_per_sale(self):
        rate_counterpart(self.sale, self.buyer, 5)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Rating.objects.create(
                    transaction=self.sale,
                    rater=self.buyer,
                    rated=self.sale.seller,
                    score=1,
                )

    def test_the_score_stays_between_one_and_five(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Rating.objects.create(
                    transaction=self.sale,
                    rater=self.buyer,
                    rated=self.sale.seller,
                    score=9,
                )


class WhatIsStillPendingTests(TestCase):
    def setUp(self):
        self.buyer = create_bidder()
        self.sale = create_completed_sale(bidder=self.buyer)

    def test_lists_the_sale_for_both_sides_until_each_one_scores(self):
        self.assertEqual(list(list_sales_to_rate(self.buyer)), [self.sale])
        self.assertEqual(list(list_sales_to_rate(self.sale.seller)), [self.sale])

        rate_counterpart(self.sale, self.buyer, 5)

        self.assertEqual(list(list_sales_to_rate(self.buyer)), [])
        self.assertEqual(list(list_sales_to_rate(self.sale.seller)), [self.sale])

    def test_does_not_list_a_sale_of_somebody_else(self):
        self.assertEqual(list(list_sales_to_rate(create_bidder("Ajena"))), [])

    def test_does_not_list_a_sale_whose_money_is_still_retained(self):
        hold_payment(create_closed_auction(bidder=self.buyer))

        self.assertEqual(list(list_sales_to_rate(self.buyer)), [self.sale])

    def test_finds_the_rating_a_user_already_gave(self):
        self.assertIsNone(find_rating(self.sale, self.buyer))

        rating = rate_counterpart(self.sale, self.buyer, 5)

        self.assertEqual(find_rating(self.sale, self.buyer), rating)


class WhatAUserIsWorthTests(TestCase):
    def setUp(self):
        self.seller = create_bidder("Vendedora")

    def test_a_user_with_no_ratings_has_no_average(self):
        self.assertIsNone(average_rating_of(self.seller))

    def test_averages_the_scores_received(self):
        for score in (5, 4, 3):
            sale = create_completed_sale(seller=self.seller)
            rate_counterpart(sale, sale.buyer, score)

        self.assertEqual(average_rating_of(self.seller), 4.0)
        self.assertEqual(list_ratings_of(self.seller).count(), 3)

    def test_the_scores_a_user_gives_do_not_count_as_received(self):
        sale = create_completed_sale(seller=self.seller)
        rate_counterpart(sale, self.seller, 1)

        self.assertIsNone(average_rating_of(self.seller))
