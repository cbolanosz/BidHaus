"""Objects the escrow tests need in order to exercise a use case."""

from auctions.models import Auction
from auctions.tests.factories import create_auction, create_bid, create_bidder


def create_closed_auction(amount="400000", seller=None, bidder=None):
    """Close an auction the way the service does: a winning bid and the state.

    Written by hand instead of through close_auction, so that a test of what
    happens on closing is not using the very thing it is testing to set up.
    """
    auction = create_auction(seller=seller)
    winning_bid = create_bid(auction, amount, bidder or create_bidder())
    auction.state = Auction.State.CLOSED
    auction.winning_bid = winning_bid
    auction.save(update_fields=["state", "winning_bid"])
    return auction


def create_closed_auction_without_bids(seller=None):
    """Close an auction nobody bid on, so it has no winner and no buyer."""
    auction = create_auction(seller=seller)
    auction.state = Auction.State.CLOSED
    auction.save(update_fields=["state"])
    return auction
