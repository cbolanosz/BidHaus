"""Use cases of the accounts app. Views call these; they never touch the ORM."""

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction

from accounts.exceptions import EmailAlreadyRegistered, InvalidCredentials

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
