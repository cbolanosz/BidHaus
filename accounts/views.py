"""HTTP layer: parse the request, call a service, render a template."""

from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.exceptions import EmailAlreadyRegistered
from accounts.forms import SignUpForm
from accounts.services import register_visitor


def sign_up(request):
    """Show the sign-up form and create the account it describes (FR30)."""
    if request.method != "POST":
        return render(request, "accounts/signup.html", {"form": SignUpForm()})

    form = SignUpForm(request.POST)
    if not form.is_valid():
        return render(request, "accounts/signup.html", {"form": form})

    try:
        user = register_visitor(
            email=form.cleaned_data["email"],
            full_name=form.cleaned_data["full_name"],
            password=form.cleaned_data["password1"],
        )
    except EmailAlreadyRegistered:
        form.add_error("email", "Ya existe una cuenta con este correo electrónico.")
        return render(request, "accounts/signup.html", {"form": form})

    messages.success(request, f"Se creó la cuenta de {user.full_name}.")
    return redirect("auctions:catalogue")
