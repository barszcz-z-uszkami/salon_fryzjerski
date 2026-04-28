from django.contrib import admin
from .models import Service, Appointment


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_minutes', 'price')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('client', 'employee', 'service', 'date', 'time', 'status')
    list_filter = ('status', 'date', 'employee')