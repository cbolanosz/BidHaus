"""The email BidHaus sends to the winner of an auction that closes (FR09).

Sending is scheduled with transaction.on_commit, so no message ever announces a
result that the database rolled back a moment later. A mailbox that cannot be
reached is written to the log and forgotten: a bid that was already registered
must not be lost because a mail server is down.
"""

import logging
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)

WON_SUBJECT = "Ganaste la subasta «{title}»"

WON_TEMPLATE = "auctions/email/auction_won.txt"


def notify_auction_result(auction):
    """Tell the winner of a closed auction that they won it (FR09).

    An auction nobody bid on has no winner to write to, so it sends nothing.
    """
    winning_bid = auction.winning_bid
    if winning_bid is None:
        return

    _schedule(
        subject=WON_SUBJECT.format(title=auction.title),
        template=WON_TEMPLATE,
        context={
            "auction": auction,
            "winning_bid": winning_bid,
            "auction_url": _auction_url(auction),
        },
        recipient=winning_bid.bidder.email,
    )


def _auction_url(auction):
    """The absolute address of the auction, so the link in an email is clickable."""
    return urljoin(settings.SITE_URL, reverse("auctions:auction_detail", args=[auction.pk]))


def _schedule(subject, template, context, recipient):
    """Queue one email to go out once the transaction that caused it commits."""
    transaction.on_commit(lambda: _send(subject, template, context, recipient))


def _send(subject, template, context, recipient):
    """Send one plain-text email, and survive a mail server that is not there.

    Every error smtplib raises is an OSError, and so is a connection that is
    refused, so that one clause covers a mail server that is unreachable,
    unauthenticated or simply not running.
    """
    message = EmailMessage(
        subject=subject,
        body=render_to_string(template, context),
        to=[recipient],
    )
    try:
        message.send()
    except OSError:
        logger.exception("BidHaus no pudo enviar «%s» a %s.", subject, recipient)
