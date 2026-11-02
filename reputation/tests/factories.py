"""Objects the reputation tests need in order to exercise a use case."""

from auctions.tests.factories import create_bidder
from escrow.services import confirm_reception, hold_payment
from escrow.tests.factories import create_closed_auction


def create_completed_sale(amount="400000", seller=None, bidder=None):
    """A sale whose money already reached the seller, which is what FR24 needs."""
    buyer = bidder or create_bidder()
    escrow_transaction = hold_payment(
        create_closed_auction(amount=amount, seller=seller, bidder=buyer)
    )
    confirm_reception(escrow_transaction, buyer)
    escrow_transaction.refresh_from_db()
    return escrow_transaction
