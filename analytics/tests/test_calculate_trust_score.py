"""Tests of the trust score of an auction (FR25)."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from analytics.exceptions import ScoreAlreadyCalculated
from analytics.models import TrustScore
from analytics.services import calculate_trust_score, find_trust_score
from analytics.trust_factors import (
    ESTABLISHED_ACCOUNT_DAYS,
    MAXIMUM_SCORE,
    MINIMUM_SCORE,
    TRUST_FACTORS,
)
from auctions.models import Auction
from auctions.tests.factories import (
    create_auction,
    create_bid,
    create_category,
    create_seller,
)

LONG_DESCRIPTION = "Pieza restaurada a mano. " * 20
SHORT_DESCRIPTION = "Se vende."


def age_the_account(user, days):
    """Backdate the registration, which auto_now_add will not let a test set."""
    type(user).objects.filter(pk=user.pk).update(
        date_joined=timezone.now() - timedelta(days=days)
    )
    user.refresh_from_db()
    return user


def create_verified_seller():
    """A seller whose identity an administrator already approved."""
    seller = create_seller()
    seller.is_verified = True
    seller.save(update_fields=["is_verified"])
    return seller


def points_of(name):
    """What that factor is worth, read from the registry and not retyped."""
    return next(factor.points for factor in TRUST_FACTORS if factor.name == name)


class TheRegistryItselfTests(TestCase):
    def test_the_weights_add_up_to_the_maximum(self):
        """An auction that meets everything must score exactly 100, not 95 or 105."""
        self.assertEqual(sum(factor.points for factor in TRUST_FACTORS), MAXIMUM_SCORE)

    def test_every_factor_is_named_only_once(self):
        names = [factor.name for factor in TRUST_FACTORS]

        self.assertEqual(len(names), len(set(names)))


class CalculateTrustScoreTests(TestCase):
    def test_an_auction_with_nothing_in_its_favour_scores_zero(self):
        """New seller, no history, one photo, no description and a bait price."""
        category = create_category("Relojes")
        create_auction(category=category, starting_price=Decimal("1000000.00"))

        auction = create_auction(
            seller=create_seller(),
            category=category,
            description=SHORT_DESCRIPTION,
            starting_price=Decimal("50000.00"),
        )

        self.assertEqual(calculate_trust_score(auction).score, MINIMUM_SCORE)

    def test_an_auction_that_meets_everything_scores_the_maximum(self):
        from auctions.services import add_photographs
        from auctions.tests.factories import build_image

        seller = age_the_account(create_verified_seller(), ESTABLISHED_ACCOUNT_DAYS + 1)
        sold = create_auction(seller=seller)
        sold.winning_bid = create_bid(sold, "500000")
        sold.save(update_fields=["winning_bid"])

        auction = create_auction(seller=seller, description=LONG_DESCRIPTION)
        add_photographs(auction, [build_image() for _ in range(3)])

        self.assertEqual(calculate_trust_score(auction).score, MAXIMUM_SCORE)

    def test_the_score_never_leaves_the_range(self):
        trust_score = calculate_trust_score(create_auction())

        self.assertGreaterEqual(trust_score.score, MINIMUM_SCORE)
        self.assertLessEqual(trust_score.score, MAXIMUM_SCORE)

    def test_stores_one_answer_per_factor(self):
        trust_score = calculate_trust_score(create_auction())

        self.assertEqual(len(trust_score.factors), len(TRUST_FACTORS))

    def test_each_answer_carries_its_label_and_its_points(self):
        trust_score = calculate_trust_score(create_auction())

        answer = trust_score.factors[0]
        self.assertIn("factor", answer)
        self.assertIn("label", answer)
        self.assertIn("points", answer)
        self.assertIn("met", answer)

    def test_the_score_is_the_sum_of_what_was_met(self):
        trust_score = calculate_trust_score(create_auction())

        earned = sum(f["points"] for f in trust_score.factors if f["met"])
        self.assertEqual(trust_score.score, earned)

    def test_refuses_to_score_the_same_auction_twice(self):
        auction = create_auction()
        calculate_trust_score(auction)

        with self.assertRaises(ScoreAlreadyCalculated):
            calculate_trust_score(auction)

        self.assertEqual(TrustScore.objects.count(), 1)

    def test_finds_the_score_of_an_auction(self):
        auction = create_auction()
        trust_score = calculate_trust_score(auction)

        self.assertEqual(find_trust_score(auction), trust_score)

    def test_finds_nothing_for_an_auction_that_has_no_score(self):
        self.assertIsNone(find_trust_score(create_auction()))


class EachFactorTests(TestCase):
    """One test per criterion, so a change of weights cannot pass unnoticed."""

    def met(self, auction, name):
        answers = calculate_trust_score(auction).factors
        return next(answer["met"] for answer in answers if answer["factor"] == name)

    def test_a_verified_seller_earns_those_points(self):
        auction = create_auction(seller=create_verified_seller())

        self.assertTrue(self.met(auction, "seller_is_verified"))

    def test_an_unverified_seller_does_not(self):
        auction = create_auction(seller=create_seller())

        self.assertFalse(self.met(auction, "seller_is_verified"))

    def test_a_seller_with_a_previous_sale_earns_those_points(self):
        seller = create_verified_seller()
        sold = create_auction(seller=seller)
        sold.winning_bid = create_bid(sold, "500000")
        sold.save(update_fields=["winning_bid"])

        self.assertTrue(self.met(create_auction(seller=seller), "seller_has_sold_before"))

    def test_a_seller_selling_for_the_first_time_does_not(self):
        auction = create_auction(seller=create_seller())

        self.assertFalse(self.met(auction, "seller_has_sold_before"))

    def test_the_lot_itself_does_not_count_as_a_previous_sale(self):
        seller = create_seller()
        auction = create_auction(seller=seller)
        auction.winning_bid = create_bid(auction, "500000")
        auction.save(update_fields=["winning_bid"])

        self.assertFalse(self.met(auction, "seller_has_sold_before"))

    def test_an_account_older_than_a_month_earns_those_points(self):
        seller = age_the_account(create_seller(), ESTABLISHED_ACCOUNT_DAYS + 1)

        self.assertTrue(
            self.met(create_auction(seller=seller), "seller_account_is_established")
        )

    def test_an_account_opened_today_does_not(self):
        auction = create_auction(seller=create_seller())

        self.assertFalse(self.met(auction, "seller_account_is_established"))

    def test_three_photographs_earn_those_points(self):
        from auctions.services import add_photographs
        from auctions.tests.factories import build_image

        auction = create_auction()
        add_photographs(auction, [build_image() for _ in range(3)])

        self.assertTrue(self.met(auction, "auction_has_several_photographs"))

    def test_a_single_photograph_does_not(self):
        from auctions.services import add_photographs
        from auctions.tests.factories import build_image

        auction = create_auction()
        add_photographs(auction, [build_image()])

        self.assertFalse(self.met(auction, "auction_has_several_photographs"))

    def test_a_long_description_earns_those_points(self):
        auction = create_auction(description=LONG_DESCRIPTION)

        self.assertTrue(self.met(auction, "description_is_detailed"))

    def test_a_one_line_description_does_not(self):
        auction = create_auction(description=SHORT_DESCRIPTION)

        self.assertFalse(self.met(auction, "description_is_detailed"))

    def test_a_price_in_the_range_of_its_category_earns_those_points(self):
        category = create_category("Relojes")
        create_auction(category=category, starting_price=Decimal("1000000.00"))
        auction = create_auction(category=category, starting_price=Decimal("900000.00"))

        self.assertTrue(self.met(auction, "price_is_not_far_below_its_category"))

    def test_a_price_far_under_its_category_does_not(self):
        category = create_category("Relojes")
        create_auction(category=category, starting_price=Decimal("1000000.00"))
        auction = create_auction(category=category, starting_price=Decimal("50000.00"))

        self.assertFalse(self.met(auction, "price_is_not_far_below_its_category"))

    def test_the_first_lot_of_a_category_gets_the_benefit_of_the_doubt(self):
        auction = create_auction(
            category=create_category("Instrumentos"), starting_price=Decimal("1000.00")
        )

        self.assertTrue(self.met(auction, "price_is_not_far_below_its_category"))


class WhatTheScoreExplainsTests(TestCase):
    def test_separates_what_was_met_from_what_was_not(self):
        trust_score = calculate_trust_score(
            create_auction(seller=create_seller(), description=SHORT_DESCRIPTION)
        )

        self.assertEqual(
            len(trust_score.met_factors) + len(trust_score.unmet_factors),
            len(TRUST_FACTORS),
        )

    def test_names_what_is_missing_in_words_a_person_reads(self):
        trust_score = calculate_trust_score(create_auction(seller=create_seller()))

        labels = [factor["label"] for factor in trust_score.unmet_factors]
        self.assertIn("El vendedor tiene su identidad verificada", labels)


class PublishingScoresTheAuctionTests(TestCase):
    """FR25 is triggered by FR36: scoring happens when publication is approved."""

    def test_publishing_leaves_the_auction_scored(self):
        from auctions.services import publish_auction
        from auctions.services import approve_auction_publication
        from auctions.tests.factories import build_image

        seller = create_seller()
        auction = publish_auction(
            seller=seller,
            category=create_category(),
            title="Cámara Yashica FX-3",
            description=LONG_DESCRIPTION,
            condition=Auction.Condition.USED,
            starting_price=Decimal("250000.00"),
            closing_date=timezone.now() + timedelta(days=2),
            images=[build_image() for _ in range(3)],
        )
        administrator = create_seller()
        administrator.role = administrator.Role.ADMINISTRATOR
        administrator.save(update_fields=["role"])
        approve_auction_publication(auction, administrator)

        trust_score = find_trust_score(auction)
        self.assertIsNotNone(trust_score)
        self.assertGreater(trust_score.score, MINIMUM_SCORE)

    def test_the_photographs_are_counted_because_they_arrive_first(self):
        from auctions.services import publish_auction
        from auctions.services import approve_auction_publication
        from auctions.tests.factories import build_image

        seller = create_seller()
        auction = publish_auction(
            seller=seller,
            category=create_category(),
            title="Cámara Yashica FX-3",
            description=LONG_DESCRIPTION,
            condition=Auction.Condition.USED,
            starting_price=Decimal("250000.00"),
            closing_date=timezone.now() + timedelta(days=2),
            images=[build_image() for _ in range(3)],
        )
        administrator = create_seller()
        administrator.role = administrator.Role.ADMINISTRATOR
        administrator.save(update_fields=["role"])
        approve_auction_publication(auction, administrator)

        answers = find_trust_score(auction).factors
        met = next(
            answer["met"]
            for answer in answers
            if answer["factor"] == "auction_has_several_photographs"
        )
        self.assertTrue(met)
