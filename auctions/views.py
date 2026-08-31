"""HTTP layer: parse the request, call a service, render a template."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render

from auctions.exceptions import (
    AuctionClosed,
    BiddingIsBusy,
    BidTooLow,
    NotABidder,
    NotASeller,
    SellerCannotBid,
    TooManyPhotographs,
)
from auctions.forms import AuctionForm, AuctionSearchForm, BidForm, PhotographUploadForm
from auctions.models import MAX_PHOTOGRAPHS, Auction
from auctions.services import (
    add_photographs,
    close_auction_if_expired,
    count_free_photograph_slots,
    find_auction,
    list_bids,
    list_photographs,
    place_bid,
    publish_auction,
    search_auctions,
)


def auction_catalogue(request):
    """List the open auctions, narrowed by the filters the visitor chose (FR03)."""
    form = AuctionSearchForm(request.GET)
    if not form.is_valid():
        return render(request, "auctions/catalogue.html", {"form": form, "auctions": []})

    auctions = search_auctions(
        text=form.cleaned_data["text"],
        category=form.cleaned_data["category"],
        condition=form.cleaned_data["condition"],
        minimum_price=form.cleaned_data["minimum_price"],
        maximum_price=form.cleaned_data["maximum_price"],
    )
    return render(request, "auctions/catalogue.html", {"form": form, "auctions": auctions})


@login_required
def auction_create(request):
    """Show the publication form and publish the auction it describes (FR01)."""
    if request.method != "POST":
        return render(request, "auctions/auction_form.html", {"form": AuctionForm()})

    form = AuctionForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "auctions/auction_form.html", {"form": form})

    try:
        auction = publish_auction(
            seller=request.user,
            category=form.cleaned_data["category"],
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            condition=form.cleaned_data["condition"],
            starting_price=form.cleaned_data["starting_price"],
            closing_date=form.cleaned_data["closing_date"],
            images=form.cleaned_data["images"],
        )
    except NotASeller:
        form.add_error(None, "Tu cuenta no tiene el rol de vendedor, así que no puede publicar.")
        return render(request, "auctions/auction_form.html", {"form": form})
    except TooManyPhotographs:
        form.add_error("images", f"Una subasta admite {MAX_PHOTOGRAPHS} fotografías como máximo.")
        return render(request, "auctions/auction_form.html", {"form": form})

    messages.success(
        request,
        f"Se publicó la subasta «{auction.title}». Puedes añadir más fotografías.",
    )
    return redirect("auctions:auction_photographs", auction_id=auction.pk)


def auction_detail(request, auction_id):
    """Show an auction with its photographs and its complete bid history (FR04).

    The auction is closed first if its date has passed, so that a visitor never
    sees a countdown on an auction that is already over (FR07).
    """
    auction = close_auction_if_expired(_find_auction_or_404(auction_id))
    return _render_auction_detail(request, auction, BidForm())


@login_required
def auction_bid(request, auction_id):
    """Register the bid a bidder submitted from the detail page (FR05)."""
    auction = _find_auction_or_404(auction_id)

    if request.method != "POST":
        return redirect("auctions:auction_detail", auction_id=auction.pk)

    form = BidForm(request.POST)
    if not form.is_valid():
        return _render_auction_detail(request, auction, form)

    try:
        bid = place_bid(
            auction_id=auction.pk,
            bidder=request.user,
            amount=form.cleaned_data["amount"],
        )
    except AuctionClosed:
        form.add_error(None, "Esta subasta ya está cerrada y no admite más pujas.")
        return _render_auction_detail(request, _find_auction_or_404(auction_id), form)
    except NotABidder:
        form.add_error(None, "Tu cuenta no tiene el rol de comprador, así que no puede pujar.")
        return _render_auction_detail(request, auction, form)
    except SellerCannotBid:
        form.add_error(None, "El vendedor no puede pujar en su propia subasta.")
        return _render_auction_detail(request, auction, form)
    except BidTooLow as error:
        form.add_error("amount", f"Tu puja debe superar el precio actual: $ {error.current_price:,.0f} COP.")
        return _render_auction_detail(request, _find_auction_or_404(auction_id), form)
    except BiddingIsBusy:
        form.add_error(None, "Hay muchas pujas al tiempo. Vuelve a intentarlo.")
        return _render_auction_detail(request, _find_auction_or_404(auction_id), form)

    messages.success(request, f"Se registró tu puja de $ {bid.amount:,.0f} COP.")
    return redirect("auctions:auction_detail", auction_id=auction.pk)


def _find_auction_or_404(auction_id):
    """Return the auction with that identifier, or answer 404."""
    try:
        return find_auction(auction_id)
    except Auction.DoesNotExist:
        raise Http404("La subasta no existe.")


def _render_auction_detail(request, auction, form):
    """Render the detail page with everything a visitor sees on it."""
    return render(
        request,
        "auctions/auction_detail.html",
        {
            "auction": auction,
            "photographs": list_photographs(auction),
            "bids": list_bids(auction),
            "form": form,
        },
    )


@login_required
def auction_photographs(request, auction_id):
    """Show the photographs of an auction and receive new ones (FR02)."""
    try:
        auction = find_auction(auction_id)
    except Auction.DoesNotExist:
        raise Http404("La subasta no existe.")

    if request.method != "POST":
        return _render_photograph_page(request, auction, PhotographUploadForm())

    form = PhotographUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return _render_photograph_page(request, auction, form)

    try:
        photographs = add_photographs(auction, form.cleaned_data["images"])
    except TooManyPhotographs as error:
        form.add_error(
            "images",
            f"Solo caben {error.remaining_slots} fotografías más: "
            f"una subasta admite {MAX_PHOTOGRAPHS} en total.",
        )
        return _render_photograph_page(request, auction, form)

    messages.success(request, f"Se subieron {len(photographs)} fotografías.")
    return redirect("auctions:auction_photographs", auction_id=auction.pk)


def _render_photograph_page(request, auction, form):
    """Render the photograph page with the state the seller needs to see."""
    free_slots = count_free_photograph_slots(auction)
    return render(
        request,
        "auctions/photograph_form.html",
        {
            "auction": auction,
            "form": form,
            "photographs": list_photographs(auction),
            "free_slots": free_slots,
            "empty_slots": range(free_slots),
            "max_photographs": MAX_PHOTOGRAPHS,
        },
    )
