from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.views.static import serve

from core.admin import admin_site

urlpatterns = [
    path("admin/", admin_site.urls),
    # Serve media files in both dev and production
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
]
