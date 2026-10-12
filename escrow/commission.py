"""What BidHaus keeps from a sale when it releases the funds (FR20)."""

from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

CENTS = Decimal("0.01")
PER_HUNDRED = Decimal("100")


def calculate_commission(amount):
    """Return the cut of the platform over that amount, rounded to the cent.

    Everything stays Decimal: a float would drop cents, and a commission that
    does not add up with the payout is a figure nobody can explain to a seller.
    Half of a cent rounds up, so the rounding never favours the platform by
    accident in one direction only.
    """
    percentage = Decimal(str(settings.COMMISSION_PERCENTAGE))
    return (amount * percentage / PER_HUNDRED).quantize(CENTS, rounding=ROUND_HALF_UP)
