from django.contrib import admin
from django.urls import path

admin.site.site_header = "Raza de Speranță – Administrare"
admin.site.site_title = "RdS Admin"
admin.site.index_title = "Panou de control"

urlpatterns = [
    path("admin/", admin.site.urls),
]
