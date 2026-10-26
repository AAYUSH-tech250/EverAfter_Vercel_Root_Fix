import csv
from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import user_passes_test, login_required
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import EventForm, GuestForm, QuickAddForm, RSVPForm, WeddingForm, SignupForm
from .models import Event, Guest, Wedding
from .utils import whatsapp_url

def _is_owner(user):
    return user.is_authenticated and (user.is_staff or user.groups.filter(name="Wedding Owner").exists())

host_required = user_passes_test(_is_owner, login_url="login")


def _wedding_for(request):
    wedding = Wedding.for_user(request.user)
    if wedding is None and request.user.is_staff:
        wedding = Wedding.get_solo()
        if wedding.owner_id is None:
            wedding.owner = request.user
            wedding.save(update_fields=["owner"])
    return wedding


S = Guest.Status


def _seats(qs):
    return qs.aggregate(s=Sum("max_members"))["s"] or 0


def _people(qs):
    return qs.aggregate(s=Sum("members_coming"))["s"] or 0


def _attach_links(request, wedding, guests):
    for g in guests:
        g.invite_link = request.build_absolute_uri(g.rsvp_path)
        g.wa_url = whatsapp_url(g, wedding, g.invite_link)
    return guests


def home(request):
    if request.user.is_authenticated:
        if _is_owner(request.user):
            return redirect("dashboard")
        if request.user.groups.filter(name__startswith="Attendance Viewer:").exists():
            return redirect("attendance_view")
        if hasattr(request.user, "planner_guest"):
            return redirect("guest_portal")
    return render(request, "core/home.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data["role"]
            code = form.cleaned_data.get("invite_code", "")
            wedding = None
            if role in ("guest", "viewer"):
                wedding = Wedding.objects.filter(invite_code__iexact=code).first()
                if wedding is None:
                    form.add_error("invite_code", "That invitation code was not found. Check it with the wedding owner.")
                    return render(request, "core/signup.html", {"form": form})
            user = form.save()
            user.email = form.cleaned_data["email"]
            user.save(update_fields=["email"])
            if role == "owner":
                user.groups.add(Group.objects.get_or_create(name="Wedding Owner")[0])
                Wedding.objects.create(owner=user, couple_names="Your Wedding", tagline="Together with our families, we invite you to celebrate.")
            elif role == "viewer":
                user.groups.add(Group.objects.get_or_create(name=f"Attendance Viewer:{wedding.pk}")[0])
            elif role == "guest":
                guest = Guest.objects.create(wedding=wedding, user=user, name=user.username, email=user.email, max_members=1)
                guest.events.set(wedding.events.all())
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect("home")
    else:
        form = SignupForm()
    return render(request, "core/signup.html", {"form": form})


@login_required
def guest_portal(request):
    guest = get_object_or_404(Guest.objects.select_related("wedding"), user=request.user)
    return render(request, "core/guest_portal.html", {"guest": guest, "wedding": guest.wedding})


# ------------------------------------------------------------------ dashboard
@host_required
def dashboard(request):
    w = _wedding_for(request)
    guests = Guest.objects.filter(wedding=w)
    yes, maybe = guests.filter(status=S.YES), guests.filter(status=S.MAYBE)
    pending, no = guests.filter(status=S.PENDING), guests.filter(status=S.NO)

    stats = {
        "households": guests.count(),
        "seats": _seats(guests),
        "yes_h": yes.count(), "yes_people": _people(yes),
        "maybe_h": maybe.count(), "maybe_seats": _seats(maybe),
        "pending_h": pending.count(), "pending_seats": _seats(pending),
        "no_h": no.count(), "no_seats": _seats(no),
        "pickup_people": _people(yes.filter(needs_pickup=True)),
        "pickup_h": yes.filter(needs_pickup=True).count(),
        "stay_people": _people(yes.filter(needs_stay=True)),
        "stay_h": yes.filter(needs_stay=True).count(),
        "not_sent": guests.filter(invite_sent_at__isnull=True).count(),
        "no_arrival": yes.filter(arrival_datetime__isnull=True).count(),
    }
    total = stats["yes_people"] + stats["maybe_seats"] + stats["pending_seats"] + stats["no_seats"]
    pct = {}
    for key, val in (("yes", stats["yes_people"]), ("maybe", stats["maybe_seats"]),
                     ("pending", stats["pending_seats"]), ("no", stats["no_seats"])):
        pct[key] = round(val * 100 / total, 1) if total else 0

    event_rows = []
    for e in w.events.all():
        att = e.attending_guests.filter(status=S.YES)
        event_rows.append({"event": e, "people": _people(att), "invited": e.invited_guests.count()})

    days_left = (w.wedding_date - timezone.localdate()).days if w.wedding_date else None
    recent = guests.exclude(responded_at=None).order_by("-responded_at")[:6]
    return render(request, "core/dashboard.html", {
        "stats": stats, "pct": pct, "event_rows": event_rows,
        "days_left": days_left, "recent": recent,
    })


# --------------------------------------------------------------------- guests
@host_required
def guest_list(request):
    w = _wedding_for(request)
    base = Guest.objects.filter(wedding=w)
    f = request.GET.get("f", "")
    q = request.GET.get("q", "").strip()
    qs = base
    if f in dict(Guest.Status.choices):
        qs = qs.filter(status=f)
    elif f == "unsent":
        qs = qs.filter(invite_sent_at__isnull=True)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q))
    guests = _attach_links(request, w, list(qs.order_by("name")))
    counts = {
        "all": base.count(),
        "yes": base.filter(status=S.YES).count(),
        "maybe": base.filter(status=S.MAYBE).count(),
        "pending": base.filter(status=S.PENDING).count(),
        "no": base.filter(status=S.NO).count(),
        "unsent": base.filter(invite_sent_at__isnull=True).count(),
    }
    return render(request, "core/guests.html", {"guests": guests, "counts": counts, "f": f, "q": q})


