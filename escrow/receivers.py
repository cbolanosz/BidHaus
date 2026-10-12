"""What the escrow app does when an auction announces something (FR14)."""

from django.dispatch import receiver

from auctions.signals import auction_closed
from escrow.services import hold_payment


@receiver(auction_closed, dispatch_uid="escrow.hold_payment_for_closed_auction")
def hold_payment_for_closed_auction(sender, auction, **kwargs):
    """Retain the payment as soon as the auction closes with a winner (FR14).

    An auction nobody bid on closes with no winning bid, so there is no payment
    to retain and no buyer to retain it from: it is skipped, not an error.
    """
    if auction.winning_bid is None:
        return
    hold_payment(auction)
