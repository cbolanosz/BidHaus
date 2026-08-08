"""HTTP layer: parse the request, call a service, render a template."""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render

from auctions.exceptions import NotASeller, TooManyPhotographs
from auctions.forms import AuctionForm, AuctionSearchForm, PhotographUploadForm
from auctions.models import MAX_PHOTOGRAPHS, Auction
from auctions.services import (
    add_photographs,
    count_free_photograph_slots,
    find_auction,
    list_photographs,
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


def auction_create(request):
    """Show the publication form and publish the auction it describes (FR01)."""
    if request.method != "POST":
        return render(request, "auctions/auction_form.html", {"form": AuctionForm()})

    form = AuctionForm(request.POST)
    if not form.is_valid():
        return render(request, "auctions/auction_form.html", {"form": form})

    try:
        auction = publish_auction(
            seller=form.cleaned_data["seller"],
            category=form.cleaned_data["category"],
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            condition=form.cleaned_data["condition"],
            starting_price=form.cleaned_data["starting_price"],
            closing_date=form.cleaned_data["closing_date"],
        )
    except NotASeller:
        form.add_error("seller", "Solo un vendedor registrado puede publicar una subasta.")
        return render(request, "auctions/auction_form.html", {"form": form})

    messages.success(request, f"Se publicó la subasta «{auction.title}». Ahora añade sus fotografías.")
    return redirect("auctions:auction_photographs", auction_id=auction.pk)


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
    return render(
        request,
        "auctions/photograph_form.html",
        {
            "auction": auction,
            "form": form,
            "photographs": list_photographs(auction),
            "free_slots": count_free_photograph_slots(auction),
            "max_photographs": MAX_PHOTOGRAPHS,
        },
    )
