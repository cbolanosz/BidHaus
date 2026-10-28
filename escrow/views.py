"""HTTP layer: parse the request, call a service, render a template."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from escrow.exceptions import (
    NotAParticipant,
    NotTheBuyer,
    TransactionIsNotHeld,
)
from escrow.forms import DisputeForm
from escrow.models import EscrowTransaction
from escrow.services import (
    assert_may_read,
    confirm_reception,
    find_transaction,
    list_state_changes,
    open_dispute,
)

User = get_user_model()


@login_required
def transaction_detail(request, transaction_id):
    """Show the state of the money of a sale and its history (FR15, UR03)."""
    escrow_transaction = _find_transaction_or_404(transaction_id)
    _assert_may_read_or_403(escrow_transaction, request.user)

    return render(
        request,
        "escrow/transaction_detail.html",
        {
            "transaction": escrow_transaction,
            "state_changes": list_state_changes(escrow_transaction),
            "may_confirm": _may_confirm(escrow_transaction, request.user),
            "shows_breakdown": _shows_breakdown(escrow_transaction, request.user),
            "dispute": getattr(escrow_transaction, "dispute", None),
        },
    )


@require_POST
@login_required
def transaction_confirm_reception(request, transaction_id):
    """Register that the buyer received the item (FR15).

    It only answers POST: confirming releases money, and an address a browser
    can follow on its own must never change the state of the system.
    """
    escrow_transaction = _find_transaction_or_404(transaction_id)

    try:
        confirm_reception(escrow_transaction, request.user)
    except NotTheBuyer:
        raise PermissionDenied("Solo el comprador puede confirmar la recepción.")
    except TransactionIsNotHeld:
        messages.warning(request, "Este pago ya no está retenido.")
    else:
        messages.success(
            request,
            "Confirmaste la recepción. El pago se liberó hacia la cuenta del vendedor.",
        )

    return redirect("escrow:transaction_detail", transaction_id=escrow_transaction.pk)


@login_required
def transaction_open_dispute(request, transaction_id):
    """Show the dispute form and register the claim it describes (FR17)."""
    escrow_transaction = _find_transaction_or_404(transaction_id)
    if escrow_transaction.buyer_id != request.user.id:
        raise PermissionDenied("Solo el comprador puede abrir una disputa.")

    if request.method != "POST":
        return _render_dispute_page(request, escrow_transaction, DisputeForm())

    form = DisputeForm(request.POST)
    if not form.is_valid():
        return _render_dispute_page(request, escrow_transaction, form)

    try:
        open_dispute(
            escrow_transaction, request.user, form.cleaned_data["description"]
        )
    except TransactionIsNotHeld:
        form.add_error(
            None,
            "Una disputa solo se abre mientras el dinero está en custodia, "
            "y el de este pago ya no lo está.",
        )
        return _render_dispute_page(request, escrow_transaction, form)

    messages.success(
        request,
        "Abrimos la disputa. El pago queda retenido hasta que un administrador decida.",
    )
    return redirect("escrow:transaction_detail", transaction_id=escrow_transaction.pk)


def _render_dispute_page(request, escrow_transaction, form):
    return render(
        request,
        "escrow/dispute_form.html",
        {"transaction": escrow_transaction, "form": form},
    )


def _find_transaction_or_404(transaction_id):
    try:
        return find_transaction(transaction_id)
    except EscrowTransaction.DoesNotExist:
        raise Http404


def _assert_may_read_or_403(escrow_transaction, user):
    try:
        assert_may_read(escrow_transaction, user)
    except NotAParticipant:
        raise PermissionDenied("Esta transacción es de su comprador y su vendedor.")


def _may_confirm(escrow_transaction, user):
    """Whether this user is the one who can still confirm the reception."""
    return escrow_transaction.is_held and escrow_transaction.buyer_id == user.id


def _shows_breakdown(escrow_transaction, user):
    """Whether this user is owed the detail of the commission (FR20).

    The buyer pays the amount of their bid and nothing else; what the platform
    charges is a matter between BidHaus and the seller, so only the seller and
    an administrator are shown it.
    """
    return (
        escrow_transaction.seller_id == user.id
        or user.role == User.Role.ADMINISTRATOR
    )
