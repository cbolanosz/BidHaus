"""Errors raised by the services when a business rule is not met."""


class AuctionError(Exception):
    """Base error of the auctions app, so a caller can catch them all at once."""


class NotASeller(AuctionError):
    """Only a user registered with the seller role may publish an auction."""
