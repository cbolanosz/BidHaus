"""What a test needs in order to read the emails a use case sent."""

from django.core import mail
from django.test import TestCase


def emails_to(address):
    """Return every message sent to that address, in the order they were sent."""
    return [message for message in mail.outbox if address in message.to]


def email_to(address):
    """Return the message sent to that address, or None if none was sent."""
    messages = emails_to(address)
    if not messages:
        return None
    return messages[0]


class NotificationTestCase(TestCase):
    """A test case that lets the emails queued on commit actually go out.

    The notifications are scheduled with transaction.on_commit, and a test runs
    inside a transaction that is rolled back and never committed, so without
    this the callbacks would never run and every mailbox would look empty.
    """

    def deliver(self, action):
        """Perform the action and let the emails it queued go out."""
        with self.captureOnCommitCallbacks(execute=True):
            return action()
