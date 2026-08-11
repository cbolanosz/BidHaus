"""Closes the auctions whose closing date has passed (FR07).

Django has no scheduler of its own, so in production this command is run by
cron. Running it every few seconds is what keeps the 30-second limit of FR07.
Running it twice in a row is harmless: the second run finds nothing to close.
"""

from django.core.management.base import BaseCommand

from auctions.services import close_expired_auctions


class Command(BaseCommand):
    help = "Closes every auction whose closing date has already passed."

    def handle(self, *args, **options):
        closed_auctions = close_expired_auctions()

        for auction in closed_auctions:
            self.stdout.write(f"Closed auction {auction.pk}: {auction.title}")

        self.stdout.write(
            self.style.SUCCESS(f"{len(closed_auctions)} auction(s) closed.")
        )
