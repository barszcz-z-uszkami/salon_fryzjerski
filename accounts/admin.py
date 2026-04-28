from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import PortfolioImage, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')

    fieldsets = UserAdmin.fieldsets + (
        ('Dodatkowe informacje', {'fields': ('phone_number', 'role')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Dodatkowe informacje', {'fields': ('phone_number', 'role')}),
    )


@admin.register(PortfolioImage)
class PortfolioImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'created_at')
    search_fields = ('title',)
    readonly_fields = ('created_at',)