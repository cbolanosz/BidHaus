"""Errors raised by the services when a business rule is not met."""


class AnalyticsError(Exception):
    """Base error of the analytics app, so a caller can catch them all at once."""


class ScoreAlreadyCalculated(AnalyticsError):
    """An auction carries one trust score, calculated when it was published."""
