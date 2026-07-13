from datetime import date, timedelta

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.urls import path
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Centru, Child, Document, Parent, Therapist, Therapy, TherapistDocument


# ──────────────────────────────────────────────────────────────────────────────
# Custom expiry-date widget with +6 luni / +1 an quick buttons
# ──────────────────────────────────────────────────────────────────────────────

_EXPIRY_ONCE_SCRIPT = (
    '<script>'
    'if(!window._expiryQuickDefined){'
    'window._expiryQuickDefined=true;'
    # btn = the button element; months = 6 or 12
    # Finds expiry/creation inputs by traversing to nearest TR (works for any row index)
    'window.expiryQuick=function(btn,months){'
    'var tr=btn.closest("tr")||btn.closest("fieldset")||btn.parentElement;'
    'var inp=tr.querySelector("input[name$=\'expiry_date\']");'
    'if(!inp)return;'
    'var ciInp=tr.querySelector("input[name$=\'creation_date\']");'
    'var base=null;'
    # Use current expiry as base (for renewal)
    'if(inp.value){'
    'var p=inp.value.split(".");'
    'if(p.length===3){base=new Date(parseInt(p[2]),parseInt(p[1])-1,parseInt(p[0]));'
    'if(isNaN(base.getTime()))base=null;}}'
    # Fall back to creation_date
    'if(!base&&ciInp&&ciInp.value){'
    'var cp=ciInp.value.split(".");'
    'if(cp.length===3){base=new Date(parseInt(cp[2]),parseInt(cp[1])-1,parseInt(cp[0]));'
    'if(isNaN(base.getTime()))base=null;}}'
    # Fall back to today
    'if(!base)base=new Date();'
    'base.setMonth(base.getMonth()+months);'
    'var y=base.getFullYear();'
    'var m=String(base.getMonth()+1).padStart(2,"0");'
    'var day=String(base.getDate()).padStart(2,"0");'
    'inp.value=day+"."+m+"."+y;'
    'inp.dispatchEvent(new Event("change",{bubbles:true}));'
    '}}'
    '</script>'
)


class ExpiryDateWidget(AdminDateWidget):
    """AdminDateWidget cu butoane rapide +6 luni / +1 an."""

    def render(self, name, value, attrs=None, renderer=None):
        base = super().render(name, value, attrs, renderer)
        btn_style = (
            'display:inline-block;width:52px;text-align:center;'
            'padding:2px 0;font-size:12px;background:#318CE7;color:#fff;'
            'border:none;border-radius:3px;cursor:pointer;margin-left:4px;'
        )
        # Pass `this` (the button) so expiryQuick traverses DOM — no ID dependency
        buttons = (
            f'<button type="button" style="{btn_style}" '
            f'onclick="expiryQuick(this,6)">+6 luni</button>'
            f'<button type="button" style="{btn_style}" '
            f'onclick="expiryQuick(this,12)">+1 an</button>'
        )
        return mark_safe(base + buttons + _EXPIRY_ONCE_SCRIPT)


# ──────────────────────────────────────────────────────────────────────────────
# Document name widget — dropdown with two presets + free-text fallback
# ──────────────────────────────────────────────────────────────────────────────

_PREDEFINED_NAMES = ["Certificat de naștere", "Scrisoare Medicală"]
_CUSTOM_SENTINEL  = "__custom__"

_DOC_NAME_SCRIPT = (
    '<script>'
    'if(!window._docNameDefined){'
    'window._docNameDefined=true;'
    # sel = the <select>; finds text input as sibling inside same <div> — no ID dependency
    'window.docNameChange=function(sel){'
    'var CERT="Certificat de na\u0219tere";'
    'var CUSTOM="__custom__";'
    'var div=sel.parentElement;'
    'var textEl=div?div.querySelector("input[type=\'text\']"):null;'
    'if(!textEl)return;'
    'textEl.style.display=sel.value===CUSTOM?"":"none";'
    'if(sel.value===CUSTOM)textEl.focus();'
    # locate expiry input in same <tr> (inline) or standalone form
    'var tr=sel.closest("tr");'
    'var exp=tr?tr.querySelector("input[name$=\'expiry_date\']")'
    ':document.querySelector("input[name$=\'expiry_date\']");'
    'if(exp){'
    'var isCert=sel.value===CERT;'
    'exp.disabled=isCert;'
    'exp.style.opacity=isCert?"0.4":"";'
    'if(isCert)exp.value="";'
    'var cont=exp.parentElement;'
    'while(cont&&!cont.querySelector("button"))cont=cont.parentElement;'
    'if(cont)cont.querySelectorAll("button").forEach(function(b){'
    'b.disabled=isCert;b.style.opacity=isCert?"0.4":"";});'
    '}}'
    '}'
    '</script>'
)

