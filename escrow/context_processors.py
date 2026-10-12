"""What the header of every page needs to know about the money of a user."""

from escrow.services import list_payments_awaiting_confirmation


def payments_awaiting_confirmation(request):
    """Offer the buyer the payments that are still waiting on them (FR15).

    A closed auction leaves the catalogue, so without this the buyer would have
    no way back to the lot they won and the confirmation would be unreachable.
    """
    if not request.user.is_authenticated:
        return {}

    payments = list(list_payments_awaiting_confirmation(request.user))
    return {
        "payments_awaiting_confirmation": len(payments),
        "next_payment_to_confirm": payments[0] if payments else None,
    }
