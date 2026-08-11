"""Presentation-only filters for the auction templates."""

from django import template

register = template.Library()


@register.filter
def largest_time_unit(duration):
    """Keep the first unit of a duration: «2 días,3 horas» becomes «2 días».

    The countdown is rendered once, when the page is served, so showing hours
    next to days would claim a precision the page does not have.
    """
    return duration.split(",")[0]
