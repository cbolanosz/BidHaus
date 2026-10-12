"""Errors raised by the services when a business rule is not met."""


class EscrowError(Exception):
    """Base error of the escrow app, so a caller can catch them all at once."""


class AuctionIsNotClosed(EscrowError):
    """Money is only retained once the auction has closed (FR14)."""


class AuctionHasNoWinner(EscrowError):
    """An auction nobody bid on has no payment to retain and no buyer."""


class TransactionAlreadyExists(EscrowError):
    """An auction has at most one escrow transaction (DBR05)."""


class StateChangeIsImmutable(EscrowError):
    """A state change is never modified nor deleted once created (DBR06)."""
