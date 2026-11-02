"""The emails BidHaus sends about an account (FR33).

Sending is scheduled with transaction.on_commit, so no message ever carries a
link that the database rolled back a moment later. A mailbox that cannot be
reached is written to the log and forgotten.
"""

import logging
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)

PASSWORD_RESET_SUBJECT = "Restablece tu contraseña de BidHaus"
PASSWORD_RESET_TEMPLATE = "accounts/email/password_reset.txt"


def send_password_reset_link(user, uidb64, token):
    """Write to the owner of an account with the link that lets them in (FR33).

    The address is built here and not in the view, because the message is read
    outside the browser that asked for it: a relative link would lead nowhere.
    """
    _schedule(
        subject=PASSWORD_RESET_SUBJECT,
        template=PASSWORD_RESET_TEMPLATE,
        context={
            "user": user,
            "reset_url": _reset_url(uidb64, token),
            "hours": settings.PASSWORD_RESET_TIMEOUT // 3600,
        },
        recipient=user.email,
    )


def _reset_url(uidb64, token):
    """The absolute address of the recovery link."""
    return urljoin(
        settings.SITE_URL,
        reverse("accounts:password_reset_confirm", args=[uidb64, token]),
    )


def _schedule(subject, template, context, recipient):
    """Queue one email to go out once the transaction that caused it commits."""
    transaction.on_commit(lambda: _send(subject, template, context, recipient))


def _send(subject, template, context, recipient):
    """Send one plain-text email, and survive a mail server that is not there."""
    message = EmailMessage(
        subject=subject,
        body=render_to_string(template, context),
        to=[recipient],
    )
    try:
        message.send()
    except OSError:
        logger.exception("BidHaus no pudo enviar «%s» a %s.", subject, recipient)
