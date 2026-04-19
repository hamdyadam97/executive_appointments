from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Employee
    path('employee/calendar/', views.employee_calendar_view, name='employee_calendar'),
    path('employee/request/', views.create_appointment_view, name='create_appointment'),
    path('employee/requests/', views.employee_requests_view, name='employee_requests'),

    # Secretary
    path('secretary/', views.secretary_dashboard_view, name='secretary_dashboard'),
    path('secretary/approve/<int:pk>/', views.approve_appointment_view, name='approve_appointment'),
    path('secretary/reject/<int:pk>/', views.reject_appointment_view, name='reject_appointment'),

    # Executive
    path('executive/', views.executive_calendar_view, name='executive_calendar'),

    # Appointment Detail
    path('appointment/<int:pk>/', views.appointment_detail_view, name='appointment_detail'),

    # Notifications
    path('notifications/', views.notifications_page_view, name='notifications_page'),

    # Employees
    path('employees/', views.employees_view, name='employees'),
    path('employees/add/', views.employee_create_view, name='employee_create'),

    # Branches
    path('branches/', views.branches_view, name='branches'),
    path('branches/add/', views.branch_create_view, name='branch_create'),
    path('branches/edit/<int:pk>/', views.branch_edit_view, name='branch_edit'),
    path('branches/delete/<int:pk>/', views.branch_delete_view, name='branch_delete'),

    # Reports
    path('reports/', views.reports_view, name='reports'),

    # Notifications API
    path('api/notifications/', views.notifications_view, name='notifications'),
    path('api/notifications/<int:pk>/read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read_view, name='mark_all_read'),
]
