from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0002_appointment_unique_active_employee_timeslot'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='client_name',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='appointment',
            name='client_phone',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='client_appointments', to=settings.AUTH_USER_MODEL),
        ),
    ]
