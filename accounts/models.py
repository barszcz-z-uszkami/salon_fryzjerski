from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('client', 'Klient'),
        ('employee', 'Pracownik salonu'),
    ]

    phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='client'
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class PortfolioImage(models.Model):
    title = models.CharField(max_length=120, blank=True)
    image = models.ImageField(upload_to='portfolio/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Zdjęcie portfolio'
        verbose_name_plural = 'Portfolio'

    def __str__(self):
        if self.title:
            return self.title
        return f'Portfolio #{self.pk}'