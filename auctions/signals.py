"""The facts the auctions app announces, for other apps to react to.

An app that reacts to an auction already depends on this one through its
foreign keys. Announcing instead of calling keeps the dependency pointing in
that single direction: `auctions` never imports `escrow` or `analytics`, so a
new listener can be added without touching anything here.
"""

from django.dispatch import Signal

# Both are sent inside the transaction that caused them, so whatever a listener
# writes is committed with the fact or rolled back with it.
auction_published = Signal()
auction_closed = Signal()
