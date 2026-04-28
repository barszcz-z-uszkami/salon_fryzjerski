from datetime import datetime, timedelta

from django.utils import timezone

from booking.models import Appointment


class AutoCompleteAppointmentsMiddleware:
    """
    Automatically marks appointments as completed when their end time passes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._mark_finished_appointments_completed()
        return self.get_response(request)

    def _mark_finished_appointments_completed(self):
        now = timezone.localtime()
        today = now.date()
        current_tz = timezone.get_current_timezone()

        # Any non-cancelled/non-completed appointment from previous days is finished.
        Appointment.objects.filter(
            date__lt=today,
            status__in=['new', 'confirmed'],
        ).update(status='completed')

        todays_appointments = Appointment.objects.filter(
            date=today,
            status__in=['new', 'confirmed'],
        ).select_related('service')

        completed_ids = []
        for appointment in todays_appointments:
            start_dt = datetime.combine(appointment.date, appointment.time)
            start_dt = timezone.make_aware(start_dt, current_tz)
            end_dt = start_dt + timedelta(minutes=appointment.service.duration_minutes)
            if end_dt <= now:
                completed_ids.append(appointment.id)

        if completed_ids:
            Appointment.objects.filter(id__in=completed_ids).update(status='completed')
