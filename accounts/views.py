from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from booking.models import Appointment
from .forms import AccountUpdateForm, RegisterForm
from .models import PortfolioImage


def landing_view(request):
    return render(request, 'accounts/landing.html')


def about_view(request):
    return render(request, 'accounts/about.html')


def portfolio_view(request):
    images = PortfolioImage.objects.all()
    return render(request, 'accounts/portfolio.html', {'images': images})


def contact_view(request):
    return render(request, 'accounts/contact.html')


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Konto zostało utworzone. Możesz się zalogować.')
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard_view(request):
    now = timezone.localtime()
    today = now.date()
    now_time = now.time()

    upcoming_appointments = Appointment.objects.none()
    cancelled_appointments = Appointment.objects.none()
    archived_appointments = Appointment.objects.none()

    if request.user.role == 'client':
        upcoming_appointments = Appointment.objects.filter(
            client=request.user,
        ).exclude(status='cancelled').filter(
            Q(date__gt=today) | Q(date=today, time__gte=now_time)
        ).order_by('date', 'time')

        cancelled_appointments = Appointment.objects.filter(
            client=request.user,
            status='cancelled',
        ).order_by('-date', '-time')

        archived_appointments = Appointment.objects.filter(
            client=request.user,
            date__lt=today,
        ).exclude(status='cancelled').order_by('-date', '-time')

    return render(
        request,
        'accounts/home.html',
        {
            'upcoming_appointments': upcoming_appointments,
            'cancelled_appointments': cancelled_appointments,
            'archived_appointments': archived_appointments,
        },
    )


@login_required
def account_update_view(request):
    if request.method == 'POST':
        form = AccountUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dane konta zostały zaktualizowane.')
            return redirect('dashboard')
    else:
        form = AccountUpdateForm(instance=request.user)

    return render(request, 'accounts/account_update.html', {'form': form})


@login_required
def account_delete_view(request):
    if request.method == 'POST':
        user = request.user
        user.delete()
        messages.success(request, 'Konto zostało usunięte.')
        return redirect('home')

    return render(request, 'accounts/account_delete.html')