"""Use cases of the reputation app. Views call these; they never touch the ORM."""

from django.db import transaction
from django.db.models import Avg, Q

from escrow.models import EscrowTransaction
from reputation.exceptions import AlreadyRated, NotAParticipant, SaleIsNotCompleted
from reputation.models import Rating


@transaction.atomic
def rate_counterpart(escrow_transaction, rater, score):
    """Register the score one side gives the other after a sale (FR24).

    Only a sale whose money reached the seller is rated. A payment still
    retained has not finished, and one refunded out of a dispute was already
    judged by an administrator: a score on top of that would be a second
    sentence for the same thing.
    """
    if escrow_transaction.state != EscrowTransaction.State.RELEASED:
        raise SaleIsNotCompleted

    counterpart = find_counterpart(escrow_transaction, rater)
    if counterpart is None:
        raise NotAParticipant
    if find_rating(escrow_transaction, rater) is not None:
        raise AlreadyRated

    rating = Rating(
        transaction=escrow_transaction, rater=rater, rated=counterpart, score=score
    )
    rating.full_clean()
    rating.save()
    return rating


def find_counterpart(escrow_transaction, user):
    """The other side of that sale, or None if this user is not in it."""
    if escrow_transaction.buyer_id == user.id:
        return escrow_transaction.seller
    if escrow_transaction.seller_id == user.id:
        return escrow_transaction.buyer
    return None


def find_rating(escrow_transaction, rater):
    """The score this user already gave for that sale, or None."""
    return Rating.objects.filter(transaction=escrow_transaction, rater=rater).first()


def list_sales_to_rate(user):
    """The completed sales where this user has yet to score the other side.

    A closed auction leaves the catalogue, so this list is the only way back to
    a sale once its money has moved.
    """
    return (
        EscrowTransaction.objects.filter(state=EscrowTransaction.State.RELEASED)
        .filter(Q(buyer=user) | Q(seller=user))
        .exclude(ratings__rater=user)
        .select_related("auction", "buyer", "seller")
        .order_by("created_at")
    )


def list_ratings_of(user):
    """Every score this user has received, most recent first."""
    return Rating.objects.filter(rated=user).select_related("rater", "transaction__auction")


def average_rating_of(user):
    """The average of the scores this user received, or None if they have none."""
    return Rating.objects.filter(rated=user).aggregate(average=Avg("score"))["average"]
