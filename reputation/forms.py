"""Forms of the reputation app: they validate the request, never change state."""

from django import forms

from reputation.models import MAXIMUM_SCORE, MINIMUM_SCORE
from reputation.widgets import StarRating


class RatingForm(forms.Form):
    """The score one side gives the other after a completed sale (FR24).

    Neither the sale nor who rates are fields: the first comes from the address
    and the second from the session.
    """

    score = forms.TypedChoiceField(
        label="¿Cómo te fue?",
        coerce=int,
        choices=[
            (score, f"{score} de {MAXIMUM_SCORE} estrellas")
            for score in range(MAXIMUM_SCORE, MINIMUM_SCORE - 1, -1)
        ],
        widget=StarRating,
        error_messages={"required": "Elige cuántas estrellas le das."},
    )
