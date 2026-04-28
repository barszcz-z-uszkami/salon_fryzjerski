from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from booking.models import Appointment, Service


class BookingFlowTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client1',
            password='TestPass123!',
            role='client',
            email='client@example.com',
        )
        self.employee_user = User.objects.create_user(
            username='employee1',
            password='TestPass123!',
            role='employee',
            email='employee@example.com',
        )
        self.second_client = User.objects.create_user(
            username='client2',
            password='TestPass123!',
            role='client',
            email='client2@example.com',
        )
        self.service = Service.objects.create(
            name='Strzyzenie test',
            description='Opis testowy',
            duration_minutes=45,
            price='99.00',
        )
        self.future_date = timezone.localdate() + timedelta(days=2)

    def test_client_can_create_appointment(self):
        self.client.force_login(self.client_user)
        response = self.client.post(
            reverse('create_appointment'),
            data={
                'service': self.service.id,
                'employee': self.employee_user.id,
                'date': self.future_date.isoformat(),
                'time': '10:00',
            },
        )

        self.assertRedirects(response, reverse('my_appointments'))
        self.assertEqual(Appointment.objects.count(), 1)
        appointment = Appointment.objects.first()
        self.assertEqual(appointment.client, self.client_user)
        self.assertEqual(appointment.status, 'new')

    def test_appointment_conflict_is_blocked(self):
        Appointment.objects.create(
            client=self.client_user,
            employee=self.employee_user,
            service=self.service,
            date=self.future_date,
            time='10:00',
            status='new',
        )
        self.client.force_login(self.second_client)

        response = self.client.post(
            reverse('create_appointment'),
            data={
                'service': self.service.id,
                'employee': self.employee_user.id,
                'date': self.future_date.isoformat(),
                'time': '10:00',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ten termin jest już zajęty dla wybranego fryzjera.')
        self.assertEqual(Appointment.objects.count(), 1)

    def test_client_can_cancel_upcoming_appointment(self):
        appointment = Appointment.objects.create(
            client=self.client_user,
            employee=self.employee_user,
            service=self.service,
            date=self.future_date,
            time='11:00',
            status='new',
        )
        self.client.force_login(self.client_user)

        response = self.client.post(reverse('cancel_appointment', args=[appointment.id]))

        self.assertRedirects(response, reverse('my_appointments'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'cancelled')

    def test_employee_panel_requires_employee_role(self):
        self.client.force_login(self.client_user)
        response = self.client.get(reverse('employee_appointments'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_employee_can_create_appointment_for_client(self):
        self.client.force_login(self.employee_user)
        response = self.client.post(
            reverse('employee_create_appointment'),
            data={
                'client': self.client_user.id,
                'service': self.service.id,
                'employee': self.employee_user.id,
                'date': self.future_date.isoformat(),
                'time': '12:00',
                'status': 'confirmed',
            },
        )

        self.assertRedirects(response, reverse('employee_appointments'))
        appointment = Appointment.objects.get(time='12:00')
        self.assertEqual(appointment.client, self.client_user)
        self.assertEqual(appointment.status, 'confirmed')

    def test_employee_can_update_status(self):
        appointment = Appointment.objects.create(
            client=self.client_user,
            employee=self.employee_user,
            service=self.service,
            date=self.future_date,
            time='13:00',
            status='new',
        )
        self.client.force_login(self.employee_user)

        response = self.client.post(
            reverse('employee_update_status', args=[appointment.id]),
            data={'status': 'completed'},
        )

        self.assertRedirects(response, reverse('employee_appointments'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'completed')
