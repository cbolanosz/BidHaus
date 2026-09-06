"""Administration of users and of the requests to verify their identity."""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html

from accounts.exceptions import AccountError
from accounts.models import User, VerificationRequest
from accounts.services import approve_verification_request, reject_verification_request


@admin.register(User)
class BidHausUserAdmin(UserAdmin):
    """Django's user admin, adapted to an email-based account."""

    ordering = ["email"]
    list_display = ["email", "full_name", "role", "is_verified", "is_staff"]
    list_filter = ["role", "is_verified", "is_staff"]
    search_fields = ["email", "full_name"]

    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Perfil", {"fields": ["full_name", "role", "is_verified"]}),
        ("Permisos", {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
        ("Fechas", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (None, {"fields": ["email", "full_name", "role", "password1", "password2"]}),
    ]


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    """Where an administrator reads an identity document (DBR08).

    The file is never linked through MEDIA_URL, because it is not a public
    file: the link points at the view that checks the role first.
    """

    list_display = ["seller", "state", "submitted_at", "resolved_by", "resolved_at"]
    list_filter = ["state"]
    search_fields = ["seller__email", "seller__full_name"]
    actions = ["approve", "reject"]

    # The decision is taken with the two actions, never by editing the row: a
    # state written by hand would not grant the role nor delete the document.
    readonly_fields = [
        "seller",
        "identity_document",
        "state",
        "submitted_at",
        "resolved_by",
        "resolved_at",
        "document_link",
    ]

    @admin.display(description="documento")
    def document_link(self, verification_request):
        """Link to the document, or say it is gone once the request is resolved."""
        if not verification_request.identity_document:
            return "Eliminado tras resolver la solicitud."

        url = reverse(
            "accounts:identity_document", args=[verification_request.pk]
        )
        return format_html('<a href="{}" target="_blank">Ver documento</a>', url)

    @admin.action(description="Aprobar la verificación de identidad")
    def approve(self, request, queryset):
        """Approve every selected request (FR23)."""
        self._resolve_each(request, queryset, approve_verification_request, "aprobaron")

    @admin.action(description="Rechazar la verificación de identidad")
    def reject(self, request, queryset):
        """Reject every selected request (FR23)."""
        self._resolve_each(request, queryset, reject_verification_request, "rechazaron")

    def _resolve_each(self, request, queryset, resolve, past_tense):
        """Run one decision per selected row and report what happened.

        A request that is already resolved is reported instead of silently
        skipped, so an administrator never wonders which rows were touched.
        """
        resolved = 0
        for verification_request in queryset:
            try:
                resolve(verification_request, request.user)
            except AccountError:
                self.message_user(
                    request,
                    f"«{verification_request.seller}» ya tenía una decisión.",
                    messages.WARNING,
                )
            else:
                resolved += 1

        if resolved:
            self.message_user(request, f"Se {past_tense} {resolved} solicitudes.")
