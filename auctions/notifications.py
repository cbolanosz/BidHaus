"""The emails BidHaus sends when an auction closes (FR09, FR10).

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
SELLER_RESULT_SUBJECT = "Cerró tu subasta «{title}»"

WON_TEMPLATE = "auctions/email/auction_won.txt"
SELLER_RESULT_TEMPLATE = "auctions/email/auction_result_seller.txt"


def notify_auction_result(auction):
    """Tell the winner and the seller how the auction ended (FR09, FR10).

    Both messages are queued in the same call because both describe the same
    fact, the auction closing. An auction nobody bid on has no winner to write
    to, so only the seller hears about it.
    """
    winning_bid = auction.winning_bid
    context = {
        "auction": auction,
        "winning_bid": winning_bid,
        "auction_url": _auction_url(auction),
    }

    if winning_bid is not None:
        _schedule(
            subject=WON_SUBJECT.format(title=auction.title),
            template=WON_TEMPLATE,
            context=context,
            recipient=winning_bid.bidder.email,
        )

    _schedule(
        subject=SELLER_RESULT_SUBJECT.format(title=auction.title),
        template=SELLER_RESULT_TEMPLATE,
        context=context,
        recipient=auction.seller.email,
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
