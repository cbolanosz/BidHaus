"""Forms of the auctions app: they validate the request, never state changes."""

from django import forms
from django.contrib.auth import get_user_model

from auctions.models import (
    MAX_PHOTOGRAPHS,
    MIN_PHOTOGRAPHS,
    MINIMUM_PRICE,
    Auction,
    Category,
)
from auctions.validators import MAX_PHOTOGRAPH_SIZE_MB, validate_photograph_size

User = get_user_model()

DATETIME_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"


class MultipleFileInput(forms.ClearableFileInput):
    """The file input Django renders for one file, allowed to take several."""

    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """An image field that validates every file chosen in a single input."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"multiple": True, "accept": "image/*"}))
        kwargs.setdefault("validators", [validate_photograph_size])
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


class AuctionForm(forms.ModelForm):
    """Data a seller fills in to publish an auction (FR01).

    The first photographs are asked for here so that no auction is ever stored
    without one, which is what DBR03 requires. The rest, up to MAX_PHOTOGRAPHS,
    are added afterwards on the photograph page.

    The seller is a visible field because sprint 1 has no login yet; it will be
    taken from the session once FR31 is implemented.
    """

    images = MultipleImageField(
        label="Fotografías",
        help_text=(
            f"Al menos {MIN_PHOTOGRAPHS}, de máximo {MAX_PHOTOGRAPH_SIZE_MB} MB cada una. "
            f"Después podrás añadir el resto, hasta {MAX_PHOTOGRAPHS}."
        ),
    )

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
        self.fields["category"].empty_label = "Elige una categoría"
        self.fields["condition"].choices = [("", "Elige el estado")] + Auction.Condition.choices
        self.fields["closing_date"].input_formats = [DATETIME_LOCAL_FORMAT]
        self.fields["description"].help_text = "Describe el artículo, su uso y sus defectos."


class AuctionSearchForm(forms.Form):
    """Filters a visitor applies to the catalogue (FR03). Every field is optional."""

    text = forms.CharField(label="Buscar", max_length=120, required=False)
    category = forms.ModelChoiceField(
        label="Categoría",
        queryset=Category.objects.all(),
        required=False,
        empty_label="Todas",
    )
    condition = forms.ChoiceField(
        label="Estado del artículo",
        choices=[("", "Cualquiera")] + Auction.Condition.choices,
        required=False,
    )
    minimum_price = forms.DecimalField(
        label="Precio desde", min_value=0, decimal_places=2, required=False
    )
    maximum_price = forms.DecimalField(
        label="Precio hasta", min_value=0, decimal_places=2, required=False
    )

    def clean(self):
        """Reject a price range whose lower end is above its upper end."""
        cleaned_data = super().clean()
        minimum_price = cleaned_data.get("minimum_price")
        maximum_price = cleaned_data.get("maximum_price")

        if minimum_price is not None and maximum_price is not None and minimum_price > maximum_price:
            self.add_error("maximum_price", "El precio máximo debe ser mayor que el mínimo.")

        return cleaned_data


class BidForm(forms.Form):
    """The amount a bidder offers for an auction (FR05).

    The bidder is a visible field because sprint 1 has no login yet; it will be
    taken from the session once FR31 is implemented.
    """

    bidder = forms.ModelChoiceField(
        label="Pujador",
        queryset=User.objects.bidders(),
        empty_label="Elige un pujador registrado",
    )
    amount = forms.DecimalField(
        label="Tu puja (COP)", max_digits=12, decimal_places=2, min_value=MINIMUM_PRICE
    )


class PhotographUploadForm(forms.Form):
    """Photographs a seller attaches to an auction that already exists (FR02)."""

    images = MultipleImageField(
        label="Fotografías",
        help_text=(
            f"Entre {MIN_PHOTOGRAPHS} y {MAX_PHOTOGRAPHS} imágenes, "
            f"de máximo {MAX_PHOTOGRAPH_SIZE_MB} MB cada una."
        ),
    )
