from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta, time, date
from django.db.models import Q, Count, Sum
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
import requests

from .models import User, Appointment, Notification, Branch
from .forms import LoginForm, EmployeeForm, BranchForm


def login_view(request):
    """صفحة تسجيل الدخول"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                auth_login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'البريد الإلكتروني أو كلمة المرور غير صحيحة')
    else:
        form = LoginForm()

    return render(request, 'appointments/login.html', {'form': form})


def logout_view(request):
    """تسجيل الخروج"""
    auth_logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    """الصفحة الرئيسية حسب الدور"""
    if request.user.role == 'employee':
        return redirect('employee_calendar')
    elif request.user.role == 'secretary':
        return redirect('secretary_dashboard')
    elif request.user.role == 'executive':
        return redirect('executive_calendar')
    return redirect('login')


def _build_calendar_context(request, filter_status=None, show_pending=True, employee_filter=None):
    """بناء بيانات الكاليندر"""
    week_offset = int(request.GET.get('week', 0))
    today = timezone.now().date()
    days_since_saturday = (today.weekday() + 2) % 7
    week_start = today - timedelta(days=days_since_saturday) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    week_days = [week_start + timedelta(days=i) for i in range(7)]

    time_slots = []
    for h in range(8, 18):
        time_slots.append(f'{h:02d}:00')
        time_slots.append(f'{h:02d}:30')

    # Build appointments lookup: (day_str, time_slot) -> appointment
    all_appointments = Appointment.objects.filter(day__range=[week_start, week_end])
    if filter_status:
        all_appointments = all_appointments.filter(status=filter_status)
    elif not show_pending:
        all_appointments = all_appointments.exclude(status='pending')

    if employee_filter:
        all_appointments = all_appointments.filter(employee=employee_filter)

    # Build grid data
    grid_data = {}
    for day in week_days:
        day_str = day.strftime('%Y-%m-%d')
        grid_data[day_str] = {}
        for slot in time_slots:
            slot_h = int(slot[:2])
            slot_m = int(slot[3:])
            slot_minutes = slot_h * 60 + slot_m
            cell = {'type': 'free', 'appointment': None, 'is_start': False}

            for apt in all_appointments:
                if apt.day != day:
                    continue
                apt_start_h = apt.start_time.hour
                apt_start_m = apt.start_time.minute
                apt_end_h = apt.end_time.hour
                apt_end_m = apt.end_time.minute
                apt_start_min = apt_start_h * 60 + apt_start_m
                apt_end_min = apt_end_h * 60 + apt_end_m

                if slot_minutes >= apt_start_min and slot_minutes < apt_end_min:
                    cell['type'] = apt.status
                    cell['appointment'] = apt
                    cell['is_start'] = (slot_minutes == apt_start_min)
                    break

            grid_data[day_str][slot] = cell

    return {
        'week_days': week_days,
        'week_start': week_start,
        'week_end': week_end,
        'week_offset': week_offset,
        'time_slots': time_slots,
        'grid_data': grid_data,
        'today': today,
    }


# ============= الموظف =============

@login_required
def employee_calendar_view(request):
    """كاليندر الموظف"""
    if request.user.role != 'employee':
        return redirect('dashboard')

    context = _build_calendar_context(request, employee_filter=request.user)
    context['selected_day'] = request.GET.get('day', '')
    context['selected_time'] = request.GET.get('time', '')
    return render(request, 'appointments/employee_calendar.html', context)


@login_required
def create_appointment_view(request):
    """إنشاء طلب حجز"""
    if request.user.role != 'employee' or request.method != 'POST':
        return redirect('employee_calendar')

    day_str = request.POST.get('day', '')
    start_time_str = request.POST.get('start_time', '09:00')
    duration = int(request.POST.get('duration', 60))
    reason = request.POST.get('reason', '').strip()
    notes = request.POST.get('notes', '').strip()

    if not reason:
        messages.error(request, 'يرجى إدخال سبب الحجز')
        return redirect('employee_calendar')

    try:
        day = date.fromisoformat(day_str)
    except (ValueError, TypeError):
        messages.error(request, 'تاريخ غير صالح')
        return redirect('employee_calendar')

    # Parse time
    h, m = map(int, start_time_str.split(':'))
    start_time = time(h, m)

    # Create appointment
    appointment = Appointment(
        employee=request.user,
        day=day,
        start_time=start_time,
        duration=duration,
        reason=reason,
        notes=notes or None,
        status='pending',
    )

    # Check conflict
    if appointment.has_conflict():
        messages.error(request, 'هذا الوقت متعارض مع موعد آخر محجوز')
        return redirect(f'/employee/calendar/?day={day_str}&time={start_time_str}')

    appointment.save()

    # Notify secretaries
    for sec in User.objects.filter(role='secretary'):
        Notification.objects.create(
            user=sec,
            type='new_request',
            message=f'طلب جديد من {request.user.name} - {appointment.reason}',
            appointment=appointment
        )

    messages.success(request, 'تم إرسال طلبك للسكرتارية بنجاح')
    return redirect('employee_calendar')


@login_required
def employee_requests_view(request):
    """طلبات الموظف"""
    if request.user.role != 'employee':
        return redirect('dashboard')

    status_filter = request.GET.get('status', 'all')
    my_appointments = Appointment.objects.filter(employee=request.user)

    if status_filter in ['pending', 'approved', 'rejected']:
        my_appointments = my_appointments.filter(status=status_filter)

    context = {
        'appointments': my_appointments.order_by('-created_at'),
        'status_filter': status_filter,
        'counts': {
            'all': Appointment.objects.filter(employee=request.user).count(),
            'pending': Appointment.objects.filter(employee=request.user, status='pending').count(),
            'approved': Appointment.objects.filter(employee=request.user, status='approved').count(),
            'rejected': Appointment.objects.filter(employee=request.user, status='rejected').count(),
        },
    }
    return render(request, 'appointments/employee_requests.html', context)


# ============= السكرتارية =============

@login_required
def secretary_dashboard_view(request):
    """لوحة السكرتارية"""
    if request.user.role != 'secretary':
        return redirect('dashboard')

    status_filter = request.GET.get('status', 'all')
    appointments_list = Appointment.objects.all()

    if status_filter in ['pending', 'approved', 'rejected']:
        appointments_list = appointments_list.filter(status=status_filter)

    context = {
        'appointments': appointments_list.order_by('-created_at'),
        'status_filter': status_filter,
        'stats': {
            'pending': Appointment.objects.filter(status='pending').count(),
            'approved': Appointment.objects.filter(status='approved').count(),
            'rejected': Appointment.objects.filter(status='rejected').count(),
        },
    }
    return render(request, 'appointments/secretary_dashboard.html', context)


def _send_approval_email(appointment):
    """إرسال إيميل موافقة"""
    if not appointment.employee.email:
        return False
    subject = 'تمت الموافقة على طلب موعدك'
    message = (
        f'مرحباً {appointment.employee.name}،\n\n'
        f'تمت الموافقة على طلبك:\n'
        f'التاريخ: {appointment.day}\n'
        f'الوقت: {appointment.start_time.strftime("%H:%M")} - {appointment.end_time.strftime("%H:%M")}\n'
        f'المدة: {appointment.duration_label}\n'
        f'السبب: {appointment.reason}\n\n'
        f'مع تحيات،\nنظام حجز المواعيد'
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [appointment.employee.email])
        return True
    except Exception:
        return False


def _send_whatsapp_message(appointment):
    """إرسال رسالة واتساب عند الموافقة"""
    phone = appointment.employee.phone_number
    if not phone:
        return None
    message = (
        f'مرحباً {appointment.employee.name}، تمت الموافقة على طلبك ✅\n'
        f'التاريخ: {appointment.day}\n'
        f'الوقت: {appointment.start_time.strftime("%H:%M")} - {appointment.end_time.strftime("%H:%M")}\n'
        f'السبب: {appointment.reason}'
    )
    # Try CallMeBot if API key is configured
    api_key = getattr(settings, 'WHATSAPP_API_KEY', None)
    if api_key:
        try:
            url = 'https://api.callmebot.com/whatsapp.php'
            payload = {'phone': phone, 'text': message, 'apikey': api_key}
            resp = requests.get(url, params=payload, timeout=10)
            if resp.status_code == 200:
                return 'sent'
        except Exception:
            pass
    # Fallback: return wa.me link
    import urllib.parse
    encoded_msg = urllib.parse.quote(message)
    return f'https://wa.me/{phone}?text={encoded_msg}'


@login_required
def approve_appointment_view(request, pk):
    """الموافقة على طلب"""
    if request.user.role != 'secretary':
        return redirect('dashboard')

    appointment = get_object_or_404(Appointment, pk=pk)
    if appointment.status != 'pending':
        return redirect('secretary_dashboard')

    if appointment.has_conflict():
        messages.error(request, 'لا يمكن الموافقة: يوجد تعارض مع موعد آخر محجوز')
        return redirect('secretary_dashboard')

    appointment.status = 'approved'
    appointment.save()

    # Notify employee
    Notification.objects.create(
        user=appointment.employee,
        type='approved',
        message=f'تمت الموافقة على طلبك: {appointment.reason}',
        appointment=appointment
    )

    # Notify executives
    for exec in User.objects.filter(role='executive'):
        Notification.objects.create(
            user=exec,
            type='new_request',
            message=f'موعد جديد: {appointment.employee.name} - {appointment.reason}',
            appointment=appointment
        )

    # Send email
    email_sent = _send_approval_email(appointment)

    # Send WhatsApp
    wa_result = _send_whatsapp_message(appointment)

    if email_sent:
        messages.success(request, 'تمت الموافقة على الطلب وتم إرسال إشعار بالبريد الإلكتروني')
    else:
        messages.success(request, 'تمت الموافقة على الطلب')

    if wa_result == 'sent':
        messages.success(request, 'تم إرسال رسالة واتساب للموظف')
    elif wa_result and wa_result.startswith('https://wa.me/'):
        messages.info(request, 'تم قبول الموعد. اضغط على زر إرسال واتساب في صفحة التفاصيل لإرسال الرسالة.')
        request.session['wa_link'] = wa_result

    return redirect('secretary_dashboard')


@login_required
def reject_appointment_view(request, pk):
    """رفض طلب"""
    if request.user.role != 'secretary':
        return redirect('dashboard')

    appointment = get_object_or_404(Appointment, pk=pk)
    if appointment.status != 'pending':
        return redirect('secretary_dashboard')

    appointment.status = 'rejected'
    appointment.save()

    Notification.objects.create(
        user=appointment.employee,
        type='rejected',
        message=f'تم رفض طلبك: {appointment.reason}',
        appointment=appointment
    )

    messages.success(request, 'تم رفض الطلب')
    return redirect('secretary_dashboard')


# ============= المدير التنفيذي =============

@login_required
def executive_calendar_view(request):
    """جدول المدير التنفيذي"""
    if request.user.role != 'executive':
        return redirect('dashboard')

    context = _build_calendar_context(request, filter_status='approved')
    return render(request, 'appointments/executive_calendar.html', context)


# ============= تفاصيل الحجز =============

@login_required
def appointment_detail_view(request, pk):
    """صفحة تفاصيل الحجز"""
    appointment = get_object_or_404(Appointment, pk=pk)
    # Permissions: employee sees own, secretary/executive sees all
    if request.user.role == 'employee' and appointment.employee != request.user:
        messages.error(request, 'ليس لديك صلاحية لعرض هذا الحجز')
        return redirect('dashboard')

    wa_link = request.session.pop('wa_link', None)
    context = {
        'appointment': appointment,
        'wa_link': wa_link,
    }
    return render(request, 'appointments/appointment_detail.html', context)


# ============= الإشعارات =============

@login_required
def notifications_view(request):
    """جلب الإشعارات (API)"""
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    data = [{
        'id': n.id,
        'message': n.message,
        'type': n.type,
        'read': n.read,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
    } for n in notifs]
    return JsonResponse({
        'notifications': data,
        'unread_count': Notification.objects.filter(user=request.user, read=False).count()
    })


@login_required
def notifications_page_view(request):
    """صفحة عرض الإشعارات"""
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = notifs.filter(read=False).count()

    # Filter by read status
    read_filter = request.GET.get('read', 'all')
    if read_filter == 'unread':
        notifs = notifs.filter(read=False)
    elif read_filter == 'read':
        notifs = notifs.filter(read=True)

    # Pagination
    paginator = Paginator(notifs, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'appointments/notifications_page.html', {
        'page_obj': page_obj,
        'unread_count': unread_count,
        'read_filter': read_filter,
    })


@login_required
def mark_notification_read_view(request, pk):
    """تعليم إشعار كمقروء"""
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.read = True
    notif.save()
    return JsonResponse({'success': True})


@login_required
def mark_all_notifications_read_view(request):
    """تعليم كل الإشعارات كمقروءة"""
    Notification.objects.filter(user=request.user, read=False).update(read=True)
    return JsonResponse({'success': True})


# ============= الموظفين =============

@login_required
def employees_view(request):
    """صفحة الموظفين"""
    if request.user.role not in ('secretary', 'executive'):
        messages.error(request, 'ليس لديك صلاحية')
        return redirect('dashboard')

    employees = User.objects.filter(role='employee').annotate(
        total_appointments=Count('appointments'),
        approved_appointments=Count('appointments', filter=Q(appointments__status='approved')),
        total_duration=Sum('appointments__duration', filter=Q(appointments__status='approved')),
    )

    # Filter by branch
    branch_filter = request.GET.get('branch', '')
    if branch_filter:
        employees = employees.filter(branch_id=branch_filter)

    # Search by name
    search = request.GET.get('search', '').strip()
    if search:
        employees = employees.filter(
            Q(name__icontains=search) | Q(username__icontains=search)
        )

    # Pagination
    paginator = Paginator(employees.order_by('-id'), 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    branches = Branch.objects.all()

    return render(request, 'appointments/employees.html', {
        'page_obj': page_obj,
        'branches': branches,
        'branch_filter': branch_filter,
        'search': search,
    })


# ============= التقارير =============

@login_required
def reports_view(request):
    """صفحة التقارير"""
    if request.user.role not in ('secretary', 'executive'):
        messages.error(request, 'ليس لديك صلاحية')
        return redirect('dashboard')

    # Top employees by appointment count
    top_by_count = User.objects.filter(role='employee').annotate(
        count=Count('appointments', filter=Q(appointments__status='approved'))
    ).order_by('-count')[:10]

    # Top employees by total duration
    top_by_duration = User.objects.filter(role='employee').annotate(
        total=Sum('appointments__duration', filter=Q(appointments__status='approved'))
    ).order_by('-total')[:10]

    # Monthly stats
    current_year = timezone.now().year
    monthly_stats = []
    for m in range(1, 13):
        month_appointments = Appointment.objects.filter(
            status='approved',
            day__year=current_year,
            day__month=m
        )
        monthly_stats.append({
            'month': m,
            'month_name': [
                'يناير', 'فبراير', 'مارس', 'إبريل', 'مايو', 'يونيو',
                'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
            ][m - 1],
            'count': month_appointments.count(),
            'duration': month_appointments.aggregate(total=Sum('duration'))['total'] or 0,
        })

    # Overall stats
    overall = {
        'total_appointments': Appointment.objects.filter(status='approved').count(),
        'total_pending': Appointment.objects.filter(status='pending').count(),
        'total_rejected': Appointment.objects.filter(status='rejected').count(),
        'total_duration': Appointment.objects.filter(status='approved').aggregate(total=Sum('duration'))['total'] or 0,
    }

    context = {
        'top_by_count': top_by_count,
        'top_by_duration': top_by_duration,
        'monthly_stats': monthly_stats,
        'overall': overall,
    }
    return render(request, 'appointments/reports.html', context)


# ============= الفروع =============

@login_required
def branches_view(request):
    """صفحة إدارة الفروع"""
    if request.user.role not in ('secretary', 'executive'):
        messages.error(request, 'ليس لديك صلاحية')
        return redirect('dashboard')

    branches = Branch.objects.annotate(employee_count=Count('employees'))
    return render(request, 'appointments/branches.html', {'branches': branches})


@login_required
def branch_create_view(request):
    """إضافة فرع جديد"""
    if request.user.role not in ('secretary', 'executive'):
        messages.error(request, 'ليس لديك صلاحية')
        return redirect('dashboard')

    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الفرع بنجاح')
            return redirect('branches')
    else:
        form = BranchForm()
    return render(request, 'appointments/branch_form.html', {'form': form, 'title': 'إضافة فرع جديد'})


@login_required
def branch_edit_view(request, pk):
    """تعديل فرع"""
    if request.user.role not in ('secretary', 'executive'):
        messages.error(request, 'ليس لديك صلاحية')
        return redirect('dashboard')

    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الفرع بنجاح')
            return redirect('branches')
    else:
        form = BranchForm(instance=branch)
    return render(request, 'appointments/branch_form.html', {'form': form, 'title': 'تعديل فرع', 'branch': branch})


@login_required
def branch_delete_view(request, pk):
    """حذف فرع"""
    if request.user.role not in ('secretary', 'executive'):
        messages.error(request, 'ليس لديك صلاحية')
        return redirect('dashboard')

    branch = get_object_or_404(Branch, pk=pk)
    branch.delete()
    messages.success(request, 'تم حذف الفرع بنجاح')
    return redirect('branches')


# ============= إضافة موظف =============

@login_required
def employee_create_view(request):
    """إضافة موظف جديد"""
    if request.user.role not in ('secretary', 'executive'):
        messages.error(request, 'ليس لديك صلاحية')
        return redirect('dashboard')

    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الموظف بنجاح')
            return redirect('employees')
    else:
        form = EmployeeForm()
    return render(request, 'appointments/employee_form.html', {'form': form})
