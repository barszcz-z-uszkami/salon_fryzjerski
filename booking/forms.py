from django import forms
from datetime import date as date_class, datetime, time, timedelta
from django.utils import timezone

from accounts.models import User
from booking.models import Appointment, Service


class AppointmentForm(forms.ModelForm):
    OPENING_TIME = time(hour=10, minute=0)
    CLOSING_TIME = time(hour=20, minute=0)
    SLOT_INTERVAL_MINUTES = 15

    class Meta:
        model = Appointment
        fields = ['service', 'employee', 'date', 'time']
        widgets = {
            'date': forms.DateInput(
                format='%d/%m/%Y',
                attrs={
                    'placeholder': 'dd/mm/rrrr',
                    'autocomplete': 'off',
                },
            ),
            'time': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['service'].label = 'Usługa'
        self.fields['employee'].label = 'Pracownik'
        self.fields['date'].label = 'Data'
        self.fields['time'].label = 'Godzina'

        self.fields['date'].input_formats = ['%d/%m/%Y']
        self.fields['date'].error_messages['invalid'] = 'Podaj datę w formacie dd/mm/rrrr.'

        self.fields['service'].queryset = Service.objects.all().order_by('name')
        self.fields['service'].empty_label = 'Wybierz usługę'
        self.fields['service'].error_messages['required'] = 'Wybierz usługę.'

        employees = User.objects.filter(role='employee').order_by('first_name', 'last_name', 'username')
        self.fields['employee'].queryset = employees
        self.fields['employee'].empty_label = None
        if not self.is_bound and not self.instance.pk:
            self.fields['employee'].initial = employees.first()

        self.fields['time'].choices = self._build_time_choices()

    def _build_time_choices(self):
        choices = []
        current_dt = datetime.combine(date_class.today(), self.OPENING_TIME)
        end_dt = datetime.combine(date_class.today(), self.CLOSING_TIME)

        while current_dt < end_dt:
            current_time = current_dt.time()
            choices.append((current_time.strftime('%H:%M:%S'), current_time.strftime('%H:%M')))
            current_dt += timedelta(minutes=self.SLOT_INTERVAL_MINUTES)

        return choices

    def _get_minimum_bookable_time_today(self):
        now = timezone.localtime()
        candidate = now + timedelta(minutes=15)
        rounded_minute = ((candidate.minute + self.SLOT_INTERVAL_MINUTES - 1) // self.SLOT_INTERVAL_MINUTES) * self.SLOT_INTERVAL_MINUTES
        if rounded_minute >= 60:
            candidate = candidate.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            candidate = candidate.replace(minute=rounded_minute, second=0, microsecond=0)
        return candidate.time()

    def clean(self):
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get('date')
        appointment_time = cleaned_data.get('time')
        employee = cleaned_data.get('employee')
        service = cleaned_data.get('service')

        if not service:
            self.add_error('service', 'Wybierz usługę.')

        if appointment_date and appointment_date < timezone.localdate():
            self.add_error('date', 'Nie można zarezerwować wizyty w przeszłości.')

        if appointment_date and appointment_date.weekday() == 6:
            self.add_error('date', 'Salon jest nieczynny w niedzielę. Wybierz dzień od poniedziałku do soboty.')

        if appointment_time:
            if appointment_time < self.OPENING_TIME or appointment_time >= self.CLOSING_TIME:
                self.add_error('time', 'Wybierz godzinę w zakresie od 10:00 do 20:00.')
            if appointment_time.minute % self.SLOT_INTERVAL_MINUTES != 0:
                self.add_error('time', 'Wybierz slot co 15 minut.')

        if employee and employee.role != 'employee':
            self.add_error('employee', 'Wybrany użytkownik nie jest pracownikiem salonu.')

        if appointment_date and appointment_time and employee:
            if appointment_date == timezone.localdate():
                minimum_time = self._get_minimum_bookable_time_today()
                if appointment_time < minimum_time:
                    self.add_error(
                        'time',
                        f'Najbliższy dostępny termin na dziś to {minimum_time.strftime("%H:%M")} lub później.'
                    )

            appointment_start = datetime.combine(appointment_date, appointment_time)
            appointment_end = appointment_start + timedelta(minutes=service.duration_minutes if service else 0)
            conflict_qs = Appointment.objects.filter(
                employee=employee,
                date=appointment_date,
            ).exclude(status='cancelled')

            if self.instance.pk:
                conflict_qs = conflict_qs.exclude(pk=self.instance.pk)

            for existing_appointment in conflict_qs.select_related('service'):
                existing_start = datetime.combine(appointment_date, existing_appointment.time)
                existing_end = existing_start + timedelta(minutes=existing_appointment.service.duration_minutes)
                if appointment_start < existing_end and appointment_end > existing_start:
                    self.add_error(
                        'time',
                        'Ten termin nakłada się na inną wizytę wybranego pracownika.'
                    )
                    break

        return cleaned_data


class EmployeeAppointmentForm(AppointmentForm):
    class Meta(AppointmentForm.Meta):
        fields = ['client_name', 'client_phone', 'service', 'employee', 'date', 'time', 'status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client_name'].label = 'Imię i nazwisko klienta'
        self.fields['client_phone'].label = 'Numer telefonu klienta'
        self.fields['client_name'].max_length = 120
        self.fields['client_phone'].max_length = 20
        self.fields['status'].label = 'Status'

    def clean(self):
        cleaned_data = super().clean()
        client_name = (cleaned_data.get('client_name') or '').strip()
        client_phone = (cleaned_data.get('client_phone') or '').strip()

        if not client_name:
            self.add_error('client_name', 'Podaj imię i nazwisko klienta.')
        if not client_phone:
            self.add_error('client_phone', 'Podaj numer telefonu klienta.')

        cleaned_data['client_name'] = client_name
        cleaned_data['client_phone'] = client_phone
        return cleaned_data
