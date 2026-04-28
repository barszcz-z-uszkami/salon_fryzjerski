from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    about_view,
    account_delete_view,
    account_update_view,
    contact_view,
    dashboard_view,
    landing_view,
    portfolio_view,
    register_view,
)

urlpatterns = [
    path('', landing_view, name='home'),
    path('o-nas/', about_view, name='about'),
    path('portfolio/', portfolio_view, name='portfolio'),
    path('kontakt/', contact_view, name='contact'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('account/update/', account_update_view, name='account_update'),
    path('account/delete/', account_delete_view, name='account_delete'),
    path('register/', register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path(
        'password-change/',
        auth_views.PasswordChangeView.as_view(template_name='accounts/password_change.html'),
        name='password_change',
    ),
    path(
        'password-change/done/',
        auth_views.PasswordChangeDoneView.as_view(template_name='accounts/password_change_done.html'),
        name='password_change_done',
    ),
]