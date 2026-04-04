from django.contrib import admin

from .models import Child, Document, Parent, Therapist, Therapy


# ──────────────────────────────────────────────────────────────────────────────
# Inlines  (show related rows inside the parent form)
# ──────────────────────────────────────────────────────────────────────────────
class ChildInline(admin.TabularInline):
    model = Child
    extra = 0
    fields = ("first_name", "last_name", "age", "child_type", "sex", "diagnostic")
    show_change_link = True


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1
    fields = ("name", "exists", "creation_date", "expiry_date")


class TherapyInlineForChild(admin.TabularInline):
    """Therapies shown inside the Child form."""
    model = Therapy
    extra = 0
    fields = ("therapist", "date", "start_time", "duration")
    show_change_link = True


class TherapyInlineForTherapist(admin.TabularInline):
    """Therapies shown inside the Therapist form."""
    model = Therapy
    extra = 0
    fields = ("child", "date", "start_time", "duration")
    show_change_link = True


# ──────────────────────────────────────────────────────────────────────────────
# Model Admins
# ──────────────────────────────────────────────────────────────────────────────
@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "phone_number", "email", "children_count")
    search_fields = ("first_name", "last_name", "phone_number", "email")
    inlines = [ChildInline]

    @admin.display(description="# Children")
    def children_count(self, obj):
        return obj.children.count()


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "age",
        "child_type",
        "sex",
        "parent",
        "docs_count",
        "therapies_count",
    )
    list_filter = ("child_type", "sex")
    search_fields = ("first_name", "last_name", "diagnostic")
    autocomplete_fields = ("parent",)
    inlines = [DocumentInline, TherapyInlineForChild]

    @admin.display(description="Docs")
    def docs_count(self, obj):
        return obj.documents.count()

    @admin.display(description="Therapies")
    def therapies_count(self, obj):
        return obj.therapies.count()


@admin.register(Therapist)
class TherapistAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "therapies_count")
    search_fields = ("first_name", "last_name")
    inlines = [TherapyInlineForTherapist]

    @admin.display(description="Total sessions")
    def therapies_count(self, obj):
        return obj.therapies.count()


@admin.register(Therapy)
class TherapyAdmin(admin.ModelAdmin):
    list_display = ("child", "therapist", "date", "start_time", "duration")
    list_filter = ("date", "therapist")
    search_fields = (
        "child__first_name",
        "child__last_name",
        "therapist__first_name",
        "therapist__last_name",
    )
    autocomplete_fields = ("child", "therapist")
    date_hierarchy = "date"


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "child", "exists", "creation_date", "expiry_date")
    list_filter = ("exists",)
    search_fields = ("name", "child__first_name", "child__last_name")
    autocomplete_fields = ("child",)
