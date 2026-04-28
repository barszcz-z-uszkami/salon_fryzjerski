from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from calendar import monthrange
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import datetime, timedelta, time

from accounts.models import User
from booking.forms import AppointmentForm
from booking.models import Appointment, Service


def is_client(user):
    return user.is_authenticated and user.role == 'client'


def is_employee(user):
    return user.is_authenticated and user.role == 'employee'


OPENING_TIME = time(hour=10, minute=0)
CLOSING_TIME = time(hour=20, minute=0)
SLOT_INTERVAL_MINUTES = 15


def _get_minimum_bookable_time_today():
    now = timezone.localtime()
    candidate = now + timedelta(minutes=15)
    rounded_minute = ((candidate.minute + SLOT_INTERVAL_MINUTES - 1) // SLOT_INTERVAL_MINUTES) * SLOT_INTERVAL_MINUTES
    if rounded_minute >= 60:
        candidate = candidate.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        candidate = candidate.replace(minute=rounded_minute, second=0, microsecond=0)
    return candidate.time()


def _is_today_closed_for_new_bookings():
    return _get_minimum_bookable_time_today() >= CLOSING_TIME


def _generate_time_slots():
    start = datetime.combine(timezone.localdate(), OPENING_TIME)
    end = datetime.combine(timezone.localdate(), CLOSING_TIME)
    slots = []

    while start < end:
        slots.append(start.strftime('%H:%M'))
        start += timedelta(minutes=SLOT_INTERVAL_MINUTES)

    return slots


def _next_open_date(start_date):
    current = start_date
    while current.weekday() == 6:
        current += timedelta(days=1)
    return current


def _get_booked_slots(employee, appointment_date, appointment_to_exclude_id=None):
    queryset = Appointment.objects.filter(
        employee=employee,
        date=appointment_date,
    ).exclude(status='cancelled')

    if appointment_to_exclude_id:
        queryset = queryset.exclude(pk=appointment_to_exclude_id)

    return set(queryset.values_list('time', flat=True))


def _get_available_slots(employee, appointment_date, service_duration_minutes, appointment_to_exclude_id=None):
    if appointment_date.weekday() == 6:
        return []

    all_slots = _generate_time_slots()
    appointments_qs = Appointment.objects.filter(
        employee=employee,
        date=appointment_date,
    ).exclude(status='cancelled')

    if appointment_to_exclude_id:
        appointments_qs = appointments_qs.exclude(pk=appointment_to_exclude_id)

    occupied_ranges = []
    for appointment in appointments_qs.select_related('service'):
        start_dt = datetime.combine(appointment_date, appointment.time)
        end_dt = start_dt + timedelta(minutes=appointment.service.duration_minutes)
        occupied_ranges.append((start_dt, end_dt))

    day_end_dt = datetime.combine(appointment_date, CLOSING_TIME)
    available = []
    for slot in all_slots:
        slot_time = datetime.strptime(slot, '%H:%M').time()
        slot_start = datetime.combine(appointment_date, slot_time)
        slot_end = slot_start + timedelta(minutes=service_duration_minutes)
        if slot_end > day_end_dt:
            continue
        overlaps = any(slot_start < end and slot_end > start for start, end in occupied_ranges)
        if not overlaps:
            available.append(slot)

    if appointment_date == timezone.localdate():
        minimum_time = _get_minimum_bookable_time_today()
        available = [slot for slot in available if datetime.strptime(slot, '%H:%M').time() >= minimum_time]

    return available


def _monday_of_week_containing(d):
    return d - timedelta(days=d.weekday())


def public_schedule_view(request):
    employees = list(User.objects.filter(role='employee').order_by('first_name', 'last_name', 'username'))
    today = timezone.localdate()

    week_raw = request.GET.get('week', '').strip()
    if week_raw:
        try:
            parsed_week = datetime.strptime(week_raw, '%Y-%m-%d').date()
            week_start = _monday_of_week_containing(parsed_week)
        except ValueError:
            week_start = _monday_of_week_containing(today)
    else:
        week_start = _monday_of_week_containing(today)

    week_end = week_start + timedelta(days=6)
    week_days = [week_start + timedelta(days=i) for i in range(7)]
    weekday_labels = ['Pn', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Nd']

    employee_id = request.GET.get('employee', '').strip()
    selected_employee = None
    if employees:
        if employee_id.isdigit():
            selected_employee = next((e for e in employees if str(e.pk) == employee_id), None)
        if selected_employee is None:
            selected_employee = employees[0]

    today_salon_closed = _is_today_closed_for_new_bookings()

    def is_day_selectable(d):
        if d.weekday() == 6:
            return False
        if d < today:
            return False
        if d == today and today_salon_closed:
            return False
        return True

    def first_selectable_day_in_week():
        for d in week_days:
            if is_day_selectable(d):
                return d
        return week_start

    selected_day = first_selectable_day_in_week()
    day_raw = request.GET.get('day', '').strip()
    if day_raw:
        try:
            parsed_day = datetime.strptime(day_raw, '%Y-%m-%d').date()
            if week_start <= parsed_day <= week_end and is_day_selectable(parsed_day):
                selected_day = parsed_day
        except ValueError:
            pass

    day_tabs = []
    if selected_employee:
        for d in week_days:
            free_slots = _get_available_slots(selected_employee, d, SLOT_INTERVAL_MINUTES)
            today_closed_evening = d == today and today_salon_closed
            clickable = is_day_selectable(d)
            day_tabs.append(
                {
                    'date': d,
                    'iso': d.isoformat(),
                    'label': weekday_labels[d.weekday()],
                    'free_count': len(free_slots),
                    'is_today': d == today,
                    'is_past': d < today,
                    'is_sunday': d.weekday() == 6,
                    'today_closed_evening': today_closed_evening,
                    'clickable': clickable,
                    'selected': d == selected_day,
                }
            )

    all_time_slots = _generate_time_slots()
    day_slots = []
    if selected_employee:
        available_set = set(
            _get_available_slots(selected_employee, selected_day, SLOT_INTERVAL_MINUTES)
        )
        for time_label in all_time_slots:
            day_slots.append({'time': time_label, 'available': time_label in available_set})

    prev_week = (week_start - timedelta(days=7)).isoformat()
    next_week = (week_start + timedelta(days=7)).isoformat()

    return render(
        request,
        'booking/public_schedule.html',
        {
            'employees': employees,
            'selected_employee': selected_employee,
            'week_start': week_start,
            'week_end': week_end,
            'selected_day': selected_day,
            'day_tabs': day_tabs,
            'day_slots': day_slots,
            'prev_week': prev_week,
            'next_week': next_week,
            'today': today,
        },
    )


def service_list_view(request):
    services = Service.objects.all().order_by('name')
    return render(request, 'booking/service_list.html', {'services': services})


@login_required
def my_appointments_view(request):
    today = timezone.localdate()
    upcoming_appointments = Appointment.objects.filter(
        client=request.user,
        date__gte=today,
    ).exclude(status='cancelled').order_by('date', 'time')
    history_appointments = Appointment.objects.filter(
        client=request.user,
        date__lt=today,
    ).order_by('-date', '-time')
    cancelled_appointments = Appointment.objects.filter(
        client=request.user,
        status='cancelled',
    ).order_by('-date', '-time')

    return render(
        request,
        'booking/my_appointments.html',
        {
            'upcoming_appointments': upcoming_appointments,
            'history_appointments': history_appointments,
            'cancelled_appointments': cancelled_appointments,
            'today': today,
        },
    )


@login_required
def create_appointment_view(request):
    if not is_client(request.user):
        messages.error(request, 'Tylko klient może umówić wizytę.')
        return redirect('dashboard')

    services = Service.objects.all().order_by('name')
    employees = User.objects.filter(role='employee').order_by('first_name', 'last_name', 'username')
    selected_service = None
    selected_employee = None
    selected_service_id = ''
    selected_employee_id = ''
    selected_date = ''
    selected_time = ''
    selected_slots = []

    if request.method == 'POST':
        service_id = request.POST.get('service', '').strip()
        employee_id = request.POST.get('employee', '').strip()
        selected_service_id = service_id
        selected_employee_id = employee_id
        selected_date = request.POST.get('date', '').strip()
        selected_time = request.POST.get('time', '').strip()

        if not service_id:
            messages.error(request, 'Wybierz usługę.')
        if not employee_id:
            messages.error(request, 'Wybierz pracownika.')

        if service_id and employee_id and selected_date and selected_time:
            selected_service = get_object_or_404(Service, pk=service_id)
            selected_employee = get_object_or_404(User, pk=employee_id, role='employee')

            try:
                parsed_date = datetime.strptime(selected_date, '%d/%m/%Y').date()
            except ValueError:
                messages.error(request, 'Podaj datę w formacie dd/mm/rrrr.')
                parsed_date = None

            if parsed_date:
                if parsed_date < timezone.localdate():
                    messages.error(request, 'Nie można rezerwować terminu w przeszłości.')
                elif parsed_date.weekday() == 6:
                    messages.error(request, 'Salon nie pracuje w niedzielę.')
                else:
                    available_slots = _get_available_slots(
                        selected_employee,
                        parsed_date,
                        selected_service.duration_minutes,
                    )
                    if selected_time not in available_slots:
                        messages.error(request, 'Wybrana godzina nie jest już dostępna.')
                    else:
                        Appointment.objects.create(
                            client=request.user,
                            employee=selected_employee,
                            service=selected_service,
                            date=parsed_date,
                            time=datetime.strptime(selected_time, '%H:%M').time(),
                            status='new',
                        )
                        messages.success(request, 'Wizyta została zarezerwowana.')
                        return redirect('my_appointments')

        if employee_id and employee_id.isdigit() and selected_date:
            selected_employee = User.objects.filter(pk=employee_id, role='employee').first()
            if selected_employee:
                try:
                    parsed_date = datetime.strptime(selected_date, '%d/%m/%Y').date()
                    selected_service = Service.objects.filter(pk=service_id).first()
                    if selected_service:
                        selected_slots = _get_available_slots(
                            selected_employee,
                            parsed_date,
                            selected_service.duration_minutes,
                        )
                except ValueError:
                    selected_slots = []

    return render(
        request,
        'booking/appointment_scheduler.html',
        {
            'services': services,
            'employees': employees,
            'selected_service': selected_service,
            'selected_employee': selected_employee,
            'selected_service_id': selected_service_id,
            'selected_employee_id': selected_employee_id,
            'selected_date': selected_date,
            'selected_time': selected_time,
            'available_slots': selected_slots,
            'today': timezone.localdate(),
            'today_is_closed': _is_today_closed_for_new_bookings(),
        },
    )


@login_required
def edit_appointment_view(request, appointment_id):
    if not is_client(request.user):
        messages.error(request, 'Brak dostępu do edycji wizyty.')
        return redirect('dashboard')

    appointment = get_object_or_404(Appointment, id=appointment_id, client=request.user)
    if appointment.status == 'cancelled' or appointment.date < timezone.localdate():
        messages.error(request, 'Tej wizyty nie można już edytować.')
        return redirect('my_appointments')

    occupied_slots = []
    all_slots = _generate_time_slots()

    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Zmiany w wizycie zostały zapisane.')
            return redirect('my_appointments')
        selected_employee = form.cleaned_data.get('employee') if hasattr(form, 'cleaned_data') else None
        selected_date = form.cleaned_data.get('date') if hasattr(form, 'cleaned_data') else None
        if selected_employee and selected_date:
            occupied_time_values = _get_booked_slots(selected_employee, selected_date, appointment.id)
            occupied_slots = sorted(slot.strftime('%H:%M') for slot in occupied_time_values)
    else:
        form = AppointmentForm(instance=appointment)
        occupied_time_values = _get_booked_slots(appointment.employee, appointment.date, appointment.id)
        occupied_slots = sorted(slot.strftime('%H:%M') for slot in occupied_time_values)

    return render(
        request,
        'booking/appointment_form.html',
        {
            'form': form,
            'is_edit_mode': True,
            'appointment': appointment,
            'occupied_slots': occupied_slots,
            'all_slots': all_slots,
        },
    )


@login_required
def cancel_appointment_view(request, appointment_id):
    if not is_client(request.user):
        messages.error(request, 'Brak dostępu do odwołania wizyty.')
        return redirect('dashboard')

    appointment = get_object_or_404(Appointment, id=appointment_id, client=request.user)
    if request.method == 'POST' and appointment.status != 'cancelled' and appointment.date >= timezone.localdate():
        appointment.status = 'cancelled'
        appointment.save(update_fields=['status'])
        messages.success(request, 'Wizyta została odwołana.')
    elif request.method == 'POST':
        messages.error(request, 'Nie można odwołać tej wizyty.')

    return redirect('my_appointments')


@login_required
def employee_appointments_view(request):
    if not is_employee(request.user):
        messages.error(request, 'To sekcja dostępna tylko dla pracownika.')
        return redirect('dashboard')

    employees = User.objects.filter(role='employee').order_by('first_name', 'last_name', 'username')
    selected_employee = request.GET.get('employee', '').strip()
    selected_status = request.GET.get('status', '').strip()
    today = timezone.localdate()

    week_raw = request.GET.get('week', '').strip()
    if week_raw:
        try:
            parsed_week = datetime.strptime(week_raw, '%Y-%m-%d').date()
            week_start = _monday_of_week_containing(parsed_week)
        except ValueError:
            week_start = _monday_of_week_containing(today)
    else:
        week_start = _monday_of_week_containing(today)
    week_end = week_start + timedelta(days=6)
    week_days = [week_start + timedelta(days=i) for i in range(7)]

    selected_employee_obj = request.user
    if selected_employee and selected_employee.isdigit():
        candidate = employees.filter(pk=selected_employee).first()
        if candidate:
            selected_employee_obj = candidate

    appointments = Appointment.objects.select_related('client', 'employee', 'service').filter(
        employee=selected_employee_obj,
        date__range=(week_start, week_end),
    )
    if selected_status:
        appointments = appointments.filter(status=selected_status)
    else:
        appointments = appointments.exclude(status='cancelled')
    appointments = appointments.order_by('date', 'time')

    week_day_map = {day: index for index, day in enumerate(week_days)}
    calendar_start_minutes = OPENING_TIME.hour * 60 + OPENING_TIME.minute
    calendar_end_minutes = CLOSING_TIME.hour * 60 + CLOSING_TIME.minute
    calendar_total_minutes = calendar_end_minutes - calendar_start_minutes
    minute_height = 1.1
    calendar_height = int(calendar_total_minutes * minute_height)

    appointment_blocks = []
    for appointment in appointments:
        day_index = week_day_map.get(appointment.date)
        if day_index is None:
            continue
        start_minutes = appointment.time.hour * 60 + appointment.time.minute
        start_offset = max(start_minutes - calendar_start_minutes, 0)
        duration = appointment.service.duration_minutes
        if start_offset >= calendar_total_minutes:
            continue
        duration = min(duration, calendar_total_minutes - start_offset)
        appointment_blocks.append(
            {
                'appointment': appointment,
                'day_index': day_index,
                'top': int(start_offset * minute_height),
                'height': max(int(duration * minute_height), 78),
                'start_label': appointment.time.strftime('%H:%M'),
                'end_label': (datetime.combine(appointment.date, appointment.time) + timedelta(minutes=appointment.service.duration_minutes)).strftime('%H:%M'),
            }
        )

    hour_labels = []
    current_hour = OPENING_TIME.hour
    while current_hour < CLOSING_TIME.hour:
        hour_labels.append(f'{current_hour:02d}:00')
        current_hour += 1

    prev_week = (week_start - timedelta(days=7)).isoformat()
    next_week = (week_start + timedelta(days=7)).isoformat()

    return render(
        request,
        'booking/employee_appointments.html',
        {
            'appointments': appointments,
            'employees': employees,
            'status_choices': Appointment.STATUS_CHOICES,
            'selected_employee': str(selected_employee_obj.pk),
            'selected_status': selected_status,
            'week_start': week_start,
            'week_end': week_end,
            'week_days': week_days,
            'appointment_blocks': appointment_blocks,
            'hour_labels': hour_labels,
            'calendar_height': calendar_height,
            'prev_week': prev_week,
            'next_week': next_week,
        },
    )


@login_required
def employee_create_appointment_view(request):
    if not is_employee(request.user):
        messages.error(request, 'To sekcja dostępna tylko dla pracownika.')
        return redirect('dashboard')

    services = Service.objects.all().order_by('name')
    employees = User.objects.filter(role='employee').order_by('first_name', 'last_name', 'username')
    selected_service = None
    selected_employee = None
    selected_service_id = ''
    selected_employee_id = ''
    selected_date = ''
    selected_time = ''
    selected_client_name = ''
    selected_client_phone = ''
    selected_slots = []

    if request.method == 'POST':
        service_id = request.POST.get('service', '').strip()
        employee_id = request.POST.get('employee', '').strip()
        selected_client_name = request.POST.get('client_name', '').strip()
        selected_client_phone = request.POST.get('client_phone', '').strip()
        selected_service_id = service_id
        selected_employee_id = employee_id
        selected_date = request.POST.get('date', '').strip()
        selected_time = request.POST.get('time', '').strip()

        if not selected_client_name:
            messages.error(request, 'Podaj imię i nazwisko klienta.')
        if not selected_client_phone:
            messages.error(request, 'Podaj numer telefonu klienta.')
        if not service_id:
            messages.error(request, 'Wybierz usługę.')
        if not employee_id:
            messages.error(request, 'Wybierz pracownika.')

        if service_id and employee_id and selected_date and selected_time and selected_client_name and selected_client_phone:
            selected_service = get_object_or_404(Service, pk=service_id)
            selected_employee = get_object_or_404(User, pk=employee_id, role='employee')

            try:
                parsed_date = datetime.strptime(selected_date, '%d/%m/%Y').date()
            except ValueError:
                messages.error(request, 'Podaj datę w formacie dd/mm/rrrr.')
                parsed_date = None

            if parsed_date:
                if parsed_date < timezone.localdate():
                    messages.error(request, 'Nie można rezerwować terminu w przeszłości.')
                elif parsed_date.weekday() == 6:
                    messages.error(request, 'Salon nie pracuje w niedzielę.')
                else:
                    available_slots = _get_available_slots(
                        selected_employee,
                        parsed_date,
                        selected_service.duration_minutes,
                    )
                    if selected_time not in available_slots:
                        messages.error(request, 'Wybrana godzina nie jest już dostępna.')
                    else:
                        Appointment.objects.create(
                            client=None,
                            client_name=selected_client_name,
                            client_phone=selected_client_phone,
                            employee=selected_employee,
                            service=selected_service,
                            date=parsed_date,
                            time=datetime.strptime(selected_time, '%H:%M').time(),
                            status='new',
                        )
                        messages.success(request, 'Wizyta została zarezerwowana.')
                        return redirect('employee_appointments')

        if employee_id and employee_id.isdigit() and selected_date:
            selected_employee = User.objects.filter(pk=employee_id, role='employee').first()
            if selected_employee:
                try:
                    parsed_date = datetime.strptime(selected_date, '%d/%m/%Y').date()
                    selected_service = Service.objects.filter(pk=service_id).first()
                    if selected_service:
                        selected_slots = _get_available_slots(
                            selected_employee,
                            parsed_date,
                            selected_service.duration_minutes,
                        )
                except ValueError:
                    selected_slots = []

    return render(
        request,
        'booking/employee_appointment_scheduler.html',
        {
            'services': services,
            'employees': employees,
            'selected_service': selected_service,
            'selected_employee': selected_employee,
            'selected_service_id': selected_service_id,
            'selected_employee_id': selected_employee_id,
            'selected_date': selected_date,
            'selected_time': selected_time,
            'selected_client_name': selected_client_name,
            'selected_client_phone': selected_client_phone,
            'available_slots': selected_slots,
            'today': timezone.localdate(),
            'today_is_closed': _is_today_closed_for_new_bookings(),
            'is_edit_mode': False,
            'submit_label': 'Zarejestruj wizytę',
        },
    )


@login_required
def employee_edit_appointment_view(request, appointment_id):
    if not is_employee(request.user):
        messages.error(request, 'To sekcja dostępna tylko dla pracownika.')
        return redirect('dashboard')

    appointment = get_object_or_404(Appointment, id=appointment_id)
    services = Service.objects.all().order_by('name')
    employees = User.objects.filter(role='employee').order_by('first_name', 'last_name', 'username')
    status_values = {value for value, _ in Appointment.STATUS_CHOICES}

    selected_service = appointment.service
    selected_employee = appointment.employee
    selected_service_id = str(appointment.service_id)
    selected_employee_id = str(appointment.employee_id)
    selected_date = appointment.date.strftime('%d/%m/%Y')
    selected_time = appointment.time.strftime('%H:%M')
    selected_client_name = appointment.get_client_display_name()
    selected_client_phone = appointment.get_client_display_phone() or ''
    selected_status = appointment.status
    selected_slots = _get_available_slots(
        appointment.employee,
        appointment.date,
        appointment.service.duration_minutes,
        appointment_to_exclude_id=appointment.id,
    )

    if request.method == 'POST':
        service_id = request.POST.get('service', '').strip()
        employee_id = request.POST.get('employee', '').strip()
        selected_client_name = request.POST.get('client_name', '').strip()
        selected_client_phone = request.POST.get('client_phone', '').strip()
        selected_status = request.POST.get('status', '').strip()
        selected_service_id = service_id
        selected_employee_id = employee_id
        selected_date = request.POST.get('date', '').strip()
        selected_time = request.POST.get('time', '').strip()

        if not selected_client_name:
            messages.error(request, 'Podaj imię i nazwisko klienta.')
        if not selected_client_phone:
            messages.error(request, 'Podaj numer telefonu klienta.')
        if not service_id:
            messages.error(request, 'Wybierz usługę.')
        if not employee_id:
            messages.error(request, 'Wybierz pracownika.')
        if selected_status not in status_values:
            messages.error(request, 'Wybierz poprawny status wizyty.')

        if service_id and employee_id and selected_date and selected_time and selected_client_name and selected_client_phone and selected_status in status_values:
            selected_service = get_object_or_404(Service, pk=service_id)
            selected_employee = get_object_or_404(User, pk=employee_id, role='employee')

            try:
                parsed_date = datetime.strptime(selected_date, '%d/%m/%Y').date()
            except ValueError:
                messages.error(request, 'Podaj datę w formacie dd/mm/rrrr.')
                parsed_date = None

            if parsed_date:
                original_time_label = appointment.time.strftime('%H:%M')
                is_original_slot = (
                    parsed_date == appointment.date
                    and selected_time == original_time_label
                    and selected_employee.id == appointment.employee_id
                )

                if not is_original_slot and parsed_date < timezone.localdate():
                    messages.error(request, 'Nie można rezerwować terminu w przeszłości.')
                elif not is_original_slot and parsed_date.weekday() == 6:
                    messages.error(request, 'Salon nie pracuje w niedzielę.')
                else:
                    available_slots = _get_available_slots(
                        selected_employee,
                        parsed_date,
                        selected_service.duration_minutes,
                        appointment_to_exclude_id=appointment.id,
                    )
                    if not is_original_slot and selected_time not in available_slots:
                        messages.error(request, 'Wybrana godzina nie jest już dostępna.')
                    else:
                        appointment.client = None
                        appointment.client_name = selected_client_name
                        appointment.client_phone = selected_client_phone
                        appointment.employee = selected_employee
                        appointment.service = selected_service
                        appointment.date = parsed_date
                        appointment.time = datetime.strptime(selected_time, '%H:%M').time()
                        appointment.status = selected_status
                        appointment.save()
                        messages.success(request, 'Wizyta została zaktualizowana.')
                        return redirect('employee_appointments')

        if employee_id and employee_id.isdigit() and selected_date:
            selected_employee = User.objects.filter(pk=employee_id, role='employee').first()
            if selected_employee:
                try:
                    parsed_date = datetime.strptime(selected_date, '%d/%m/%Y').date()
                    selected_service = Service.objects.filter(pk=service_id).first()
                    if selected_service:
                        selected_slots = _get_available_slots(
                            selected_employee,
                            parsed_date,
                            selected_service.duration_minutes,
                            appointment_to_exclude_id=appointment.id,
                        )
                except ValueError:
                    selected_slots = []

    return render(
        request,
        'booking/employee_appointment_scheduler.html',
        {
            'services': services,
            'employees': employees,
            'status_choices': Appointment.STATUS_CHOICES,
            'selected_service': selected_service,
            'selected_employee': selected_employee,
            'selected_service_id': selected_service_id,
            'selected_employee_id': selected_employee_id,
            'selected_date': selected_date,
            'selected_time': selected_time,
            'selected_client_name': selected_client_name,
            'selected_client_phone': selected_client_phone,
            'selected_status': selected_status,
            'available_slots': selected_slots,
            'today': timezone.localdate(),
            'today_is_closed': _is_today_closed_for_new_bookings(),
            'is_edit_mode': True,
            'submit_label': 'Zapisz zmiany',
            'appointment_id': appointment.id,
        },
    )


@login_required
def employee_update_status_view(request, appointment_id):
    if not is_employee(request.user):
        messages.error(request, 'To sekcja dostępna tylko dla pracownika.')
        return redirect('dashboard')

    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        valid_statuses = {choice[0] for choice in Appointment.STATUS_CHOICES}
        if new_status in valid_statuses:
            appointment.status = new_status
            appointment.save(update_fields=['status'])
            messages.success(request, 'Status wizyty został zmieniony.')
        else:
            messages.error(request, 'Nieprawidłowy status wizyty.')

    return redirect('employee_appointments')


@login_required
def appointment_availability_view(request):
    if not is_client(request.user):
        return JsonResponse({'error': 'Brak dostępu.'}, status=403)

    employee_id = request.GET.get('employee')
    appointment_date = request.GET.get('date')
    appointment_id = request.GET.get('appointment_id')

    if not employee_id or not appointment_date:
        return JsonResponse({'occupied_slots': []})

    employee = get_object_or_404(User, pk=employee_id, role='employee')
    try:
        selected_date = datetime.strptime(appointment_date, '%d/%m/%Y').date()
    except ValueError:
        return JsonResponse({'occupied_slots': []})

    exclude_id = int(appointment_id) if appointment_id and appointment_id.isdigit() else None
    occupied_time_values = _get_booked_slots(employee, selected_date, exclude_id)
    occupied_slots = sorted(slot.strftime('%H:%M') for slot in occupied_time_values)

    return JsonResponse({'occupied_slots': occupied_slots})


@login_required
def appointment_calendar_view(request):
    if not (is_client(request.user) or is_employee(request.user)):
        return JsonResponse({'error': 'Brak dostępu.'}, status=403)

    employee_id = request.GET.get('employee', '').strip()
    service_id = request.GET.get('service', '').strip()
    year = request.GET.get('year', '').strip()
    month = request.GET.get('month', '').strip()
    day = request.GET.get('day', '').strip()
    appointment_id = request.GET.get('appointment_id', '').strip()
    exclude_id = int(appointment_id) if appointment_id.isdigit() else None

    if not year.isdigit() or not month.isdigit():
        return JsonResponse({'disabled_days': [], 'available_slots': []})

    employee = None
    service = None
    if employee_id and service_id:
        employee = get_object_or_404(User, pk=employee_id, role='employee')
        service = get_object_or_404(Service, pk=service_id)

    year_value = int(year)
    month_value = int(month)
    today = timezone.localdate()
    days_in_month = monthrange(year_value, month_value)[1]
    today_closed = _is_today_closed_for_new_bookings()

    disabled_days = []
    for day_value in range(1, days_in_month + 1):
        current_date = datetime(year_value, month_value, day_value).date()
        if current_date < today or current_date.weekday() == 6:
            disabled_days.append(day_value)
            continue
        if current_date == today and today_closed:
            disabled_days.append(day_value)
            continue
        if employee and service and not _get_available_slots(employee, current_date, service.duration_minutes, appointment_to_exclude_id=exclude_id):
            disabled_days.append(day_value)

    available_slots = []
    if day.isdigit() and employee and service:
        try:
            selected_date = datetime(year_value, month_value, int(day)).date()
            if selected_date >= today and selected_date.weekday() != 6:
                if selected_date == today and today_closed:
                    available_slots = []
                else:
                    available_slots = _get_available_slots(employee, selected_date, service.duration_minutes, appointment_to_exclude_id=exclude_id)
        except ValueError:
            available_slots = []

    return JsonResponse({'disabled_days': disabled_days, 'available_slots': available_slots})
