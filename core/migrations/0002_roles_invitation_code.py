import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import core.models

class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0001_initial'),
    ]
    operations = [
        migrations.AddField(
            model_name='wedding',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='planned_weddings', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='wedding',
            name='invite_code',
            field=models.CharField(default=core.models.make_invite_code, editable=False, max_length=16, unique=True),
        ),
        migrations.AddField(
            model_name='wedding',
            name='invitation_file',
            field=models.FileField(blank=True, upload_to='invitations/'),
        ),
        migrations.AddField(
            model_name='guest',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='planner_guest', to=settings.AUTH_USER_MODEL),
        ),
    ]
