from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(required=True, max_length=20, label='Numer telefonu')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Użytkownik o tej nazwie już istnieje.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Konto z tym adresem e-mail już istnieje.')
        return email

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get('phone_number') or '').strip()
        if User.objects.filter(phone_number__iexact=phone_number).exists():
            raise forms.ValidationError('Konto z tym numerem telefonu już istnieje.')
        return phone_number


class AccountUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        labels = {
            'first_name': 'Imię',
            'last_name': 'Nazwisko',
            'email': 'E-mail',
            'phone_number': 'Numer telefonu',
        }

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Konto z tym adresem e-mail już istnieje.')
        return email

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get('phone_number') or '').strip()
        if User.objects.filter(phone_number__iexact=phone_number).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Konto z tym numerem telefonu już istnieje.')
        return phone_number