"""Use cases of the auctions app. Views call these; they never touch the ORM."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max

from auctions.exceptions import NoPhotographs, NotASeller, TooManyPhotographs
from auctions.models import MAX_PHOTOGRAPHS, Auction, Photograph

User = get_user_model()

FIRST_DISPLAY_ORDER = 1


@transaction.atomic
def publish_auction(
    seller, category, title, description, condition, starting_price, closing_date, images
):
    """Publish an auction with its first photographs (FR01).

    Only a user registered with the seller role may publish. The auction and its
    photographs are stored in the same transaction, so an auction never reaches
    the catalogue without the photograph that DBR03 demands. The current price
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
    add_photographs(auction, images)
    return auction


def search_auctions(text=None, category=None, condition=None, minimum_price=None, maximum_price=None):
    """Return the open auctions that match the filters of the catalogue (FR03).

    A filter that receives no value does not narrow the search, so calling this
    without arguments returns the whole catalogue.
    """
    return (
        Auction.objects.open()
        .matching_text(text)
        .in_category(category)
        .with_condition(condition)
        .priced_from(minimum_price)
        .priced_up_to(maximum_price)
        .for_catalogue()
    )


def find_auction(auction_id):
    """Return the auction with that identifier, or raise Auction.DoesNotExist."""
    return Auction.objects.select_related("seller", "category").get(pk=auction_id)


def list_photographs(auction):
    """Return the photographs of an auction, in the order the seller chose."""
    return auction.photographs.all()


def list_bids(auction):
    """Return the complete bid history of an auction, highest amount first (FR04)."""
    return auction.bids.select_related("bidder")


def count_free_photograph_slots(auction):
    """Return how many photographs the auction can still receive (DBR03)."""
    return MAX_PHOTOGRAPHS - auction.photographs.count()


@transaction.atomic
def add_photographs(auction, images):
    """Attach uploaded images to an auction, keeping it within 1 and 8 (FR02).

    The images are appended after the ones already stored, so a second upload
    continues the display order instead of restarting it.
    """
    if not images:
        raise NoPhotographs

    free_slots = count_free_photograph_slots(auction)
    if len(images) > free_slots:
        raise TooManyPhotographs(free_slots)

    first_order = _next_display_order(auction)
    photographs = []
    for offset, image in enumerate(images):
        photograph = Photograph(auction=auction, image=image, display_order=first_order + offset)
        photograph.full_clean()
        photograph.save()
        photographs.append(photograph)
    return photographs


def _next_display_order(auction):
    """Return the display order that continues the photographs already stored."""
    highest_order = auction.photographs.aggregate(Max("display_order"))["display_order__max"]
    if highest_order is None:
        return FIRST_DISPLAY_ORDER
    return highest_order + 1
