"""HTTP layer: parse the request, call a service, render a template."""

from django.contrib import messages
from django.shortcuts import redirect, render

from auctions.exceptions import NotASeller
from auctions.forms import AuctionForm
from auctions.services import publish_auction


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

    messages.success(request, f"Se publicó la subasta «{auction.title}».")
    return redirect("auctions:auction_create")
