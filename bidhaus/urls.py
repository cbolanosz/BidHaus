"""Root URL map: the Django admin and the apps of the project."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("escrow/", include("escrow.urls")),
    path("", include("auctions.urls")),
]

# Kept apart from DEBUG on purpose: with DEBUG off the project shows its own
# error pages, and the photographs have to keep loading while it does. The
# route is written by hand because django.conf.urls.static.static() checks
# DEBUG itself and hands back nothing when it is off.
if settings.SERVE_MEDIA_LOCALLY:
    urlpatterns += [
        re_path(
            rf"^{settings.MEDIA_URL.lstrip('/')}(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
