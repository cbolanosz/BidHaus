"""HTTP layer: parse the request, call a service, render a template."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render

from escrow.models import EscrowTransaction
from escrow.services import find_transaction
from reputation.exceptions import AlreadyRated, NotAParticipant, SaleIsNotCompleted
from reputation.forms import RatingForm
from reputation.services import (
    find_counterpart,
    list_sales_to_rate,
    rate_counterpart,
)


@login_required
def sales_to_rate(request):
    """List the completed sales this user has yet to score (FR24)."""
    return render(
        request,
        "reputation/sales_to_rate.html",
        {"sales": list_sales_to_rate(request.user)},
    )


@login_required
def rate(request, transaction_id):
    """Show the rating form of one sale and register the score it carries (FR24)."""
    escrow_transaction = _find_transaction_or_404(transaction_id)
    counterpart = find_counterpart(escrow_transaction, request.user)
    if counterpart is None:
        raise PermissionDenied("Solo las dos partes de una venta se califican.")

    if request.method != "POST":
        return _render_rating_page(request, escrow_transaction, counterpart, RatingForm())

    form = RatingForm(request.POST)
    if not form.is_valid():
        return _render_rating_page(request, escrow_transaction, counterpart, form)

    try:
        rate_counterpart(escrow_transaction, request.user, form.cleaned_data["score"])
    except SaleIsNotCompleted:
        form.add_error(None, "Esta venta todavía no se completó.")
        return _render_rating_page(request, escrow_transaction, counterpart, form)
    except AlreadyRated:
        form.add_error(None, f"Ya calificaste a {counterpart.full_name} por esta venta.")
        return _render_rating_page(request, escrow_transaction, counterpart, form)

    messages.success(request, f"Calificaste a {counterpart.full_name}.")
    return redirect("reputation:sales_to_rate")


def _find_transaction_or_404(transaction_id):
    try:
        return find_transaction(transaction_id)
    except EscrowTransaction.DoesNotExist:
        raise Http404("La venta no existe.")


def _render_rating_page(request, escrow_transaction, counterpart, form):
    return render(
        request,
        "reputation/rate.html",
        {"transaction": escrow_transaction, "counterpart": counterpart, "form": form},
    )