_SEL_STYLE = (
    'width:100%;padding:5px 8px;border:1px solid #ccc;'
    'border-radius:4px;font-size:14px;'
)
_TXT_STYLE = (
    'width:100%;box-sizing:border-box;'
    'padding:5px 8px;border:1px solid #ccc;border-radius:4px;font-size:14px;'
)


class DocumentNameWidget(forms.Widget):

    def render(self, name, value, attrs=None, renderer=None):
        value = value or ''
        is_preset   = value in _PREDEFINED_NAMES
        select_val  = value if is_preset else (_CUSTOM_SENTINEL if value else '')
        text_val    = '' if is_preset else value

        input_id  = (attrs or {}).get('id', f'id_{name}')
        select_id = f'{input_id}_select'
        text_id   = f'{input_id}_text'

        def opt(val, label):
            s = ' selected' if val == select_val else ''
            return f'<option value="{val}"{s}>{label}</option>'

        options = '<option value="">— Alege tip document —</option>'
        for n in _PREDEFINED_NAMES:
            options += opt(n, n)
        options += opt(_CUSTOM_SENTINEL, 'Altul (text liber)…')

        txt_hidden = '' if select_val == _CUSTOM_SENTINEL else 'display:none;'

        html = (
            f'<div style="display:flex;flex-direction:column;gap:6px;">'
            f'<select id="{select_id}" name="{name}_choice" style="{_SEL_STYLE}"'
            f' onchange="docNameChange(this)">{options}</select>'
            f'<input type="text" id="{text_id}" name="{name}_custom"'
            f' value="{text_val}" placeholder="Introdu nume document\u2026"'
            f' style="{_TXT_STYLE}{txt_hidden}">'
            f'</div>'
        )
        return mark_safe(_DOC_NAME_SCRIPT + html)

    def value_from_datadict(self, data, files, name):
        choice = data.get(f'{name}_choice', '')
        if choice == _CUSTOM_SENTINEL:
            return data.get(f'{name}_custom', '').strip()
        return choice


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = '__all__'
        widgets = {
            'name': DocumentNameWidget(),
            'expiry_date': ExpiryDateWidget(),
        }


# ──────────────────────────────────────────────────────────────────────────────
# TherapistDocument widgets & form
# ──────────────────────────────────────────────────────────────────────────────

_THERAPIST_DOC_NAMES = [
    "Carte de identitate",
    "Contract individual de munc\u0103",
    "Fi\u0219a Postului",
    "Asigurare de malpraxis",
]

_THERAPIST_DOC_SCRIPT = (
    '<script>'
    'if(!window._therapistDocNameDefined){'
    'window._therapistDocNameDefined=true;'
    'window.therapistDocNameChange=function(sel){'
    'var CUSTOM="__custom__";'
    'var div=sel.parentElement;'
    'var textEl=div?div.querySelector("input[type=\'text\']"):null;'
    'if(!textEl)return;'
    'textEl.style.display=sel.value===CUSTOM?"":"none";'
    'if(sel.value===CUSTOM)textEl.focus();'
    '}}'
    '</script>'
)


class TherapistDocNameWidget(forms.Widget):

    def render(self, name, value, attrs=None, renderer=None):
        value = value or ''
        is_preset  = value in _THERAPIST_DOC_NAMES
        select_val = value if is_preset else (_CUSTOM_SENTINEL if value else '')
        text_val   = '' if is_preset else value

        input_id  = (attrs or {}).get('id', f'id_{name}')
        select_id = f'{input_id}_select'
        text_id   = f'{input_id}_text'

        def opt(val, label):
            s = ' selected' if val == select_val else ''
            return f'<option value="{val}"{s}>{label}</option>'

        options = '<option value="">— Alege tip document —</option>'
        for n in _THERAPIST_DOC_NAMES:
            options += opt(n, n)
        options += opt(_CUSTOM_SENTINEL, 'Altul (text liber)\u2026')

        txt_hidden = '' if select_val == _CUSTOM_SENTINEL else 'display:none;'

        html = (
            f'<div style="display:flex;flex-direction:column;gap:6px;">'
            f'<select id="{select_id}" name="{name}_choice" style="{_SEL_STYLE}"'
            f' onchange="therapistDocNameChange(this)">{options}</select>'
            f'<input type="text" id="{text_id}" name="{name}_custom"'
            f' value="{text_val}" placeholder="Introdu nume document\u2026"'
            f' style="{_TXT_STYLE}{txt_hidden}">'
            f'</div>'
        )
        return mark_safe(_THERAPIST_DOC_SCRIPT + html)

    def value_from_datadict(self, data, files, name):
        choice = data.get(f'{name}_choice', '')
        if choice == _CUSTOM_SENTINEL:
            return data.get(f'{name}_custom', '').strip()
        return choice


