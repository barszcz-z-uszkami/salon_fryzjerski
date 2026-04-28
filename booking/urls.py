from django.urls import path

from booking.views import (
    appointment_calendar_view,
    appointment_availability_view,
    cancel_appointment_view,
    create_appointment_view,
    employee_appointments_view,
    employee_create_appointment_view,
    employee_edit_appointment_view,
    employee_update_status_view,
    edit_appointment_view,
    public_schedule_view,
    service_list_view,
)


urlpatterns = [
    path('terminarz/', public_schedule_view, name='public_schedule'),
    path('services/', service_list_view, name='service_list'),
    path('appointments/availability/', appointment_availability_view, name='appointment_availability'),
    path('appointments/calendar/', appointment_calendar_view, name='appointment_calendar'),
    path('appointments/new/', create_appointment_view, name='create_appointment'),
    path('appointments/<int:appointment_id>/edit/', edit_appointment_view, name='edit_appointment'),
    path('appointments/<int:appointment_id>/cancel/', cancel_appointment_view, name='cancel_appointment'),
    path('employee/appointments/', employee_appointments_view, name='employee_appointments'),
    path('employee/appointments/new/', employee_create_appointment_view, name='employee_create_appointment'),
    path('employee/appointments/<int:appointment_id>/edit/', employee_edit_appointment_view, name='employee_edit_appointment'),
    path('employee/appointments/<int:appointment_id>/status/', employee_update_status_view, name='employee_update_status'),
]
