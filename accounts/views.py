"""HTTP layer: parse the request, call a service, render a template."""

from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.exceptions import (
    AlreadyVerified,
    EmailAlreadyRegistered,
    InvalidCredentials,
    VerificationAlreadyPending,
)
from accounts.forms import LoginForm, SignUpForm, VerificationRequestForm
from accounts.models import VerificationRequest
from accounts.services import (
    authenticate_user,
    find_pending_verification_request,
    find_verification_request,
    list_verification_requests,
    register_visitor,
    submit_verification_request,
)

User = get_user_model()


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


def log_in(request):
    """Show the login form and start the session it describes (FR31)."""
    if request.method != "POST":
        return render(request, "accounts/login.html", {"form": LoginForm()})

    form = LoginForm(request.POST)
    if not form.is_valid():
        return render(request, "accounts/login.html", {"form": form})

    try:
        user = authenticate_user(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
        )
    except InvalidCredentials:
        form.add_error(None, "El correo o la contraseña no coinciden.")
        return render(request, "accounts/login.html", {"form": form})

    login(request, user)
    messages.success(request, f"Hola, {user.full_name}.")
    return redirect(_destination_after_login(request))


@require_POST
@login_required
def log_out(request):
    """End the session of the user who is logged in (FR32).

    Only POST is accepted. Behind a link, any other site could close the
    session of a visitor with an image tag, and a browser that prefetches
    links would close it by accident.
    """
    logout(request)
    messages.success(request, "Cerraste la sesión.")
    return redirect("auctions:catalogue")


@login_required
def verification_request_create(request):
    """Show the verification page and receive the identity document (FR21)."""
    if request.method != "POST":
        return _render_verification_page(request, VerificationRequestForm())

    form = VerificationRequestForm(request.POST, request.FILES)
    if not form.is_valid():
        return _render_verification_page(request, form)

    try:
        submit_verification_request(
            seller=request.user,
            identity_document=form.cleaned_data["identity_document"],
        )
    except AlreadyVerified:
        form.add_error(None, "Tu identidad ya está verificada.")
        return _render_verification_page(request, form)
    except VerificationAlreadyPending:
        form.add_error(None, "Ya tienes una solicitud esperando respuesta.")
        return _render_verification_page(request, form)

    messages.success(
        request,
        "Recibimos tu documento. Un administrador revisará tu solicitud.",
    )
    return redirect("accounts:verification_request")


def _render_verification_page(request, form):
    """Render the verification page with the state the seller needs to see."""
    return render(
        request,
        "accounts/verification_request.html",
        {
            "form": form,
            "pending_request": find_pending_verification_request(request.user),
            "requests": list_verification_requests(request.user),
        },
    )


@login_required
def identity_document(request, request_id):
    """Serve an identity document to an administrator, and to nobody else (DBR08)."""
    if request.user.role != User.Role.ADMINISTRATOR:
        raise PermissionDenied("Solo un administrador puede ver documentos de identidad.")

    try:
        verification_request = find_verification_request(request_id)
    except VerificationRequest.DoesNotExist:
        raise Http404("La solicitud no existe.")

    if not verification_request.identity_document:
        raise Http404("Esta solicitud ya no conserva el documento.")

    return FileResponse(verification_request.identity_document.open("rb"))


def _destination_after_login(request):
    """Return where to send the user, refusing an address outside this site.

    Anyone can put a ?next= in the address bar, so a destination that points
    at another host is discarded instead of followed.
    """
    destination = request.POST.get(REDIRECT_FIELD_NAME)
    if destination and url_has_allowed_host_and_scheme(
        destination, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destination

    return reverse("auctions:catalogue")
