"""Forms of the accounts app: they validate the request, never change state."""

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class SignUpForm(UserCreationForm):
    """Data a visitor fills in to create an account (FR30).

    Django's own creation form is extended instead of rewritten: it already
    asks for the password twice, refuses the two if they differ and runs the
    accepted one through AUTH_PASSWORD_VALIDATORS, which is what SR01 asks for.
    Its save() is never called, because a form validates and a service stores.
    """

    class Meta:
        model = User
        fields = ["full_name", "email"]
