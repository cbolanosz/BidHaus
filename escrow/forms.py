"""Forms of the escrow app: they validate the request, never change state."""

from django import forms

from escrow.models import MAX_EVIDENCE_FILES, Dispute
from escrow.validators import (
    EVIDENCE_EXTENSIONS,
    MAX_EVIDENCE_SIZE_MB,
    validate_evidence_size,
)


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


class MultipleFileInput(forms.ClearableFileInput):
    """The file input Django renders for one file, allowed to take several."""

    allow_multiple_selected = True


class MultipleEvidenceField(forms.FileField):
    """A file field that validates every file chosen in a single input."""

    def __init__(self, *args, **kwargs):
        accepted = ",".join(f".{extension}" for extension in EVIDENCE_EXTENSIONS)
        kwargs.setdefault(
            "widget", MultipleFileInput(attrs={"multiple": True, "accept": accepted})
        )
        kwargs.setdefault("validators", [validate_evidence_size])
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        """Validate every chosen file. An empty selection is validated as one
        missing value, so a required field still reports that it is empty."""
        clean_one_file = super().clean
        if not isinstance(data, (list, tuple)):
            data = [data]
        if not data:
            data = [None]
        return [clean_one_file(uploaded_file, initial) for uploaded_file in data]


class EvidenceUploadForm(forms.Form):
    """The files a buyer attaches to a dispute already open (FR18)."""

    files = MultipleEvidenceField(
        label="Pruebas",
        help_text=(
            f"Hasta {MAX_EVIDENCE_FILES} archivos en "
            f"{', '.join(EVIDENCE_EXTENSIONS)}, de máximo "
            f"{MAX_EVIDENCE_SIZE_MB} MB cada uno. "
            "Solo los ve el vendedor y un administrador."
        ),
        error_messages={"required": "Elige al menos un archivo para adjuntarlo."},
    )
