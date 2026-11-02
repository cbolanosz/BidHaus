"""What the header of every page needs to know about pending ratings."""

from reputation.services import list_sales_to_rate


def sales_waiting_to_be_rated(request):
    """Offer the user the sales they can still score (FR24).

    A closed auction leaves the catalogue, so without this the way back to a
    finished sale would be gone and the rating unreachable.
    """
    if not request.user.is_authenticated:
        return {}

    sales = list(list_sales_to_rate(request.user))
    return {
        "sales_to_rate": len(sales),
        "next_sale_to_rate": sales[0] if sales else None,
    }
