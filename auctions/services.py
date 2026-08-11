"""Use cases of the auctions app. Views call these; they never touch the ORM."""

import time

from django.contrib.auth import get_user_model
from django.db import OperationalError, transaction
from django.db.models import Max
from django.utils import timezone

from auctions.exceptions import (
    AuctionClosed,
    BiddingIsBusy,
    BidTooLow,
    NoPhotographs,
    NotABidder,
    NotASeller,
    SellerCannotBid,
    TooManyPhotographs,
)
from auctions.models import MAX_PHOTOGRAPHS, Auction, Bid, Photograph

User = get_user_model()

FIRST_DISPLAY_ORDER = 1

# SQLite serialises writes with a database-level lock, so a bid that arrives
# while another one is being written fails instead of waiting (CLAUDE.md 4.1).
BID_ATTEMPTS = 3
BID_RETRY_BACKOFF_SECONDS = 0.1


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
    return Auction.objects.select_related(
        "seller", "category", "winning_bid__bidder"
    ).get(pk=auction_id)


def close_expired_auctions():
    """Close every auction whose closing date has already passed (FR07).

    Idempotent: an auction that is no longer open is not selected again, so
    running this twice closes nothing the second time. Returns what it closed.
    """
    expired_auctions = list(Auction.objects.expired())
    for auction in expired_auctions:
        close_auction(auction)
    return expired_auctions


def close_auction_if_expired(auction):
    """Close an auction that is served after its closing date (FR07).

    Django has no scheduler, so between two runs of the close_auctions command
    an auction can be requested while it is already past its time. Closing it
    on access keeps what the visitor sees honest.
    """
    if auction.is_open and auction.closing_date <= timezone.now():
        close_auction(auction)
    return auction


@transaction.atomic
def close_auction(auction):
    """Close an open auction and mark its highest bid as the winner (FR07, FR08).

    The bids are ordered by descending amount and then by time, so the first one
    is the highest and, on a tie, the one that arrived first. An auction that
    nobody bid on closes with no winning bid.
    """
    if not auction.is_open:
        return auction

    auction.state = Auction.State.CLOSED
    auction.winning_bid = auction.bids.first()
    auction.save(update_fields=["state", "winning_bid"])
    return auction


def list_photographs(auction):
    """Return the photographs of an auction, in the order the seller chose."""
    return auction.photographs.all()


def list_bids(auction):
    """Return the complete bid history of an auction, highest amount first (FR04)."""
    return auction.bids.select_related("bidder")


def place_bid(auction_id, bidder, amount):
    """Register a bid on an open auction and update its current price (FR05).

    Two bidders can reach this at the same time, and on SQLite the loser of that
    race is rejected with a lock error rather than made to wait. Retrying the
    whole transaction is what turns that rejection into a bid that is simply
    registered a moment later.
    """
    for attempt in range(BID_ATTEMPTS):
        try:
            return _register_bid(auction_id, bidder, amount)
        except OperationalError:
            time.sleep(BID_RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise BiddingIsBusy


@transaction.atomic
def _register_bid(auction_id, bidder, amount):
    """Validate and store one bid against the price stored right now.

    The auction is read again inside the transaction because the price rendered
    in the form may already be stale by the time the bidder submits it.
    """
    auction = Auction.objects.select_for_update().get(pk=auction_id)  # no-op on SQLite, kept for portability

    if bidder.role != User.Role.BIDDER:
        raise NotABidder
    if auction.seller_id == bidder.id:
        raise SellerCannotBid
    if not auction.is_open or auction.closing_date <= timezone.now():
        raise AuctionClosed
    if amount <= auction.current_price:
        raise BidTooLow(auction.current_price)

    bid = Bid(auction=auction, bidder=bidder, amount=amount)
    bid.full_clean()
    bid.save()

    auction.current_price = amount
    auction.save(update_fields=["current_price"])
    return bid


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
