"""Use cases of the auctions app. Views call these; they never touch the ORM."""

from django.contrib.auth import get_user_model
from django.db import transaction

from auctions.exceptions import NotASeller
from auctions.models import Auction

User = get_user_model()


@transaction.atomic
def publish_auction(seller, category, title, description, condition, starting_price, closing_date):
    """Publish an auction that opens at its starting price (FR01).

    Only a user registered with the seller role may publish. The current price
    starts equal to the starting price, so the first bid is compared against a
    real amount instead of against a null.
    """
    if seller.role != User.Role.SELLER:
        raise NotASeller

    auction = Auction(
        seller=seller,
        category=category,
        title=title,
        description=description,
        condition=condition,
        starting_price=starting_price,
        current_price=starting_price,
        closing_date=closing_date,
        state=Auction.State.OPEN,
    )
    auction.full_clean()
    auction.save()
    return auction