def _guest_form(request, guest=None):
    w = _wedding_for(request)
    if request.method == "POST":
        form = GuestForm(request.POST, instance=guest, wedding=w)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.wedding = w
            obj.save()
            form.save_m2m()
            messages.success(request, f"Saved {obj.name}.")
            return redirect("guest_list")
    else:
        form = GuestForm(instance=guest, wedding=w)
    if guest:
        _attach_links(request, w, [guest])
    return render(request, "core/guest_form.html", {"form": form, "guest": guest})


@host_required
def guest_add(request):
    return _guest_form(request)


@host_required
def guest_edit(request, pk):
    guest = get_object_or_404(Guest, pk=pk, wedding=_wedding_for(request))
    return _guest_form(request, guest)


@host_required
def guest_delete(request, pk):
    guest = get_object_or_404(Guest, pk=pk, wedding=_wedding_for(request))
    if request.method == "POST":
        guest.delete()
        messages.success(request, "Guest removed.")
        return redirect("guest_list")
    return render(request, "core/confirm_delete.html", {
        "label": guest.name, "cancel_url": "guest_list",
    })


@host_required
def guest_bulk(request):
    w = _wedding_for(request)
    if request.method == "POST":
        form = QuickAddForm(request.POST)
        if form.is_valid():
            all_events = list(w.events.all())
            created = 0
            for line in form.cleaned_data["lines"].splitlines():
                parts = [p.strip() for p in line.split(",")]
                if not parts or not parts[0]:
                    continue
                seats = 1
                if len(parts) > 2 and parts[2].isdigit():
                    seats = max(1, int(parts[2]))
                g = Guest.objects.create(
                    wedding=w, name=parts[0], phone=parts[1] if len(parts) > 1 else "",
                    max_members=seats, side=form.cleaned_data["side"],
                )
                g.events.set(all_events)
                created += 1
            messages.success(request, f"Added {created} guest(s). Now send their invitations!")
            return redirect("guest_list")
    else:
        form = QuickAddForm()
    return render(request, "core/guest_bulk.html", {"form": form})


