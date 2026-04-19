from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Branch(models.Model):
    name = models.CharField(max_length=100, verbose_name='اسم الفرع')
    address = models.TextField(blank=True, null=True, verbose_name='العنوان')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='رقم الهاتف')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'فرع'
        verbose_name_plural = 'الفروع'
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = [
        ('employee', 'موظف'),
        ('secretary', 'سكرتارية'),
        ('executive', 'مدير تنفيذي'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee', verbose_name='الدور')
    name = models.CharField(max_length=100, verbose_name='الاسم', blank=True)
    phone_number = models.CharField(max_length=20, verbose_name='رقم الهاتف', blank=True, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees', verbose_name='الفرع')

    class Meta:
        verbose_name = 'مستخدم'
        verbose_name_plural = 'المستخدمون'

    def __str__(self):
        return self.name or self.username


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('approved', 'تمت الموافقة'),
        ('rejected', 'تم الرفض'),
    ]
    DURATION_CHOICES = [
        (30, 'نصف ساعة'),
        (60, 'ساعة'),
        (120, 'ساعتين'),
    ]

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments', verbose_name='الموظف', limit_choices_to={'role': 'employee'})
    day = models.DateField(verbose_name='اليوم')
    start_time = models.TimeField(verbose_name='من الساعة')
    duration = models.IntegerField(choices=DURATION_CHOICES, default=60, verbose_name='المدة')
    reason = models.TextField(verbose_name='سبب الحجز')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات إضافية')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='الحالة')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'موعد'
        verbose_name_plural = 'المواعيد'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.name} - {self.day} {self.start_time}"

    @property
    def end_time(self):
        from datetime import datetime, timedelta
        dt = datetime.combine(self.day, self.start_time)
        end = dt + timedelta(minutes=self.duration)
        return end.time()

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES)[self.status]

    @property
    def duration_label(self):
        return dict(self.DURATION_CHOICES)[self.duration]

    def has_conflict(self):
        """التحقق من وجود تعارض مع مواعيد أخرى (موافق عليها فقط)"""
        from datetime import datetime, timedelta
        start_dt = datetime.combine(self.day, self.start_time)
        end_dt = start_dt + timedelta(minutes=self.duration)

        conflicts = Appointment.objects.filter(
            day=self.day,
            status='approved'
        ).exclude(pk=self.pk)

        for apt in conflicts:
            apt_start = datetime.combine(apt.day, apt.start_time)
            apt_end = apt_start + timedelta(minutes=apt.duration)
            if start_dt < apt_end and end_dt > apt_start:
                return True
        return False


class Notification(models.Model):
    TYPE_CHOICES = [
        ('new_request', 'طلب جديد'),
        ('approved', 'موافقة'),
        ('rejected', 'رفض'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='المستخدم')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='النوع')
    message = models.TextField(verbose_name='الرسالة')
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='notifications', verbose_name='الموعد')
    read = models.BooleanField(default=False, verbose_name='مقروء')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'إشعار'
        verbose_name_plural = 'الإشعارات'
        ordering = ['-created_at']

    def __str__(self):
        return self.message[:50]
