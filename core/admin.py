from datetime import date

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget
from django.urls import path
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Child, Document, Parent, Therapist, Therapy


# ──────────────────────────────────────────────────────────────────────────────
# Custom expiry-date widget with +6 luni / +1 an quick buttons
# ──────────────────────────────────────────────────────────────────────────────

_EXPIRY_ONCE_SCRIPT = (
    '<script>'
    'if(!window._expiryQuickDefined){'
    'window._expiryQuickDefined=true;'
    'window.expiryQuick=function(id,months){'
    'var inp=document.getElementById(id);'
    'if(!inp)return;'
    'var d=new Date();'
    'd.setMonth(d.getMonth()+months);'
    'var y=d.getFullYear();'
    'var m=String(d.getMonth()+1).padStart(2,"0");'
    'var day=String(d.getDate()).padStart(2,"0");'
    'inp.value=day+"."+m+"."+y;'
    'inp.dispatchEvent(new Event("change",{bubbles:true}));'
    '}}'
    '</script>'
)


class ExpiryDateWidget(AdminDateWidget):
    """AdminDateWidget cu butoane rapide +6 luni / +1 an."""

    def render(self, name, value, attrs=None, renderer=None):
        base = super().render(name, value, attrs, renderer)
        input_id = (attrs or {}).get('id', '')
        btn_style = (
            'display:inline-block;width:52px;text-align:center;'
            'padding:2px 0;font-size:12px;background:#318CE7;color:#fff;'
            'border:none;border-radius:3px;cursor:pointer;margin-left:4px;'
        )
        buttons = (
            f'<button type="button" style="{btn_style}" '
            f'onclick="expiryQuick(\'{input_id}\', 6)">+6 luni</button>'
            f'<button type="button" style="{btn_style}" '
            f'onclick="expiryQuick(\'{input_id}\', 12)">+1 an</button>'
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
    'window.docNameChange=function(sel,textId){'
    'var CERT="Certificat de na\u0219tere";'
    'var CUSTOM="__custom__";'
    'var textEl=document.getElementById(textId);'
    'if(!textEl)return;'
    'textEl.style.display=sel.value===CUSTOM?"":"none";'
    'if(sel.value===CUSTOM){textEl.focus();}'
    # locate expiry input in same <tr> (inline) or by id (standalone form)
    'var tr=sel.closest("tr");'
    'var exp=tr?tr.querySelector("input[name$=\\"expiry_date\\"]")'
    ':document.getElementById("id_expiry_date");'
    'if(exp){'
    'var isCert=sel.value===CERT;'
    'exp.disabled=isCert;'
    'exp.style.opacity=isCert?"0.4":"";'
    'if(isCert)exp.value="";'
    'var cont=exp.parentElement;'
    'while(cont&&!cont.querySelector("button"))cont=cont.parentElement;'
    'if(cont)cont.querySelectorAll("button[onclick]").forEach(function(b){'
    'b.disabled=isCert;b.style.opacity=isCert?"0.4":"";});'
    '}};'
    'window.docNameInit=function(selId,textId){'
    'var sel=document.getElementById(selId);'
    'if(sel)docNameChange(sel,textId);'
    '};}'
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
            f' onchange="docNameChange(this,\'{text_id}\')">{options}</select>'
            f'<input type="text" id="{text_id}" name="{name}_custom"'
            f' value="{text_val}" placeholder="Introdu nume document…"'
            f' style="{_TXT_STYLE}{txt_hidden}">'
            f'</div>'
            f'<script>document.addEventListener("DOMContentLoaded",function(){{'
            f'docNameInit("{select_id}","{text_id}");'
            f'}});</script>'
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
    list_display = ("therapist", "child", "date", "start_time")
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
