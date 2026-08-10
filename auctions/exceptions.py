"""Errors raised by the services when a business rule is not met."""


class AuctionError(Exception):
    """Base error of the auctions app, so a caller can catch them all at once."""


class NotASeller(AuctionError):
    """Only a user registered with the seller role may publish an auction."""


class BidIsImmutable(AuctionError):
    """A bid cannot be modified nor deleted once it is registered (DBR04)."""


class NoPhotographs(AuctionError):
    """An upload must carry at least one photograph."""


class TooManyPhotographs(AuctionError):
    """The upload would push the auction over the maximum number of photographs."""

    def __init__(self, remaining_slots):
        self.remaining_slots = remaining_slots
        super().__init__(f"Only {remaining_slots} photographs still fit in this auction.")
