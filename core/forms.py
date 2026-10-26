from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Event, Guest, Wedding

DT_FORMAT = "%Y-%m-%dT%H:%M"
DT_INPUTS = [DT_FORMAT, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]


def dt_widget():
    return forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT_FORMAT)


def date_widget():
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class SignupForm(UserCreationForm):
    ROLE_CHOICES = [("owner", "Owner — create and manage a wedding"), ("guest", "Guest — join using an invitation code"), ("viewer", "Attendance viewer — join using the wedding code; see attendance only")]
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="Account type")
    invite_code = forms.CharField(required=False, label="Wedding invitation code", help_text="Required for Guest and Attendance Viewer accounts.")
    class Meta:
        model = User
        fields = ("username", "email", "role", "invite_code", "password1", "password2")

    def clean_invite_code(self):
        code = self.cleaned_data.get("invite_code", "").strip().upper()
        if self.cleaned_data.get("role") in ("guest", "viewer") and not code:
            raise forms.ValidationError("Enter the invitation code provided by the wedding owner.")
        return code


class WeddingForm(forms.ModelForm):
    class Meta:
        model = Wedding
        fields = [
            "couple_names", "tagline", "wedding_date", "rsvp_deadline",
            "destination", "venue_name", "venue_address", "map_link", "arrival_help",
            "host_contact_name", "host_contact_phone", "invite_message", "invitation_file",
        ]
        widgets = {
            "wedding_date": date_widget(),
            "rsvp_deadline": date_widget(),
            "venue_address": forms.Textarea(attrs={"rows": 2}),
            "arrival_help": forms.Textarea(attrs={"rows": 3}),
            "invite_message": forms.Textarea(attrs={"rows": 7}),
        }


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["name", "starts_at", "ends_at", "venue", "address", "map_link", "dress_code", "description"]
        widgets = {
            "starts_at": dt_widget(),
            "ends_at": dt_widget(),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ("starts_at", "ends_at"):
            self.fields[f].input_formats = DT_INPUTS

    def clean(self):
        data = super().clean()
        starts_at = data.get("starts_at")
        ends_at = data.get("ends_at")
        if starts_at and ends_at and ends_at < starts_at:
            self.add_error("ends_at", "The end time must be after the start time.")
        return data


class GuestForm(forms.ModelForm):
    """Used by the host to add / edit a guest and (if needed) record a reply received by phone."""

    class Meta:
        model = Guest
        fields = [
            "name", "phone", "email", "side", "max_members", "events", "host_note",
            "status", "members_coming", "member_names", "attending_events", "guest_note",
            "arrival_datetime", "arrival_mode", "arrival_from", "arrival_details",
            "needs_pickup", "needs_stay",
        ]
        widgets = {
            "events": forms.CheckboxSelectMultiple,
            "attending_events": forms.CheckboxSelectMultiple,
            "arrival_datetime": dt_widget(),
            "host_note": forms.Textarea(attrs={"rows": 2}),
            "member_names": forms.Textarea(attrs={"rows": 2}),
            "guest_note": forms.Textarea(attrs={"rows": 2}),
            "max_members": forms.NumberInput(attrs={"min": 1}),
            "members_coming": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, wedding=None, **kwargs):
        super().__init__(*args, **kwargs)
        events = wedding.events.all() if wedding else Event.objects.none()
        self.fields["events"].queryset = events
        self.fields["attending_events"].queryset = events
        self.fields["arrival_datetime"].input_formats = DT_INPUTS
        if not self.instance.pk and wedding:
            self.fields["events"].initial = list(events.values_list("pk", flat=True))

    def clean(self):
        data = super().clean()
        mx = data.get("max_members") or 1
        n = data.get("members_coming") or 0
        if n > mx:
            self.add_error("members_coming", f"Cannot be more than the {mx} seats invited.")
        if data.get("status") == Guest.Status.YES and n < 1:
            self.add_error("members_coming", "Enter how many people are coming.")
        return data


class QuickAddForm(forms.Form):
    lines = forms.CharField(
        label="One guest per line",
        widget=forms.Textarea(attrs={"rows": 8, "placeholder": "Sharma family, 9876543210, 4\nRahul Verma, 9123456789, 1"}),
        help_text="Format: Name, phone, seats  (phone and seats are optional)",
    )
    side = forms.ChoiceField(choices=Guest.Side.choices, initial=Guest.Side.COMMON)


class RSVPForm(forms.ModelForm):
    """What the guest sees on their personal invitation page."""

    status = forms.ChoiceField(
        label="Will you be joining us?",
        choices=[
            (Guest.Status.YES, "Yes, we'll be there 🎉"),
            (Guest.Status.MAYBE, "Not sure yet 🤔"),
            (Guest.Status.NO, "Sorry, can't make it 😔"),
        ],
        widget=forms.RadioSelect,
    )
    members_coming = forms.IntegerField(
        label="How many people are coming (including you)?",
        min_value=0, required=False,
        widget=forms.NumberInput(attrs={"inputmode": "numeric"}),
    )

    class Meta:
        model = Guest
        fields = [
            "status", "members_coming", "member_names", "attending_events",
            "arrival_datetime", "arrival_mode", "arrival_from", "arrival_details",
            "needs_pickup", "needs_stay", "guest_note",
        ]
        widgets = {
            "attending_events": forms.CheckboxSelectMultiple,
            "arrival_datetime": dt_widget(),
            "member_names": forms.Textarea(attrs={"rows": 2, "placeholder": "e.g. Ramesh, Sunita, Aarav (8)"}),
            "guest_note": forms.Textarea(attrs={"rows": 2, "placeholder": "Anything you'd like us to know?"}),
            "arrival_details": forms.TextInput(attrs={"placeholder": "e.g. Rajdhani Exp 12951 / Indigo 6E-203 / Jaipur Junction"}),
            "arrival_from": forms.TextInput(attrs={"placeholder": "e.g. Mumbai"}),
        }
        labels = {
            "member_names": "Names of everyone coming",
            "attending_events": "Which functions will you attend?",
            "arrival_datetime": "When will you reach us?",
            "needs_pickup": "We need a pickup from the station / airport",
            "needs_stay": "We need a place to stay",
            "guest_note": "Message for the couple",
        }

    def __init__(self, *args, guest, **kwargs):
        super().__init__(*args, **kwargs)
        self.guest = guest
        self.fields["attending_events"].queryset = guest.events.all()
        self.fields["attending_events"].required = False
        self.fields["members_coming"].widget.attrs.update({"min": 0, "max": guest.max_members})
        self.fields["arrival_datetime"].input_formats = DT_INPUTS

    def clean(self):
        data = super().clean()
        status = data.get("status")
        n = data.get("members_coming") or 0
        mx = self.guest.max_members
        if status == Guest.Status.YES and not (1 <= n <= mx):
            self.add_error("members_coming", f"Please enter a number between 1 and {mx}.")
        elif status == Guest.Status.MAYBE and n > mx:
            self.add_error("members_coming", f"We have kept {mx} seat(s) for you.")
        if status == Guest.Status.NO:
            n = 0
            data["attending_events"] = Event.objects.none()
            data["needs_pickup"] = False
            data["needs_stay"] = False
        data["members_coming"] = n
        return data
