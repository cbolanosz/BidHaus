"""What the header of every page needs to know about the money of a user."""

from escrow.services import list_open_disputes_of, list_payments_awaiting_confirmation


def what_the_buyer_still_has_to_do(request):
    """Offer the buyer the sales that are still waiting on them (FR15, FR18).

    A closed auction leaves the catalogue, so without this the buyer would have
    no way back to the lot they won: neither to confirm that it arrived, nor to
    follow the claim they opened when it did not.
    """
    if not request.user.is_authenticated:
        return {}

    payments = list(list_payments_awaiting_confirmation(request.user))
    disputes = list(list_open_disputes_of(request.user))
    return {
        "payments_awaiting_confirmation": len(payments),
        "next_payment_to_confirm": payments[0] if payments else None,
        "open_disputes": len(disputes),
        "next_open_dispute": disputes[0] if disputes else None,
    }
