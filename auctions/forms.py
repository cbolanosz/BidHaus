"""Forms of the auctions app: they validate the request, never state changes."""

from django import forms
from django.contrib.auth import get_user_model

from auctions.models import Auction

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
