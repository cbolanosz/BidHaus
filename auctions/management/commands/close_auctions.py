"""Closes the auctions whose closing date has passed (FR07).

Django has no scheduler of its own, so in production this command is run by
cron. Running it every few seconds is what keeps the 30-second limit of FR07.
Running it twice in a row is harmless: the second run finds nothing to close.
"""

from django.core.management.base import BaseCommand, CommandError

from auctions.services import close_expired_auctions


class Command(BaseCommand):
    help = "Closes every auction whose closing date has already passed."

    def handle(self, *args, **options):
        """Close what can be closed and fail loudly about what cannot.

        Nobody watches a cron job, so a failure that only printed a line would
        go unnoticed. Ending with an error is what makes cron report it.
        """
        closed_auctions, failures = close_expired_auctions()

        for auction in closed_auctions:
            self.stdout.write(f"Closed auction {auction.pk}: {auction.title}")

        for failure in failures:
            self.stderr.write(
                f"Could not close auction {failure.auction.pk} "
                f"({failure.auction.title}): "
                f"{type(failure.error).__name__}: {failure.error}"
            )

        self.stdout.write(
            self.style.SUCCESS(f"{len(closed_auctions)} auction(s) closed.")
        )
        if failures:
            raise CommandError(f"{len(failures)} auction(s) could not be closed.")
