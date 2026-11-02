"""Errors raised by the services when a business rule is not met."""


class ReputationError(Exception):
    """Base error of the reputation app, so a caller can catch them all at once."""


class SaleIsNotCompleted(ReputationError):
    """Only a sale that went through is rated: there is nothing to judge before."""


class NotAParticipant(ReputationError):
    """Only the two sides of a sale rate each other (DBR09)."""


class AlreadyRated(ReputationError):
    """Each participant rates the other once per sale, and the score stands."""
