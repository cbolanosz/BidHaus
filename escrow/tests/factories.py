"""Objects the escrow tests need in order to exercise a use case."""

from django.core.files.uploadedfile import SimpleUploadedFile

from auctions.models import Auction
from auctions.tests.factories import create_auction, create_bid, create_bidder

# The smallest thing that passes as a PDF, so a test never carries a real file.
PDF_BYTES = b"%PDF-1.4\n%%EOF\n"


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


def build_evidence(name="factura.pdf"):
    """Build a small file that passes as a piece of evidence."""
    return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")
