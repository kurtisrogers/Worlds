"""URL configuration for Worlds platform."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("payments/", include("payments.urls")),
    path("integrations/", include("integrations.urls")),
    path("editor/", include("editor.urls")),
    path("engagement/", include("engagement.urls")),
    path("library/", include("library.urls")),
    path("", include("stories.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