_HAS_EXPIRY_SCRIPT = (
    '<script>'
    'if(!window._hasExpiryDefined){'
    'window._hasExpiryDefined=true;'
    'window.expiryToggle=function(cb){'
    # TabularInline: use opacity (not visibility/display) so columns stay aligned
    # and the cell background matches the row stripe (no white border artifact)
    'var tr=cb.closest("tr");'
    'if(tr){'
    'tr.querySelectorAll("td.field-expiry_date,td.field-_expirat").forEach(function(td){'
    'td.style.opacity=cb.checked?"":"0";'
    'td.style.pointerEvents=cb.checked?"":"none";'
    '});return;}'
    # Standalone form: hide/show the .form-row with expiry_date
    'var cont=cb.closest(".inline-related")||cb.closest("fieldset")||cb.closest("form");'
    'if(cont){'
    'var expInp=cont.querySelector("input[name$=\'expiry_date\']");'
    'if(expInp){'
    'var row=expInp.closest(".form-row")||expInp.closest("p");'
    'if(row)row.style.display=cb.checked?"":"none";}}'
    '};'
    # Init existing rows on page load
    'document.addEventListener("DOMContentLoaded",function(){'
    'document.querySelectorAll("input[name$=\'has_expiry\']").forEach(function(cb){'
    'expiryToggle(cb);});});'
    # Init new inline rows
    'document.addEventListener("formset:added",function(e){'
    'var row=e.detail&&e.detail.row;'
    'if(!row)return;'
    'row.querySelectorAll("input[name$=\'has_expiry\']").forEach(function(cb){'
    'expiryToggle(cb);});});'
    '}'
    '</script>'
)


class HasExpiryWidget(forms.CheckboxInput):
    """Standard checkbox that injects the expiryToggle script and onchange handler."""

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        attrs['onchange'] = 'expiryToggle(this)'
        base = super().render(name, value, attrs, renderer)
        return mark_safe(_HAS_EXPIRY_SCRIPT + base)


class TherapistDocumentForm(forms.ModelForm):
    class Meta:
        model = TherapistDocument
        fields = '__all__'
        widgets = {
            'name': TherapistDocNameWidget(),
            'has_expiry': HasExpiryWidget(),
            'expiry_date': ExpiryDateWidget(),
        }


class ExpiratFilter(admin.SimpleListFilter):
    title = "Expirat"
    parameter_name = "expirat"

    def lookups(self, request, model_admin):
        return [
            ("da", "Da"),
            ("nu", "Nu"),
        ]

    def queryset(self, request, queryset):
        today = date.today()
        if self.value() == "da":
            return queryset.filter(expiry_date__lt=today)
        if self.value() == "nu":
            return queryset.filter(expiry_date__gte=today)
        return queryset


