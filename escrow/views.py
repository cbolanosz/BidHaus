"""HTTP layer: parse the request, call a service, render a template."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from escrow.exceptions import (
    DisputeIsResolved,
    NoEvidence,
    NotAnAdministrator,
    NotAParticipant,
    NotTheBuyer,
    TooManyEvidenceFiles,
    TransactionIsNotHeld,
)
from escrow.forms import DisputeForm, DisputeResolutionForm, EvidenceUploadForm
from escrow.models import MAX_EVIDENCE_FILES, Dispute, EscrowTransaction, Evidence
from escrow.services import (
    assert_may_read,
    attach_evidence,
    confirm_reception,
    count_free_evidence_slots,
    find_dispute_by_id,
    find_evidence,
    find_transaction,
    list_evidence,
    list_open_disputes,
    list_state_changes,
    open_dispute,
    resolve_dispute,
)

User = get_user_model()


@login_required
def transaction_detail(request, transaction_id):
    """Show the state of the money of a sale and its history (FR15, UR03)."""
    escrow_transaction = _find_transaction_or_404(transaction_id)
    _assert_may_read_or_403(escrow_transaction, request.user)
    dispute = getattr(escrow_transaction, "dispute", None)

    return render(
        request,
        "escrow/transaction_detail.html",
        {
            "transaction": escrow_transaction,
            "state_changes": list_state_changes(escrow_transaction),
            "may_confirm": _may_confirm(escrow_transaction, request.user),
            "shows_breakdown": _shows_breakdown(escrow_transaction, request.user),
            "dispute": dispute,
            "evidence": list_evidence(dispute) if dispute else [],
            "may_resolve": _may_resolve(dispute, request.user),
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


@login_required
def dispute_evidence(request, dispute_id):
    """Show the evidence of a dispute and receive new files (FR18)."""
    dispute = _find_dispute_or_404(dispute_id)
    if dispute.opened_by_id != request.user.id:
        raise PermissionDenied("Solo quien abrió la disputa puede adjuntar pruebas.")

    if request.method != "POST":
        return _render_evidence_page(request, dispute, EvidenceUploadForm())

    form = EvidenceUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return _render_evidence_page(request, dispute, form)

    try:
        attached = attach_evidence(dispute, request.user, form.cleaned_data["files"])
    except DisputeIsResolved:
        form.add_error(None, "Esta disputa ya se resolvió: no admite más pruebas.")
        return _render_evidence_page(request, dispute, form)
    except NoEvidence:
        form.add_error("files", "Elige al menos un archivo para adjuntarlo.")
        return _render_evidence_page(request, dispute, form)
    except TooManyEvidenceFiles as error:
        form.add_error(
            "files",
            f"Solo caben {error.remaining_slots} archivos más: "
            f"una disputa admite {MAX_EVIDENCE_FILES} en total.",
        )
        return _render_evidence_page(request, dispute, form)

    messages.success(request, f"Se adjuntaron {len(attached)} archivos.")
    return redirect("escrow:dispute_evidence", dispute_id=dispute.pk)


@login_required
def evidence_file(request, evidence_id):
    """Serve a file of a dispute to the two sides of the sale and an administrator.

    Evidence is stored outside MEDIA_ROOT precisely so that no address reaches
    it without passing through this check first (DBR07).
    """
    try:
        evidence = find_evidence(evidence_id)
    except Evidence.DoesNotExist:
        raise Http404("La prueba no existe.")

    _assert_may_read_or_403(evidence.dispute.transaction, request.user)
    return FileResponse(evidence.file.open("rb"), filename=evidence.filename)


@login_required
def dispute_queue(request):
    """List the claims waiting for an administrator to decide (FR19)."""
    _assert_is_an_administrator(request.user)

    return render(
        request,
        "escrow/dispute_queue.html",
        {"disputes": list_open_disputes()},
    )


@login_required
def dispute_resolve(request, dispute_id):
    """Show a claim with its evidence and register the decision taken (FR19)."""
    _assert_is_an_administrator(request.user)
    dispute = _find_dispute_or_404(dispute_id)

    if request.method != "POST":
        return _render_resolution_page(request, dispute, DisputeResolutionForm())

    form = DisputeResolutionForm(request.POST)
    if not form.is_valid():
        return _render_resolution_page(request, dispute, form)

    try:
        resolve_dispute(
            dispute,
            request.user,
            outcome=form.cleaned_data["outcome"],
            resolution=form.cleaned_data["resolution"],
        )
    except DisputeIsResolved:
        form.add_error(None, "Esta disputa ya estaba resuelta.")
        return _render_resolution_page(request, dispute, form)

    messages.success(request, "Resolviste la disputa y el dinero se movió.")
    return redirect(
        "escrow:transaction_detail", transaction_id=dispute.transaction_id
    )


def _assert_is_an_administrator(user):
    if user.role != User.Role.ADMINISTRATOR:
        raise PermissionDenied("Solo un administrador resuelve una disputa.")


def _render_resolution_page(request, dispute, form):
    return render(
        request,
        "escrow/dispute_resolve.html",
        {
            "dispute": dispute,
            "transaction": dispute.transaction,
            "evidence": list_evidence(dispute),
            "form": form,
        },
    )


def _render_evidence_page(request, dispute, form):
    """Render the evidence page with the state the buyer needs to see."""
    return render(
        request,
        "escrow/evidence_form.html",
        {
            "dispute": dispute,
            "transaction": dispute.transaction,
            "evidence": list_evidence(dispute),
            "free_slots": count_free_evidence_slots(dispute),
            "form": form,
        },
    )


def _find_dispute_or_404(dispute_id):
    try:
        return find_dispute_by_id(dispute_id)
    except Dispute.DoesNotExist:
        raise Http404("La disputa no existe.")


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


def _may_resolve(dispute, user):
    """Whether this user is the one who can still decide the claim (FR19)."""
    return dispute is not None and dispute.is_open and user.role == User.Role.ADMINISTRATOR


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
