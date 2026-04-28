from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class AccountsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            role='client',
            email='test@example.com',
        )

    def test_register_page_is_available(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_password_change_requires_login(self):
        response = self.client.get(reverse('password_change'))
        self.assertRedirects(response, '/login/?next=/password-change/')

    def test_logged_user_can_open_password_change_page(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('password_change'))
        self.assertEqual(response.status_code, 200)