class RdsAdminSite(admin.AdminSite):
    site_header = "Raza de Speranță – Admin"
    site_title = "RdS Admin"
    index_title = "Dashboard"

    def get_urls(self):
        from .views import (
            TherapyBatchView, RaportLunarView, RaportAnualView, RaportSaptamanaiView,
            RaportZilnicView,
            raport_lunar_excel, raport_anual_excel, raport_saptamanal_excel,
            raport_zilnic_excel,
        )
        custom = [
            path(
                "core/therapy/batch/",
                self.admin_view(TherapyBatchView.as_view()),
                name="therapy_batch",
            ),
            path(
                "core/rapoarte/zilnic/",
                self.admin_view(RaportZilnicView.as_view()),
                name="raport_zilnic",
            ),
            path(
                "core/rapoarte/lunar/",
                self.admin_view(RaportLunarView.as_view()),
                name="raport_lunar",
            ),
            path(
                "core/rapoarte/anual/",
                self.admin_view(RaportAnualView.as_view()),
                name="raport_anual",
            ),
            path(
                "core/rapoarte/saptamanal/",
                self.admin_view(RaportSaptamanaiView.as_view()),
                name="raport_saptamanal",
            ),
            path(
                "core/rapoarte/zilnic/excel/",
                self.admin_view(raport_zilnic_excel),
                name="raport_zilnic_excel",
            ),
            path(
                "core/rapoarte/lunar/excel/",
                self.admin_view(raport_lunar_excel),
                name="raport_lunar_excel",
            ),
            path(
                "core/rapoarte/anual/excel/",
                self.admin_view(raport_anual_excel),
                name="raport_anual_excel",
            ),
            path(
                "core/rapoarte/saptamanal/excel/",
                self.admin_view(raport_saptamanal_excel),
                name="raport_saptamanal_excel",
            ),
        ]
        return custom + super().get_urls()

    def each_context(self, request):
        ctx = super().each_context(request)
        ctx["batch_therapy_url"]  = "core/therapy/batch/"
        ctx["raport_zilnic_url"] = "core/rapoarte/zilnic/"
        ctx["raport_lunar_url"]  = "core/rapoarte/lunar/"
        ctx["raport_anual_url"]  = "core/rapoarte/anual/"
        ctx["raport_sapt_url"]   = "core/rapoarte/saptamanal/"
        return ctx

    def index(self, request, extra_context=None):
        from django.contrib import messages as dj_messages
        today = date.today()
        # Expired patient documents
        expired_docs = Document.objects.filter(expiry_date__lt=today, exists=True)
        count = expired_docs.count()
        if count:
            names = ", ".join(
                f"{d.name} ({d.child})" for d in expired_docs.select_related("child")[:5]
            )
            suffix = f" (primele 5: {names})" if count > 5 else f": {names}"
            dj_messages.warning(
                request,
                f"Atenție: există {count} document(e) pacient expirate{suffix}.",
            )
        # Expired therapist eligibility documents
        expired_tdocs = TherapistDocument.objects.filter(has_expiry=True, expiry_date__lt=today)
        tcount = expired_tdocs.count()
        if tcount:
            tnames = ", ".join(
                f"{d.name} ({d.therapist})" for d in expired_tdocs.select_related("therapist")[:5]
            )
            tsuffix = f" (primele 5: {tnames})" if tcount > 5 else f": {tnames}"
            dj_messages.warning(
                request,
                f"Atenție: există {tcount} document(e) eligibilitate psiholog expirate{tsuffix}.",
            )
        return super().index(request, extra_context=extra_context)

    def get_app_list(self, request, app_label=None):
        """Reorganize all models into 4 named groups regardless of Django app."""
        original = super().get_app_list(request)
        # Flatten to a dict keyed by object_name (lowercase)
        all_models = {}
        for app in original:
            for m in app["models"]:
                all_models[m["object_name"].lower()] = m

        def group(label, name, keys):
            models = [all_models[k] for k in keys if k in all_models]
            if not models:
                return None
            return {
                "name": name,
                "app_label": label,
                "app_url": "",
                "has_module_perms": True,
                "models": models,
            }

        sections = [
            group("persoane",   "Persoane",   ["parent", "child", "therapist"]),
            group("auxiliare",  "Auxiliare",  ["centru", "therapy"]),
            group("documente",  "Documente",  ["document", "therapistdocument"]),
        ]
        if request.user.is_superuser:
            sections.append(group("utilizatori", "Utilizatori", ["user"]))
        return [s for s in sections if s]


admin_site = RdsAdminSite(name="admin")


# ──────────────────────────────────────────────────────────────────────────────
# Mixin: grant full access to any active staff user (bypasses model-level permissions)
# ──────────────────────────────────────────────────────────────────────────────
class StaffFullAccessMixin:
    """Any active staff user gets full CRUD on this model, no model-level perms needed."""

    def _is_staff(self, request):
        return request.user.is_active and request.user.is_staff

    # Django 5.x calls has_module_permission (singular); keep both for compatibility
    def has_module_permission(self, request):
        return self._is_staff(request)

    def has_module_perms(self, request):
        return self._is_staff(request)

    def has_view_permission(self, request, obj=None):
        return self._is_staff(request)

    def has_add_permission(self, request):
        return self._is_staff(request)

    def has_change_permission(self, request, obj=None):
        return self._is_staff(request)

    def has_delete_permission(self, request, obj=None):
        return self._is_staff(request)


