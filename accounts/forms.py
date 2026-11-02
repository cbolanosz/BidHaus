"""Forms of the accounts app: they validate the request, never change state."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm

from accounts.models import VerificationRequest
from accounts.validators import DOCUMENT_EXTENSIONS, MAX_DOCUMENT_SIZE_MB

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


class LoginForm(forms.Form):
    """Credentials a registered user types to start a session (FR31).

    The password is not stripped: a leading or trailing space belongs to it.
    """

    email = forms.EmailField(label="Correo electrónico")
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class VerificationRequestForm(forms.ModelForm):
    """The identity document a seller sends to be verified (FR21).

    The seller is not a field: it is the user in session.
    """

    class Meta:
        model = VerificationRequest
        fields = ["identity_document"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["identity_document"].required = True
        self.fields["identity_document"].help_text = (
            f"Cédula o pasaporte en {', '.join(DOCUMENT_EXTENSIONS)}, "
            f"de máximo {MAX_DOCUMENT_SIZE_MB} MB. "
            "Se elimina en cuanto se resuelve la solicitud."
        )


class PasswordResetRequestForm(forms.Form):
    """The address a user who forgot their password types (FR33)."""

    email = forms.EmailField(
        label="Correo electrónico",
        help_text="Te enviamos un enlace para elegir una contraseña nueva.",
    )


class SetNewPasswordForm(SetPasswordForm):
    """The new password chosen from a recovery link (FR33).

    Django's own form is extended instead of rewritten: it asks for the
    password twice, refuses the two if they differ, and runs the accepted one
    through AUTH_PASSWORD_VALIDATORS, which is the same gate sign-up uses.
    Its save() is never called, because a form validates and a service stores.
    """
