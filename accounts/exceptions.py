"""Errors raised by the services when a business rule is not met."""


class AccountError(Exception):
    """Base error of the accounts app, so a caller can catch them all at once."""


class EmailAlreadyRegistered(AccountError):
    """Another account already uses that email address (DBR01)."""


class InvalidCredentials(AccountError):
    """No active account matches that email and that password."""


class VerificationAlreadyPending(AccountError):
    """The seller already has a request waiting for a decision (DBR08)."""


class AlreadyVerified(AccountError):
    """The identity of this seller has already been verified."""


class NotAnAdministrator(AccountError):
    """Only an administrator decides on a verification request (DBR08)."""


class VerificationAlreadyResolved(AccountError):
    """The request already carries a decision and is not decided twice."""