# ──────────────────────────────────────────────────────────────────────────────
# Inlines  (show related rows inside the parent form)
# ──────────────────────────────────────────────────────────────────────────────
class ChildInline(admin.TabularInline):
    model = Child
    extra = 0
    fields = ("last_name", "first_name", "cnp", "_varsta", "_tip_copil", "_sex", "status", "diagnostic")
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
    form = DocumentForm
    extra = 1
    fields = ("name", "exists", "creation_date", "expiry_date", "_expirat")
    readonly_fields = ("_expirat",)

    @admin.display(description="Expirat")
    def _expirat(self, obj):
        if not obj.expiry_date:
            return "—"
        if obj.expiry_date < date.today():
            return format_html('<span style="color:#ba2121;font-weight:bold">Da</span>')
        return format_html('<span style="color:#28a745">Nu</span>')


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


class TherapistDocumentInline(admin.TabularInline):
    model = TherapistDocument
    form = TherapistDocumentForm
    extra = 1
    fields = ("name", "has_expiry", "expiry_date", "pdf_file", "_expirat", "_download_link")
    readonly_fields = ("_expirat", "_download_link")

    @admin.display(description="Expirat")
    def _expirat(self, obj):
        if not obj.has_expiry or not obj.expiry_date:
            return "—"
        if obj.expiry_date < date.today():
            return format_html('<span style="color:#ba2121;font-weight:bold">Da</span>')
        return format_html('<span style="color:#28a745">Nu</span>')

    @admin.display(description="Fișier")
    def _download_link(self, obj):
        if not obj.pdf_file:
            return "—"
        return format_html('<a href="{}" download>⬇ Descarcă</a>', obj.pdf_file.url)


# ──────────────────────────────────────────────────────────────────────────────
# Model Admins
# ──────────────────────────────────────────────────────────────────────────────
@admin.register(Parent, site=admin_site)
class ParentAdmin(StaffFullAccessMixin, admin.ModelAdmin):
    list_display = ("last_name", "first_name", "phone_number", "email", "children_count")
    search_fields = ("last_name", "first_name", "phone_number", "email")
    inlines = [ChildInline]

    def get_inlines(self, request, obj):
        # Hide ChildInline when creating a new parent (no pk yet)
        if obj is None:
            return []
        return [ChildInline]

    @admin.display(description="Nr. pacienti activi")
    def children_count(self, obj):
        return obj.children.filter(status="activ").count()


