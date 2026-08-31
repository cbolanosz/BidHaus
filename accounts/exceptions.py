"""Errors raised by the services when a business rule is not met."""


class AccountError(Exception):
    """Base error of the accounts app, so a caller can catch them all at once."""


class EmailAlreadyRegistered(AccountError):
    """Another account already uses that email address (DBR01)."""
