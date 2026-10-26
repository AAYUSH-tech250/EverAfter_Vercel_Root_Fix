import uuid
import secrets
import string

from django.db import models
from django.conf import settings
from django.urls import reverse

def make_invite_code():
    alphabet = string.ascii_uppercase + string.digits
    return "WED-" + "".join(secrets.choice(alphabet) for _ in range(8))


DEFAULT_INVITE = (
    "Namaste {name}! 🙏\n\n"
    "You are warmly invited to the wedding of {couple}.\n"
    "Please open your personal invitation to see all the functions and let us know if you can join us:\n"
    "{link}"
)


class Wedding(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="planned_weddings")
    invite_code = models.CharField(max_length=16, unique=True, default=make_invite_code, editable=False)
    invitation_file = models.FileField(upload_to="invitations/", blank=True)
    couple_names = models.CharField(max_length=120, default="Bride & Groom")
    tagline = models.CharField(max_length=200, blank=True, default="Together with our families, we invite you to celebrate.")
    wedding_date = models.DateField(null=True, blank=True)
    destination = models.CharField("Destination city / town", max_length=150, blank=True)
    venue_name = models.CharField(max_length=200, blank=True)
    venue_address = models.TextField(blank=True)
    map_link = models.URLField("Google Maps link", blank=True)
    arrival_help = models.TextField(
        "How to reach (shown to guests)", blank=True,
        help_text="Nearest airport / railway station, travel tips, who to call on arrival.",
    )
    host_contact_name = models.CharField(max_length=100, blank=True)
    host_contact_phone = models.CharField(max_length=30, blank=True)
    rsvp_deadline = models.DateField("Please reply by", null=True, blank=True)
    invite_message = models.TextField(
        "WhatsApp invitation message", default=DEFAULT_INVITE,
        help_text="Use {name}, {couple} and {link} - they are filled in automatically.",
    )

    def __str__(self):
        return self.couple_names

    @classmethod
    def for_user(cls, user):
        """Return only the current owner's wedding; legacy staff can claim the legacy singleton."""
        if user.is_authenticated:
            wedding = cls.objects.filter(owner=user).first()
            if wedding:
                return wedding
            if user.is_staff:
                legacy = cls.objects.filter(owner__isnull=True).first()
                if legacy:
                    legacy.owner = user
                    legacy.save(update_fields=["owner"])
                    return legacy
        return None

    @classmethod
    def get_solo(cls):
        # Kept for compatibility with legacy integrations; app views use for_user().
        return cls.objects.first() or cls.objects.create()


class Event(models.Model):
    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name="events")
    name = models.CharField(max_length=120, help_text="e.g. Mehendi, Sangeet, Haldi, Wedding, Reception")
    starts_at = models.DateTimeField("Starts")
    ends_at = models.DateTimeField("Ends (optional)", null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True, help_text="Leave empty to use the main venue.")
    address = models.CharField(max_length=300, blank=True)
    map_link = models.URLField(blank=True)
    dress_code = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return self.name

    @property
    def display_venue(self):
        return self.venue or self.wedding.venue_name


class Guest(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="planner_guest")
    class Status(models.TextChoices):
        PENDING = "pending", "Not replied"
        YES = "yes", "Coming"
        MAYBE = "maybe", "Not sure yet"
        NO = "no", "Can't come"

    class Side(models.TextChoices):
        BRIDE = "bride", "Bride side"
        GROOM = "groom", "Groom side"
        COMMON = "common", "Common / Friends"

    class Mode(models.TextChoices):
        TRAIN = "train", "Train"
        FLIGHT = "flight", "Flight"
        BUS = "bus", "Bus"
        CAR = "car", "Own car / cab"
        OTHER = "other", "Other"

    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name="guests")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # who is invited
    name = models.CharField("Guest / family name", max_length=150)
    phone = models.CharField("WhatsApp / phone", max_length=30, blank=True)
    email = models.EmailField(blank=True)
    side = models.CharField(max_length=10, choices=Side.choices, default=Side.COMMON)
    max_members = models.PositiveSmallIntegerField("Seats invited", default=1)
    events = models.ManyToManyField(Event, blank=True, related_name="invited_guests", verbose_name="Invited to")
    invite_sent_at = models.DateTimeField(null=True, blank=True)
    host_note = models.TextField("Private note (only you see this)", blank=True)

    # the reply
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    members_coming = models.PositiveSmallIntegerField("People coming", default=0)
    member_names = models.TextField("Names of people coming", blank=True)
    attending_events = models.ManyToManyField(Event, blank=True, related_name="attending_guests", verbose_name="Will attend")
    responded_at = models.DateTimeField(null=True, blank=True)
    guest_note = models.TextField("Message from guest", blank=True)

    # travel
    arrival_datetime = models.DateTimeField("Arrival date & time", null=True, blank=True)
    arrival_mode = models.CharField("Travelling by", max_length=10, choices=Mode.choices, blank=True)
    arrival_from = models.CharField("Coming from (city)", max_length=100, blank=True)
    arrival_details = models.CharField(
        "Train / flight no. or station / airport", max_length=150, blank=True,
    )
    needs_pickup = models.BooleanField("Needs pickup from station / airport", default=False)
    needs_stay = models.BooleanField("Needs a place to stay", default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def rsvp_path(self):
        return reverse("rsvp", args=[self.token])
