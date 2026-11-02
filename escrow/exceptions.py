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


class NotTheBuyer(EscrowError):
    """Only the buyer of a transaction may confirm that they received (FR15)."""


class NotAParticipant(EscrowError):
    """A transaction is readable by its buyer, its seller and an administrator."""


class TransactionIsNotHeld(EscrowError):
    """The money of this transaction has already moved: there is nothing to confirm."""


class DisputeIsResolved(EscrowError):
    """A dispute an administrator already decided takes no more evidence (FR18)."""


class NoEvidence(EscrowError):
    """Attaching nothing is not attaching evidence (FR18)."""


class TooManyEvidenceFiles(EscrowError):
    """The upload would push the dispute over the maximum number of files."""

    def __init__(self, remaining_slots):
        self.remaining_slots = remaining_slots
        super().__init__(f"Only {remaining_slots} evidence files still fit in this dispute.")


class NotAnAdministrator(EscrowError):
    """Only an administrator arbitrates between a buyer and a seller (FR19)."""


class UnknownOutcome(EscrowError):
    """A dispute ends with the money released or refunded, and nothing else."""