@admin.register(Child, site=admin_site)
class ChildAdmin(StaffFullAccessMixin, admin.ModelAdmin):
    list_display = (
        "last_name",
        "first_name",
        "cnp",
        "_varsta",
        "_tip_copil",
        "_sex",
        "status",
        "parent",
        "docs_count",
        "_terapii_luna_curenta",
        "_terapii_luna_anterioara",
        "_terapii_an_curent",
    )
    list_filter = ("child_type", "sex", "status", "diagnostic")
    search_fields = ("first_name", "last_name", "cnp")
    autocomplete_fields = ("parent",)
    readonly_fields = ("_varsta", "_tip_copil", "_sex")
    fields = (
        "last_name", "first_name", "cnp", "_varsta", "_tip_copil",
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

    @admin.display(description="Terapii luna curentă")
    def _terapii_luna_curenta(self, obj):
        today = date.today()
        return obj.therapies.filter(date__year=today.year, date__month=today.month).count()

    @admin.display(description="Terapii luna anterioară")
    def _terapii_luna_anterioara(self, obj):
        today = date.today()
        prev = today.replace(day=1) - timedelta(days=1)
        return obj.therapies.filter(date__year=prev.year, date__month=prev.month).count()

    @admin.display(description="Terapii an curent")
    def _terapii_an_curent(self, obj):
        return obj.therapies.filter(date__year=date.today().year).count()


@admin.register(Therapist, site=admin_site)
class TherapistAdmin(StaffFullAccessMixin, admin.ModelAdmin):
    list_display = ("last_name", "first_name", "centru", "_terapii_luna_curenta", "_terapii_luna_anterioara", "_terapii_an_curent")
    search_fields = ("last_name", "first_name", "centru__name")
    list_filter = ("centru",)
    inlines = [TherapistDocumentInline]
    fields = ("first_name", "last_name", "centru")

    @admin.display(description="Terapii luna curentă")
    def _terapii_luna_curenta(self, obj):
        today = date.today()
        return obj.therapies.filter(date__year=today.year, date__month=today.month).count()

    @admin.display(description="Terapii luna anterioară")
    def _terapii_luna_anterioara(self, obj):
        today = date.today()
        prev = today.replace(day=1) - timedelta(days=1)
        return obj.therapies.filter(date__year=prev.year, date__month=prev.month).count()

    @admin.display(description="Terapii an curent")
    def _terapii_an_curent(self, obj):
        return obj.therapies.filter(date__year=date.today().year).count()


@admin.register(Centru, site=admin_site)
class CentruAdmin(StaffFullAccessMixin, admin.ModelAdmin):
    list_display = ("name", "_therapists_count")
    search_fields = ("name",)
    
    @admin.display(description="Terapeuți")
    def _therapists_count(self, obj):
        return obj.therapists.count()


@admin.register(Therapy, site=admin_site)
class TherapyAdmin(StaffFullAccessMixin, admin.ModelAdmin):
    list_display = ("therapist", "child", "date", "start_time")
    list_filter = ("date", "therapist")
    search_fields = (
        "child__last_name",
        "child__first_name",
        "therapist__last_name",
        "therapist__first_name",
    )
    autocomplete_fields = ("child", "therapist")
    date_hierarchy = "date"


@admin.register(Document, site=admin_site)
class DocumentAdmin(StaffFullAccessMixin, admin.ModelAdmin):
    form = DocumentForm
    list_display = ("name", "child", "exists", "creation_date", "expiry_date", "_expirat")
    list_filter = ("exists", ExpiratFilter)
    search_fields = ("name", "child__first_name", "child__last_name")
    autocomplete_fields = ("child",)

    @admin.display(description="Expirat")
    def _expirat(self, obj):
        if not obj.expiry_date:
            return "—"
        if obj.expiry_date < date.today():
            return format_html('<span style="color:#ba2121;font-weight:bold">Da</span>')
        return format_html('<span style="color:#28a745">Nu</span>')


class TherapistExpiratFilter(admin.SimpleListFilter):
    title = "Expirat"
    parameter_name = "expirat"

    def lookups(self, request, model_admin):
        return [("da", "Da"), ("nu", "Nu")]

    def queryset(self, request, queryset):
        today = date.today()
        if self.value() == "da":
            return queryset.filter(has_expiry=True, expiry_date__lt=today)
        if self.value() == "nu":
            return queryset.filter(has_expiry=True, expiry_date__gte=today)
        return queryset


@admin.register(TherapistDocument, site=admin_site)
class TherapistDocumentAdmin(StaffFullAccessMixin, admin.ModelAdmin):
    form = TherapistDocumentForm
    list_display = ("name", "therapist", "has_expiry", "expiry_date", "_expirat", "_download_link")
    list_filter = ("has_expiry", TherapistExpiratFilter)
    search_fields = ("name", "therapist__last_name", "therapist__first_name")
    autocomplete_fields = ("therapist",)

    @admin.display(description="Expirat")
    def _expirat(self, obj):
        if not obj.has_expiry or not obj.expiry_date:
            return "—"
        if obj.expiry_date < date.today():
            return format_html('<span style="color:#ba2121;font-weight:bold">Da</span>')
        return format_html('<span style="color:#28a745">Nu</span>')

    @admin.display(description="Fișier PDF")
    def _download_link(self, obj):
        if not obj.pdf_file:
            return "—"
        return format_html('<a href="{}" download>⬇ Descarcă</a>', obj.pdf_file.url)


# ──────────────────────────────────────────────────────────────────────────────
# User admin (Utilizatori)
# ──────────────────────────────────────────────────────────────────────────────
@admin.register(User, site=admin_site)
class RestrictedUserAdmin(UserAdmin):
    """Superusers: full access. Staff: can only view/edit own account."""

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_staff

    def has_module_perms(self, request):
        return request.user.is_active and request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(pk=request.user.pk)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return obj.pk == request.user.pk

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        # Staff can edit password, first_name, last_name, email — everything else is read-only
        return (
            "username",
            "is_active", "is_staff", "is_superuser",
            "groups", "user_permissions",
            "last_login", "date_joined",
        )

    def get_fieldsets(self, request, obj=None):
        if not request.user.is_superuser:
            # Non-superusers: show only account + personal info sections
            return (
                (None, {"fields": ("username", "password")}),
                ("Date personale", {"fields": ("first_name", "last_name", "email")}),
            )
        # Superusers: default fieldsets minus the "Password-based authentication" toggle
        fieldsets = super().get_fieldsets(request, obj)
        return [
            (name, opts)
            for name, opts in fieldsets
            if "usable_password" not in opts.get("fields", ())
        ]
