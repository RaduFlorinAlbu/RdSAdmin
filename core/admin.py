from django.contrib import admin
from django.urls import path

from .models import Child, Document, Parent, Therapist, Therapy


class RdsAdminSite(admin.AdminSite):
    site_header = "Raza de Speranță – Admin"
    site_title = "RdS Admin"
    index_title = "Dashboard"

    def get_urls(self):
        from .views import TherapyBatchView
        custom = [
            path(
                "core/therapy/batch/",
                self.admin_view(TherapyBatchView.as_view()),
                name="therapy_batch",
            ),
        ]
        return custom + super().get_urls()

    def each_context(self, request):
        ctx = super().each_context(request)
        ctx["batch_therapy_url"] = "core/therapy/batch/"
        return ctx


admin_site = RdsAdminSite(name="admin")


# ──────────────────────────────────────────────────────────────────────────────
# Inlines  (show related rows inside the parent form)
# ──────────────────────────────────────────────────────────────────────────────
class ChildInline(admin.TabularInline):
    model = Child
    extra = 0
    fields = ("first_name", "last_name", "cnp", "_varsta", "_tip_copil", "_sex", "status", "diagnostic")
    readonly_fields = ("_varsta", "_tip_copil", "_sex")
    show_change_link = True

    @admin.display(description="Vârstă")
    def _varsta(self, obj):
        if not obj.cnp:
            return "Necalculat"
        return obj.age

    @admin.display(description="Tip")
    def _tip_copil(self, obj):
        if not obj.cnp:
            return "Necalculat"
        return obj.get_child_type_display()

    @admin.display(description="Sex")
    def _sex(self, obj):
        if not obj.cnp:
            return "Nestabilit"
        return obj.get_sex_display()


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1
    fields = ("name", "exists", "creation_date", "expiry_date")


class TherapyInlineForChild(admin.TabularInline):
    """Therapies shown inside the Child form."""
    model = Therapy
    extra = 0
    fields = ("therapist", "date", "start_time")
    show_change_link = True


class TherapyInlineForTherapist(admin.TabularInline):
    """Therapies shown inside the Therapist form."""
    model = Therapy
    extra = 0
    fields = ("child", "date", "start_time")
    show_change_link = True


# ──────────────────────────────────────────────────────────────────────────────
# Model Admins
# ──────────────────────────────────────────────────────────────────────────────
@admin.register(Parent, site=admin_site)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "phone_number", "email", "children_count")
    search_fields = ("first_name", "last_name", "phone_number", "email")
    inlines = [ChildInline]

    @admin.display(description="Nr. copii activi")
    def children_count(self, obj):
        return obj.children.filter(status="activ").count()


@admin.register(Child, site=admin_site)
class ChildAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "cnp",
        "_varsta",
        "_tip_copil",
        "_sex",
        "status",
        "parent",
        "docs_count",
        "therapies_count",
    )
    list_filter = ("child_type", "sex", "status", "diagnostic")
    search_fields = ("first_name", "last_name", "cnp")
    autocomplete_fields = ("parent",)
    readonly_fields = ("_varsta", "_tip_copil", "_sex")
    fields = (
        "first_name", "last_name", "cnp", "_varsta", "_tip_copil",
        "_sex", "status", "diagnostic", "parent",
    )
    inlines = [DocumentInline]

    @admin.display(description="Vârstă")
    def _varsta(self, obj):
        if not obj.cnp:
            return "Necalculat"
        return obj.age

    @admin.display(description="Tip")
    def _tip_copil(self, obj):
        if not obj.cnp:
            return "Necalculat"
        return obj.get_child_type_display()

    @admin.display(description="Sex")
    def _sex(self, obj):
        if not obj.cnp:
            return "Nestabilit"
        return obj.get_sex_display()

    @admin.display(description="Documente")
    def docs_count(self, obj):
        return obj.documents.count()

    @admin.display(description="Ședințe")
    def therapies_count(self, obj):
        return obj.therapies.count()


@admin.register(Therapist, site=admin_site)
class TherapistAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "therapies_count")
    search_fields = ("first_name", "last_name")
    inlines = []

    @admin.display(description="Total ședințe")
    def therapies_count(self, obj):
        return obj.therapies.count()


@admin.register(Therapy, site=admin_site)
class TherapyAdmin(admin.ModelAdmin):
    list_display = ("child", "therapist", "date", "start_time")
    list_filter = ("date", "therapist")
    search_fields = (
        "child__first_name",
        "child__last_name",
        "therapist__first_name",
        "therapist__last_name",
    )
    autocomplete_fields = ("child", "therapist")
    date_hierarchy = "date"


@admin.register(Document, site=admin_site)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "child", "exists", "creation_date", "expiry_date")
    list_filter = ("exists",)
    search_fields = ("name", "child__first_name", "child__last_name")
    autocomplete_fields = ("child",)
