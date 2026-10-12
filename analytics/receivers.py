"""What the analytics app does when an auction announces something (FR25)."""

from django.dispatch import receiver

from analytics.services import calculate_trust_score
from auctions.signals import auction_published


@receiver(auction_published, dispatch_uid="analytics.score_published_auction")
def score_published_auction(sender, auction, **kwargs):
    """Score the auction the moment it is published (FR25)."""
    calculate_trust_score(auction)