@host_required
@require_POST
def guest_send(request, pk):
    """Marks the invitation as sent and bounces the host to WhatsApp with the message ready."""
    w = _wedding_for(request)
    guest = get_object_or_404(Guest, pk=pk, wedding=w)
    guest.invite_sent_at = timezone.now()
    guest.save(update_fields=["invite_sent_at"])
    link = request.build_absolute_uri(guest.rsvp_path)
    return redirect(whatsapp_url(guest, w, link))


def _csv_response(filename):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.write("\ufeff")  # so Excel reads UTF-8 properly
    return resp


def _arrival(g):
    return timezone.localtime(g.arrival_datetime).strftime("%d %b %Y %I:%M %p") if g.arrival_datetime else ""


@host_required
def guest_export(request):
    w = _wedding_for(request)
    resp = _csv_response("guests.csv")
    out = csv.writer(resp)
    out.writerow(["Name", "Phone", "Side", "Seats invited", "Status", "People coming", "Names",
                  "Functions attending", "Arrival", "Mode", "From", "Details", "Pickup", "Stay", "Message"])
    for g in Guest.objects.filter(wedding=w).prefetch_related("attending_events"):
        out.writerow([
            g.name, g.phone, g.get_side_display(), g.max_members, g.get_status_display(), g.members_coming,
            g.member_names, ", ".join(e.name for e in g.attending_events.all()), _arrival(g),
            g.get_arrival_mode_display(), g.arrival_from, g.arrival_details,
            "Yes" if g.needs_pickup else "", "Yes" if g.needs_stay else "", g.guest_note,
        ])
    return resp


# ------------------------------------------------------------------ logistics
def _logistics_qs(request, w):
    qs = Guest.objects.filter(wedding=w, status__in=[S.YES, S.MAYBE])
    if request.GET.get("pickup"):
        qs = qs.filter(needs_pickup=True)
    return qs


@host_required
def logistics(request):
    w = _wedding_for(request)
    qs = _logistics_qs(request, w)
    days = {}
    for g in qs.exclude(arrival_datetime=None).order_by("arrival_datetime"):
        d = timezone.localtime(g.arrival_datetime).date()
        days.setdefault(d, []).append(g)
    day_rows = [{"date": d, "guests": gs, "people": sum(x.members_coming for x in gs)} for d, gs in days.items()]
    missing = qs.filter(arrival_datetime=None).order_by("name")
    return render(request, "core/logistics.html", {
        "day_rows": day_rows, "missing": missing, "pickup_only": bool(request.GET.get("pickup")),
    })


@host_required
def logistics_export(request):
    w = _wedding_for(request)
    resp = _csv_response("arrivals.csv")
    out = csv.writer(resp)
    out.writerow(["Arrival", "Name", "Phone", "People", "Status", "Mode", "From", "Details", "Pickup", "Stay"])
    for g in _logistics_qs(request, w).order_by("arrival_datetime", "name"):
        out.writerow([
            _arrival(g), g.name, g.phone, g.members_coming, g.get_status_display(),
            g.get_arrival_mode_display(), g.arrival_from, g.arrival_details,
            "Yes" if g.needs_pickup else "", "Yes" if g.needs_stay else "",
        ])
    return resp


# ------------------------------------------------------------------- programs
@host_required
def program_list(request):
    w = _wedding_for(request)
    rows = []
    for e in w.events.all():
        rows.append({
            "event": e,
            "invited": e.invited_guests.count(),
            "people": _people(e.attending_guests.filter(status=S.YES)),
        })
    return render(request, "core/programs.html", {"rows": rows})


def _program_form(request, event=None):
    w = _wedding_for(request)
    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            obj = form.save(commit=False)
            is_new = obj.pk is None
            obj.wedding = w
            obj.save()
            if is_new:  # invite everyone already on the list to the new function
                obj.invited_guests.set(Guest.objects.filter(wedding=w))
            messages.success(request, f"Saved {obj.name}.")
            return redirect("program_list")
    else:
        form = EventForm(instance=event)
    return render(request, "core/program_form.html", {"form": form, "event": event})


