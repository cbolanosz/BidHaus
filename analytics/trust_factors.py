"""What BidHaus looks at to decide how much an auction can be trusted (FR25).

Every factor answers one yes-or-no question about the auction and is worth a
fixed number of points. The score is the sum of what the auction earns, so a
brand-new seller does not start accused: they start at zero and earn trust.

Adding a factor means appending to TRUST_FACTORS and nothing else. No service
grows an if-chain, which is what the open/closed principle asks for here. The
weights must add up to MAXIMUM_SCORE, and a test refuses to let them drift.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from django.utils import timezone

MINIMUM_SCORE = 0
MAXIMUM_SCORE = 100

# A seller who registered minutes before publishing has no history to judge.
ESTABLISHED_ACCOUNT_DAYS = 30
# Below this, a description says the title again and nothing more.
DETAILED_DESCRIPTION_CHARACTERS = 200
# One photograph is the minimum DBR03 allows; several is what shows the item.
SEVERAL_PHOTOGRAPHS = 3
# A price far under what the category is worth is the oldest bait there is.
SUSPICIOUS_FRACTION_OF_CATEGORY_PRICE = Decimal("0.4")


@dataclass(frozen=True)
class TrustFactor:
    """One question the score asks, and what answering it yes is worth."""

    name: str
    label: str
    points: int
    is_met: Callable


def seller_is_verified(auction):
    """An administrator checked this seller's identity document (FR21, FR23)."""
    return auction.seller.is_verified


def seller_has_sold_before(auction):
    """This is not the first lot this seller takes all the way to a buyer."""
    return (
        type(auction)
        .objects.filter(seller=auction.seller, winning_bid__isnull=False)
        .exclude(pk=auction.pk)
        .exists()
    )


def seller_account_is_established(auction):
    """The account is older than a month, so it was not opened for this lot."""
    age = timezone.now() - auction.seller.date_joined
    return age.days >= ESTABLISHED_ACCOUNT_DAYS


def auction_has_several_photographs(auction):
    """The item was shown from more than one angle."""
    return auction.photographs.count() >= SEVERAL_PHOTOGRAPHS


def description_is_detailed(auction):
    """The description says something about the item, its use and its defects."""
    return len(auction.description) >= DETAILED_DESCRIPTION_CHARACTERS


def price_is_not_far_below_its_category(auction):
    """The starting price is in the range of what its category is worth.

    A category with nothing to compare against gives the benefit of the doubt:
    the first lot of a category is not suspicious for being the first.
    """
    from django.db.models import Avg

    average = (
        type(auction)
        .objects.filter(category=auction.category)
        .exclude(pk=auction.pk)
        .aggregate(average=Avg("starting_price"))["average"]
    )
    if average is None:
        return True
    return auction.starting_price >= average * SUSPICIOUS_FRACTION_OF_CATEGORY_PRICE


# The order is the order a reader sees on the page: the identity of the seller
# first, then their history, then the lot itself.
TRUST_FACTORS = [
    TrustFactor(
        name="seller_is_verified",
        label="El vendedor tiene su identidad verificada",
        points=30,
        is_met=seller_is_verified,
    ),
    TrustFactor(
        name="seller_has_sold_before",
        label="El vendedor ya ha vendido en BidHaus",
        points=20,
        is_met=seller_has_sold_before,
    ),
    TrustFactor(
        name="seller_account_is_established",
        label="La cuenta del vendedor tiene más de un mes",
        points=10,
        is_met=seller_account_is_established,
    ),
    TrustFactor(
        name="auction_has_several_photographs",
        label="El lote tiene tres fotografías o más",
        points=15,
        is_met=auction_has_several_photographs,
    ),
    TrustFactor(
        name="description_is_detailed",
        label="La descripción detalla el artículo",
        points=10,
        is_met=description_is_detailed,
    ),
    TrustFactor(
        name="price_is_not_far_below_its_category",
        label="El precio inicial está en el rango de su categoría",
        points=15,
        is_met=price_is_not_far_below_its_category,
    ),
]
