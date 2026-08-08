"""Forms of the auctions app: they validate the request, never state changes."""

from django import forms
from django.contrib.auth import get_user_model

from auctions.models import MAX_PHOTOGRAPHS, MIN_PHOTOGRAPHS, Auction
from auctions.validators import MAX_PHOTOGRAPH_SIZE_MB, validate_photograph_size

User = get_user_model()

DATETIME_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"


class AuctionForm(forms.ModelForm):
    """Data a seller fills in to publish an auction (FR01).

    The seller is a visible field because sprint 1 has no login yet; it will be
    taken from the session once FR31 is implemented.
    """

    class Meta:
        model = Auction
        fields = ["seller", "category", "title", "description", "condition", "starting_price", "closing_date"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "closing_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format=DATETIME_LOCAL_FORMAT,
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["seller"].queryset = User.objects.sellers()
        self.fields["seller"].empty_label = "Elige un vendedor registrado"
        self.fields["closing_date"].input_formats = [DATETIME_LOCAL_FORMAT]
        self.fields["description"].help_text = "Describe el artículo, su uso y sus defectos."


class MultipleFileInput(forms.ClearableFileInput):
    """The file input Django renders for one file, allowed to take several."""

    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """An image field that validates every file chosen in a single input."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"multiple": True, "accept": "image/*"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        """Validate every chosen file. An empty selection is validated as one
        missing value, so a required field still reports that it is empty."""
        clean_one_image = super().clean
        if not isinstance(data, (list, tuple)):
            data = [data]
        if not data:
            data = [None]
        return [clean_one_image(image, initial) for image in data]


class PhotographUploadForm(forms.Form):
    """Photographs a seller attaches to an auction that already exists (FR02)."""

    images = MultipleImageField(
        label="Fotografías",
        validators=[validate_photograph_size],
        help_text=(
            f"Entre {MIN_PHOTOGRAPHS} y {MAX_PHOTOGRAPHS} imágenes, "
            f"de máximo {MAX_PHOTOGRAPH_SIZE_MB} MB cada una."
        ),
    )
