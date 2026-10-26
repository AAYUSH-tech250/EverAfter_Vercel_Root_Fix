# Initial schema for the wedding planner application.
import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Wedding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('couple_names', models.CharField(default='Bride & Groom', max_length=120)),
                ('tagline', models.CharField(blank=True, default='Together with our families, we invite you to celebrate.', max_length=200)),
                ('wedding_date', models.DateField(blank=True, null=True)),
                ('destination', models.CharField(blank=True, max_length=150, verbose_name='Destination city / town')),
                ('venue_name', models.CharField(blank=True, max_length=200)),
                ('venue_address', models.TextField(blank=True)),
                ('map_link', models.URLField(blank=True, verbose_name='Google Maps link')),
                ('arrival_help', models.TextField(blank=True, help_text='Nearest airport / railway station, travel tips, who to call on arrival.', verbose_name='How to reach (shown to guests)')),
                ('host_contact_name', models.CharField(blank=True, max_length=100)),
                ('host_contact_phone', models.CharField(blank=True, max_length=30)),
                ('rsvp_deadline', models.DateField(blank=True, null=True, verbose_name='Please reply by')),
                ('invite_message', models.TextField(default='Namaste {name}! 🙏\n\nYou are warmly invited to the wedding of {couple}.\nPlease open your personal invitation to see all the functions and let us know if you can join us:\n{link}', help_text='Use {name}, {couple} and {link} - they are filled in automatically.', verbose_name='WhatsApp invitation message')),
            ],
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='e.g. Mehendi, Sangeet, Haldi, Wedding, Reception', max_length=120)),
                ('starts_at', models.DateTimeField(verbose_name='Starts')),
                ('ends_at', models.DateTimeField(blank=True, null=True, verbose_name='Ends (optional)')),
                ('venue', models.CharField(blank=True, help_text='Leave empty to use the main venue.', max_length=200)),
                ('address', models.CharField(blank=True, max_length=300)),
                ('map_link', models.URLField(blank=True)),
                ('dress_code', models.CharField(blank=True, max_length=150)),
                ('description', models.TextField(blank=True)),
                ('wedding', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='core.wedding')),
            ],
            options={'ordering': ['starts_at']},
        ),
        migrations.CreateModel(
            name='Guest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=150, verbose_name='Guest / family name')),
                ('phone', models.CharField(blank=True, max_length=30, verbose_name='WhatsApp / phone')),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('side', models.CharField(choices=[('bride', 'Bride side'), ('groom', 'Groom side'), ('common', 'Common / Friends')], default='common', max_length=10)),
                ('max_members', models.PositiveSmallIntegerField(default=1, verbose_name='Seats invited')),
                ('invite_sent_at', models.DateTimeField(blank=True, null=True)),
                ('host_note', models.TextField(blank=True, verbose_name='Private note (only you see this)')),
                ('status', models.CharField(choices=[('pending', 'Not replied'), ('yes', 'Coming'), ('maybe', 'Not sure yet'), ('no', "Can't come")], default='pending', max_length=10)),
                ('members_coming', models.PositiveSmallIntegerField(default=0, verbose_name='People coming')),
                ('member_names', models.TextField(blank=True, verbose_name='Names of people coming')),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('guest_note', models.TextField(blank=True, verbose_name='Message from guest')),
                ('arrival_datetime', models.DateTimeField(blank=True, null=True, verbose_name='Arrival date & time')),
                ('arrival_mode', models.CharField(blank=True, choices=[('train', 'Train'), ('flight', 'Flight'), ('bus', 'Bus'), ('car', 'Own car / cab'), ('other', 'Other')], max_length=10, verbose_name='Travelling by')),
                ('arrival_from', models.CharField(blank=True, max_length=100, verbose_name='Coming from (city)')),
                ('arrival_details', models.CharField(blank=True, max_length=150, verbose_name='Train / flight no. or station / airport')),
                ('needs_pickup', models.BooleanField(default=False, verbose_name='Needs pickup from station / airport')),
                ('needs_stay', models.BooleanField(default=False, verbose_name='Needs a place to stay')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('attending_events', models.ManyToManyField(blank=True, related_name='attending_guests', to='core.event', verbose_name='Will attend')),
                ('events', models.ManyToManyField(blank=True, related_name='invited_guests', to='core.event', verbose_name='Invited to')),
                ('wedding', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='guests', to='core.wedding')),
            ],
            options={'ordering': ['name']},
        ),
    ]
