from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Appointment, Notification


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'name', 'role', 'is_staff']
    list_filter = ['role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('معلومات إضافية', {'fields': ('role', 'name')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('معلومات إضافية', {'fields': ('role', 'name')}),
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'day', 'start_time', 'end_time', 'duration_label', 'status', 'created_at']
    list_filter = ['status', 'day']
    search_fields = ['employee__name', 'reason']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'message', 'read', 'created_at']
    list_filter = ['type', 'read']
