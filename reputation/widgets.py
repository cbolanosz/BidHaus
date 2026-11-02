"""How a score is asked for: a row of stars, not a list of options (FR24)."""

from django import forms


class StarRating(forms.RadioSelect):
    """Radios drawn as five stars that fill up to the one under the cursor.

    The inputs stay in the page, so the keyboard and the form validation keep
    working untouched; only their labels are drawn. The filling is done with
    sibling selectors in CSS, which is why the page needs no script.
    """

    template_name = "reputation/widgets/stars.html"
