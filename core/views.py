import calendar
import json
from datetime import date, time, timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from .models import Child, Therapist, Therapy

MAX_SLOTS_PER_THERAPIST = 6
FIRST_SLOT_START = time(8, 0)


def _slot_start(index: int) -> time:
    dt = timedelta(hours=FIRST_SLOT_START.hour) + timedelta(hours=index * 2)
    total_minutes = int(dt.total_seconds() // 60)
    return time(total_minutes // 60, total_minutes % 60)


def _therapies_for_date(session_date: date) -> list:
    """Return existing therapies for a date grouped by therapist, ordered by start_time."""
    rows = (
        Therapy.objects.filter(date=session_date)
        .select_related("therapist", "child")
        .order_by("therapist__last_name", "therapist__first_name", "start_time")
    )
    groups = {}
    for t in rows:
        tid = t.therapist_id
        if tid not in groups:
            groups[tid] = {"therapist_id": tid, "children": []}
        groups[tid]["children"].append(t.child_id)
    return list(groups.values())


@method_decorator(staff_member_required, name="dispatch")
class TherapyBatchView(View):
    template_name = "admin/core/therapy_batch.html"

    def _base_context(self, request):
        return {
            **admin_site_context(request),
            "therapists": list(
                Therapist.objects.order_by("last_name", "first_name").values("id", "first_name", "last_name")
            ),
            "children": list(
                Child.objects.filter(status="activ")
                .order_by("last_name", "first_name")
                .values("id", "first_name", "last_name")
            ),
            "max_slots": MAX_SLOTS_PER_THERAPIST,
            "slot_labels": [
                f"{_slot_start(i).strftime('%H:%M')}–{_slot_start(i+1).strftime('%H:%M')}"
                for i in range(MAX_SLOTS_PER_THERAPIST)
            ],
            "today": date.today().isoformat(),
            "tomorrow": (date.today() + timedelta(days=1)).isoformat(),
        }

    def get(self, request):
        # AJAX: return existing therapies for a given date as JSON
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            date_str = request.GET.get("date", "")
            try:
                session_date = date.fromisoformat(date_str)
            except ValueError:
                return JsonResponse({"error": "invalid date"}, status=400)
            return JsonResponse({"tables": _therapies_for_date(session_date)})

        return render(request, self.template_name, self._base_context(request))

    def post(self, request):
        selected_date_str = request.POST.get("session_date", "")
        try:
            session_date = date.fromisoformat(selected_date_str)
        except ValueError:
            messages.error(request, "Dată invalidă.")
            return render(request, self.template_name, self._base_context(request))

        # Parse tables
        raw = request.POST
        tables = {}
        for key, value in raw.items():
            if not key.startswith("tables["):
                continue
            parts = key.replace("]", "").replace("tables[", "").split("[")
            table_idx = parts[0]
            field = parts[1]
            tables.setdefault(table_idx, {"therapist": None, "children": {}})
            if field == "therapist":
                tables[table_idx]["therapist"] = value
            elif field == "children":
                tables[table_idx]["children"][parts[2]] = value

        errors = []
        to_create = []

        for t_idx, table in tables.items():
            therapist_id = table.get("therapist")
            if not therapist_id:
                errors.append(f"Tabela {int(t_idx)+1}: niciun terapeut selectat.")
                continue
            try:
                therapist = Therapist.objects.get(pk=therapist_id)
            except Therapist.DoesNotExist:
                errors.append(f"Tabela {int(t_idx)+1}: terapeut invalid.")
                continue

            for slot_idx_str, child_id in sorted(table["children"].items(), key=lambda x: int(x[0])):
                if not child_id:
                    continue
                slot_idx = int(slot_idx_str)
                if slot_idx >= MAX_SLOTS_PER_THERAPIST:
                    continue
                try:
                    child = Child.objects.get(pk=child_id, status="activ")
                except Child.DoesNotExist:
                    errors.append(f"Tabela {int(t_idx)+1}, slot {slot_idx+1}: copil invalid sau arhivat.")
                    continue
                to_create.append(Therapy(
                    child=child,
                    therapist=therapist,
                    date=session_date,
                    start_time=_slot_start(slot_idx),
                ))

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, self.template_name, self._base_context(request))

        with transaction.atomic():
            # Replace: delete all sessions for this date, then bulk-insert the new ones
            deleted, _ = Therapy.objects.filter(date=session_date).delete()
            Therapy.objects.bulk_create(to_create)

        messages.success(
            request,
            f"Orar salvat pentru {session_date}: {len(to_create)} ședință(e) "
            f"({deleted} înlocuite)." if deleted else
            f"Orar salvat pentru {session_date}: {len(to_create)} ședință(e)."
        )
        return redirect("admin:therapy_batch")


def admin_site_context(request):
    from django.contrib import admin as _admin
    return {
        "has_permission": request.user.is_active and request.user.is_staff,
        "site_header": _admin.site.site_header,
        "site_title": _admin.site.site_title,
        "title": "Editează/Adaugă orar",
        "opts": {"app_label": "core"},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Report helpers
# ─────────────────────────────────────────────────────────────────────────────

MONTHS_RO = [
    "", "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
    "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie",
]


def _available_years():
    from django.db.models import Min, Max
    agg = Therapy.objects.aggregate(mn=Min("date__year"), mx=Max("date__year"))
    mn = agg["mn"] or date.today().year
    mx = agg["mx"] or date.today().year
    return list(range(mn, mx + 1))


def _report_context(request, title):
    from django.contrib import admin as _admin
    return {
        "has_permission": request.user.is_active and request.user.is_staff,
        "site_header": _admin.site.site_header,
        "site_title": _admin.site.site_title,
        "title": title,
        "opts": {"app_label": "core"},
    }


@method_decorator(staff_member_required, name="dispatch")
class RaportLunarView(View):
    template_name = "admin/core/raport_lunar.html"

    def get(self, request):
        today = date.today()
        year  = int(request.GET.get("an",  today.year))
        month = int(request.GET.get("luna", today.month))

        _, days_in_month = calendar.monthrange(year, month)
        days = list(range(1, days_in_month + 1))

        # Fetch all therapies for the month
        therapies = (
            Therapy.objects
            .filter(date__year=year, date__month=month)
            .select_related("child", "therapist")
        )

        # Build pivot: {(child_id, therapist_id): {day: count}}
        pivot = {}
        meta  = {}  # key -> (child_display, therapist_display, cnp)
        for t in therapies:
            key = (t.child_id, t.therapist_id)
            if key not in pivot:
                pivot[key] = {}
                meta[key] = (
                    f"{t.child.last_name} {t.child.first_name}",
                    f"{t.therapist.last_name} {t.therapist.first_name}",
                    t.child.cnp,
                )
            d = t.date.day
            pivot[key][d] = pivot[key].get(d, 0) + 1

        rows = []
        for key in sorted(meta, key=lambda k: (meta[k][0], meta[k][1])):
            child_name, therapist_name, cnp = meta[key]
            counts = [pivot[key].get(d, "") for d in days]
            total  = sum(v for v in counts if v)
            rows.append({
                "child":     child_name,
                "therapist": therapist_name,
                "cnp":       cnp,
                "counts":    counts,
                "total":     total,
            })

        ctx = _report_context(request, f"Raport lunar – {MONTHS_RO[month]} {year}")
        ctx.update({
            "year": year, "month": month,
            "month_name": MONTHS_RO[month],
            "days": days,
            "rows": rows,
            "years": _available_years(),
            "months": list(enumerate(MONTHS_RO))[1:],  # (1,"Ianuarie")..
        })
        return render(request, self.template_name, ctx)


@method_decorator(staff_member_required, name="dispatch")
class RaportAnualView(View):
    template_name = "admin/core/raport_anual.html"

    def get(self, request):
        today = date.today()
        year  = int(request.GET.get("an", today.year))

        therapies = (
            Therapy.objects
            .filter(date__year=year)
            .select_related("child", "therapist")
        )

        pivot = {}
        meta  = {}
        for t in therapies:
            key = (t.child_id, t.therapist_id)
            if key not in pivot:
                pivot[key] = {}
                meta[key] = (
                    f"{t.child.last_name} {t.child.first_name}",
                    f"{t.therapist.last_name} {t.therapist.first_name}",
                    t.child.cnp,
                )
            m = t.date.month
            pivot[key][m] = pivot[key].get(m, 0) + 1

        rows = []
        for key in sorted(meta, key=lambda k: (meta[k][0], meta[k][1])):
            child_name, therapist_name, cnp = meta[key]
            counts = [pivot[key].get(m, "") for m in range(1, 13)]
            total  = sum(v for v in counts if v)
            rows.append({
                "child":     child_name,
                "therapist": therapist_name,
                "cnp":       cnp,
                "counts":    counts,
                "total":     total,
            })

        ctx = _report_context(request, f"Raport anual – {year}")
        ctx.update({
            "year": year,
            "month_names": MONTHS_RO[1:],  # 12 names
            "rows": rows,
            "years": _available_years(),
            "months": list(enumerate(MONTHS_RO))[1:],  # (1,"Ianuarie")..
        })
        return render(request, self.template_name, ctx)
