from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, time, timedelta
from appointments.models import User, Appointment, Notification


class Command(BaseCommand):
    help = 'Create demo users and sample appointments'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            # Create users
            users_data = [
                {'username': 'employee', 'name': 'أحمد محمد', 'role': 'employee', 'password': 'password'},
                {'username': 'secretary', 'name': 'سارة أحمد', 'role': 'secretary', 'password': 'password'},
                {'username': 'executive', 'name': 'المهندس خالد', 'role': 'executive', 'password': 'password'},
            ]

            created_users = {}
            for data in users_data:
                user, created = User.objects.get_or_create(
                    username=data['username'],
                    defaults={'name': data['name'], 'role': data['role']}
                )
                if created or not user.has_usable_password():
                    user.set_password(data['password'])
                    user.save()
                    status = 'Created'
                else:
                    status = 'Exists'
                created_users[data['role']] = user
                self.stdout.write(f"  {status}: {user.name} ({user.username})")

            employee = created_users['employee']
            secretary = created_users['secretary']

            # Create sample appointments
            today = date.today()
            appointments_data = [
                {'day': today, 'start_time': time(10, 0), 'duration': 60, 'reason': 'اجتماع أسبوعي لمناقشة المشاريع', 'status': 'approved'},
                {'day': today, 'start_time': time(13, 0), 'duration': 30, 'reason': 'مراجعة تقرير المبيعات', 'status': 'pending'},
                {'day': today + timedelta(days=1), 'start_time': time(9, 30), 'duration': 60, 'reason': 'مقابلة مع مورد جديد', 'status': 'pending'},
                {'day': today + timedelta(days=2), 'start_time': time(11, 0), 'duration': 120, 'reason': 'اجتماع مع فريق التطوير', 'status': 'approved'},
                {'day': today + timedelta(days=3), 'start_time': time(14, 30), 'duration': 60, 'reason': 'مراجعة الميزانية الشهرية', 'status': 'pending'},
            ]

            for data in appointments_data:
                apt, created = Appointment.objects.get_or_create(
                    employee=employee,
                    day=data['day'],
                    start_time=data['start_time'],
                    defaults={
                        'duration': data['duration'],
                        'reason': data['reason'],
                        'status': data['status'],
                    }
                )
                if created:
                    self.stdout.write(f"  Created appointment: {apt}")

            self.stdout.write(self.style.SUCCESS('\nDemo data created successfully!'))
            self.stdout.write('\nLogin credentials:')
            self.stdout.write('  employee / password')
            self.stdout.write('  secretary / password')
            self.stdout.write('  executive / password')
