"""Use cases of the analytics app. Views call these; they never touch the ORM."""

from django.db import transaction

from analytics.exceptions import ScoreAlreadyCalculated
from analytics.models import TrustScore
from analytics.trust_factors import TRUST_FACTORS


@transaction.atomic
def calculate_trust_score(auction):
    """Score how much this auction can be trusted, from 0 to 100 (FR25).

    Every factor is asked once and its answer stored, so the page can tell a
    visitor why the number is what it is instead of handing them a figure with
    no argument behind it.
    """
    if find_trust_score(auction) is not None:
        raise ScoreAlreadyCalculated

    factors = [_answer(factor, auction) for factor in TRUST_FACTORS]
    score = sum(factor["points"] for factor in factors if factor["met"])
    return TrustScore.objects.create(auction=auction, score=score, factors=factors)


def find_trust_score(auction):
    """Return the score of that auction, or None if it has none yet (FR26)."""
    return TrustScore.objects.filter(auction=auction).first()


def _answer(trust_factor, auction):
    """Ask one factor about this auction and record what it answered."""
    return {
        "factor": trust_factor.name,
        "label": trust_factor.label,
        "points": trust_factor.points,
        "met": bool(trust_factor.is_met(auction)),
    }
