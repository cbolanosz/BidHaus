"""Errors raised by the services when a business rule is not met."""


class AuctionError(Exception):
    """Base error of the auctions app, so a caller can catch them all at once."""


class NotASeller(AuctionError):
    """Only a user registered with the seller role may publish an auction."""


class BidIsImmutable(AuctionError):
    """A bid cannot be modified nor deleted once it is registered (DBR04)."""


class NotABidder(AuctionError):
    """Only a user registered with the bidder role may place a bid."""


class SellerCannotBid(AuctionError):
    """The seller of an auction may not bid on it (DBR04)."""


class AuctionClosed(AuctionError):
    """The auction no longer accepts bids, because it is closed or expired."""


class BidTooLow(AuctionError):
    """The amount does not beat the current price of the auction (DBR04)."""

    def __init__(self, current_price):
        self.current_price = current_price
        super().__init__(f"The bid must be higher than {current_price}.")


class BiddingIsBusy(AuctionError):
    """Concurrent bids kept the auction locked for longer than we wait."""


class NoPhotographs(AuctionError):
    """An upload must carry at least one photograph."""


class TooManyPhotographs(AuctionError):
    """The upload would push the auction over the maximum number of photographs."""

    def __init__(self, remaining_slots):
        self.remaining_slots = remaining_slots
        super().__init__(f"Only {remaining_slots} photographs still fit in this auction.")
