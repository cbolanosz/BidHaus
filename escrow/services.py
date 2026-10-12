"""Use cases of the escrow app. Views call these; they never touch the ORM."""

from django.db import transaction

from escrow.exceptions import (
    AuctionHasNoWinner,
    AuctionIsNotClosed,
    TransactionAlreadyExists,
)
from escrow.models import EscrowTransaction, StateChange

# A change nobody triggered by hand: the system itself moved the money.
SYSTEM = None


@transaction.atomic
def hold_payment(auction):
    """Retain the payment of the winning bidder of a closed auction (FR14).

    The money never leaves the platform in this project: retaining it means
    writing the transaction and the first entry of its history. Both happen
    together, so a transaction never exists without the change that created it.
    """
    if auction.is_open:
        raise AuctionIsNotClosed
    if auction.winning_bid is None:
        raise AuctionHasNoWinner
    if find_transaction_for_auction(auction) is not None:
        raise TransactionAlreadyExists

    escrow_transaction = EscrowTransaction.objects.create(
        auction=auction,
        buyer=auction.winning_bid.bidder,
        seller=auction.seller,
        amount=auction.winning_bid.amount,
        state=EscrowTransaction.State.HELD,
    )
    record_state_change(escrow_transaction, previous_state="", actor=SYSTEM)
    return escrow_transaction


def record_state_change(escrow_transaction, previous_state, actor):
    """Append the transition that left the transaction in its current state."""
    return StateChange.objects.create(
        transaction=escrow_transaction,
        previous_state=previous_state,
        new_state=escrow_transaction.state,
        actor=actor,
    )


def find_transaction_for_auction(auction):
    """Return the transaction of that auction, or None if it has none yet."""
    return EscrowTransaction.objects.filter(auction=auction).first()


def list_state_changes(escrow_transaction):
    """Return the history of the transaction, oldest first."""
    return escrow_transaction.state_changes.select_related("actor")
