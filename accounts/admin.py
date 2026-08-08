"""Seeding of users while there is no sign-up screen (sprint 1)."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


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
