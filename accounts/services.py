"""Use cases of the accounts app. Views call these; they never touch the ORM."""

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.exceptions import (
    AlreadyVerified,
    EmailAlreadyRegistered,
    InvalidCredentials,
    NotAnAdministrator,
    VerificationAlreadyPending,
    VerificationAlreadyResolved,
)
from accounts.models import VerificationRequest

User = get_user_model()


@transaction.atomic
def register_visitor(email, full_name, password):
    """Create the account a visitor needs before placing a bid (FR30).

    The account starts with the bidder role: publishing requires the seller
    role, which an administrator grants after verifying an identity document.
    The email is compared without regard to case, because two addresses that
    differ only in capitalisation are the same mailbox to the person typing it.
    """
    if User.objects.filter(email__iexact=email).exists():
        raise EmailAlreadyRegistered

    return User.objects.create_user(
        email=email,
        full_name=full_name,
        password=password,
        role=User.Role.BIDDER,
    )


def authenticate_user(email, password):
    """Return the registered user those credentials identify (FR31).

    Django compares the password against the stored hash and refuses an
    account that is not active. An unknown email and a wrong password fail
    the same way on purpose: distinguishing them would tell a stranger which
    addresses are registered.
    """
    user = authenticate(email=email, password=password)
    if user is None:
        raise InvalidCredentials

    return user


@transaction.atomic
def submit_verification_request(seller, identity_document):
    """Send an identity document so an administrator can verify a seller (FR21).

    Any registered user may ask: the seller role is what the approval grants,
    not what it requires. Only one request waits at a time, so a rejected
    seller can try again but nobody can queue two (DBR08).
    """
    if seller.is_verified:
        raise AlreadyVerified
    if find_pending_verification_request(seller) is not None:
        raise VerificationAlreadyPending

    verification_request = VerificationRequest(
        seller=seller,
        identity_document=identity_document,
        state=VerificationRequest.State.PENDING,
    )
    verification_request.full_clean()
    verification_request.save()
    return verification_request


def find_pending_verification_request(seller):
    """Return the request this seller is waiting on, or None."""
    return seller.verification_requests.filter(
        state=VerificationRequest.State.PENDING
    ).first()


def list_verification_requests(seller):
    """Return every request this seller has sent, most recent first."""
    return seller.verification_requests.all()


def find_verification_request(request_id):
    """Return that request, or raise VerificationRequest.DoesNotExist."""
    return VerificationRequest.objects.select_related("seller").get(pk=request_id)


@transaction.atomic
def approve_verification_request(verification_request, administrator):
    """Trust the identity of a seller and let them publish (FR23).

    Approving is what turns a bidder into a seller: the role and the badge are
    granted here, in the same transaction as the decision, so an approved
    request and an account that cannot publish never coexist.
    """
    seller = _resolve(
        verification_request, administrator, VerificationRequest.State.APPROVED
    )
    seller.role = User.Role.SELLER
    seller.is_verified = True
    seller.save(update_fields=["role", "is_verified"])
    return verification_request


@transaction.atomic
def reject_verification_request(verification_request, administrator):
    """Refuse the identity a seller claimed (FR23).

    The account is left exactly as it was, so a rejected seller keeps bidding
    and may send a new document.
    """
    _resolve(verification_request, administrator, VerificationRequest.State.REJECTED)
    return verification_request


def _resolve(verification_request, administrator, state):
    """Record who decided what and when, and destroy the document (DBR08).

    The identity document is deleted as soon as the decision exists: it was
    read to decide, and keeping it afterwards has no purpose that justifies
    holding somebody's identity papers.
    """
    if administrator.role != User.Role.ADMINISTRATOR:
        raise NotAnAdministrator
    if not verification_request.is_pending:
        raise VerificationAlreadyResolved

    verification_request.state = state
    verification_request.resolved_by = administrator
    verification_request.resolved_at = timezone.now()
    verification_request.save(update_fields=["state", "resolved_by", "resolved_at"])
    verification_request.identity_document.delete(save=True)

    return verification_request.seller
