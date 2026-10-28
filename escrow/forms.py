"""Forms of the escrow app: they validate the request, never change state."""

from django import forms

from escrow.models import Dispute


class DisputeForm(forms.ModelForm):
    """What the buyer writes when the item did not arrive as described (FR17).

    Neither the transaction nor who opens the claim are fields: the first comes
    from the address and the second from the session.
    """

    class Meta:
        model = Dispute
        fields = ["description"]
        labels = {"description": "¿Qué pasó con el artículo?"}
        help_texts = {
            "description": (
                "Cuenta en qué se diferencia de lo publicado, o si nunca llegó. "
                "Un administrador lee esto para decidir."
            )
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 6})}