@host_required
def program_add(request):
    return _program_form(request)


@host_required
def program_edit(request, pk):
    event = get_object_or_404(Event, pk=pk, wedding=_wedding_for(request))
    return _program_form(request, event)


@host_required
def program_delete(request, pk):
    event = get_object_or_404(Event, pk=pk, wedding=_wedding_for(request))
    if request.method == "POST":
        event.delete()
        messages.success(request, "Program removed.")
        return redirect("program_list")
    return render(request, "core/confirm_delete.html", {"label": event.name, "cancel_url": "program_list"})


# ------------------------------------------------------------------- settings
@host_required
def wedding_settings(request):
    w = _wedding_for(request)
    if request.method == "POST":
        form = WeddingForm(request.POST, request.FILES, instance=w)
        if form.is_valid():
            form.save()
            messages.success(request, "Wedding details saved.")
            return redirect("wedding_settings")
    else:
        form = WeddingForm(instance=w)
    return render(request, "core/settings.html", {"form": form})


# ------------------------------------------------------- public guest invitation
def rsvp(request, token):
    guest = get_object_or_404(Guest.objects.select_related("wedding"), token=token)
    w = guest.wedding
    events = guest.events.all()
    initial = None
    if guest.status == S.PENDING:
        initial = {
            "members_coming": guest.max_members,
            "attending_events": list(events.values_list("pk", flat=True)),
        }
    if request.method == "POST":
        form = RSVPForm(request.POST, instance=guest, guest=guest)
        if form.is_valid():
            g = form.save(commit=False)
            g.responded_at = timezone.now()
            g.save()
            form.save_m2m()
            messages.success(request, "Thank you! Your reply is saved. You can open this link again anytime to change it.")
            return redirect("rsvp", token=guest.token)
    else:
        form = RSVPForm(instance=guest, guest=guest, initial=initial)
    return render(request, "core/rsvp.html", {
        "guest": guest, "wedding": w, "events": events, "form": form,
        "wedding_date_iso": w.wedding_date.isoformat() if isinstance(w.wedding_date, date) else "",
    })


# ---------------------------------------------------------- limited attendance viewer
from django.core.exceptions import PermissionDenied


@login_required
def attendance_view(request):
    """Read-only view for staff or members of the 'Attendance Viewer' group.
    Deliberately excludes phone, email, travel, address, and private notes.
    """
    wedding_id = None
    is_owner = _is_owner(request.user)
    if not is_owner and not request.user.is_staff:
        viewer_group = request.user.groups.filter(name__startswith="Attendance Viewer:").first()
        if not viewer_group:
            raise PermissionDenied
        try:
            wedding_id = int(viewer_group.name.split(":", 1)[1])
        except (ValueError, IndexError):
            raise PermissionDenied
    wedding = _wedding_for(request) if is_owner else None
    if wedding is None and wedding_id is not None:
        wedding = Wedding.objects.filter(pk=wedding_id).first()
    if wedding is None and request.user.is_staff:
        wedding = Wedding.objects.first()
    if wedding is None:
        return render(request, "core/attendance.html", {"wedding": None, "rows": [], "event_rows": []})
    guests = Guest.objects.filter(wedding=wedding).prefetch_related("attending_events")
    rows = []
    for guest in guests:
        rows.append({
            "name": guest.name,
            "status": guest.get_status_display(),
            "status_code": guest.status,
            "functions": list(guest.attending_events.values_list("name", flat=True))
                if guest.status == S.YES else [],
            "people": guest.members_coming if guest.status == S.YES else 0,
        })
    event_rows = []
    for event in wedding.events.all():
        attendees = event.attending_guests.filter(status=S.YES)
        event_rows.append({
            "name": event.name,
            "people": _people(attendees),
            "guests": list(attendees.values_list("name", flat=True)),
        })
    return render(request, "core/attendance.html", {
        "wedding": wedding, "rows": rows, "event_rows": event_rows,
    })
