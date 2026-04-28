from django.db import models
from django.conf import settings
from django.db.models import Q


class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.name


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('new', 'Nowa'),
        ('confirmed', 'Potwierdzona'),
        ('completed', 'Zrealizowana'),
        ('cancelled', 'Odwołana'),
    ]

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_appointments',
        null=True,
        blank=True,
    )
    client_name = models.CharField(max_length=120, blank=True)
    client_phone = models.CharField(max_length=20, blank=True)
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_appointments'
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE
    )
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'date', 'time'],
                condition=~Q(status='cancelled'),
                name='unique_active_employee_timeslot',
            ),
        ]

    def __str__(self):
        return f"{self.get_client_display_name()} - {self.service.name} - {self.date} {self.time}"

    def get_client_display_name(self):
        if self.client:
            return self.client.get_full_name() or self.client.username
        return self.client_name or 'Klient'

    def get_client_display_phone(self):
        if self.client and self.client.phone_number:
            return self.client.phone_number
        return self.client_phone