"""Use cases of the escrow app. Views call these; they never touch the ORM."""

from django.contrib.auth import get_user_model
from django.db import transaction

from escrow.exceptions import (
    AuctionHasNoWinner,
    AuctionIsNotClosed,
    NotAParticipant,
    NotTheBuyer,
    TransactionAlreadyExists,
    TransactionIsNotHeld,
)
from escrow.models import EscrowTransaction, StateChange

User = get_user_model()

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


@transaction.atomic
def confirm_reception(escrow_transaction, buyer):
    """Let the buyer declare that the item arrived, which frees the money (FR15).

    Only the buyer may do it: the whole point of retaining the payment is that
    the person who paid is the one who decides it was earned. Confirming is
    recorded as the transition it causes, with the buyer as its actor, so the
    history answers who released the money and when.
    """
    if escrow_transaction.buyer_id != buyer.id:
        raise NotTheBuyer
    if not escrow_transaction.is_held:
        raise TransactionIsNotHeld

    previous_state = escrow_transaction.state
    escrow_transaction.state = EscrowTransaction.State.RELEASED
    escrow_transaction.save(update_fields=["state"])
    record_state_change(escrow_transaction, previous_state=previous_state, actor=buyer)
    return escrow_transaction


def find_transaction(transaction_id):
    """Return that transaction, or raise EscrowTransaction.DoesNotExist."""
    return EscrowTransaction.objects.select_related(
        "auction", "buyer", "seller"
    ).get(pk=transaction_id)


def assert_may_read(escrow_transaction, user):
    """Refuse anyone who is not the buyer, the seller or an administrator.

    Money is not public the way the catalogue is: what somebody paid and to
    whom concerns only the two sides of the sale and whoever arbitrates it.
    """
    is_participant = user.id in (escrow_transaction.buyer_id, escrow_transaction.seller_id)
    is_administrator = user.role == User.Role.ADMINISTRATOR
    if not (is_participant or is_administrator):
        raise NotAParticipant


def list_payments_awaiting_confirmation(buyer):
    """Return the payments this buyer still has to confirm, oldest first (FR15).

    Oldest first because the one that has been waiting longest is the one the
    seller is waiting on.
    """
    return (
        EscrowTransaction.objects.filter(
            buyer=buyer, state=EscrowTransaction.State.HELD
        )
        .select_related("auction")
        .order_by("created_at")
    )
