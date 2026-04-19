from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Appointment, User, Branch


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'أدخل البريد الإلكتروني',
            'class': 'form-input',
        }),
        label='البريد الإلكتروني',
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'أدخل كلمة المرور',
            'class': 'form-input',
        }),
        label='كلمة المرور',
    )


class AppointmentRequestForm(forms.ModelForm):
    TIME_CHOICES = []
    for h in range(8, 18):
        TIME_CHOICES.append((f'{h:02d}:00', f'{h:02d}:00'))
        TIME_CHOICES.append((f'{h:02d}:30', f'{h:02d}:30'))

    start_time = forms.ChoiceField(
        choices=TIME_CHOICES,
        label='من الساعة',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    duration = forms.ChoiceField(
        choices=[(30, 'نصف ساعة'), (60, 'ساعة'), (120, 'ساعتين')],
        label='المدة',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'اكتب سبب الحجز...',
            'class': 'form-textarea',
            'rows': 3,
        }),
        label='سبب الحجز',
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'أي ملاحظات إضافية...',
            'class': 'form-textarea',
            'rows': 2,
        }),
        label='ملاحظات إضافية',
        required=False,
    )

    class Meta:
        model = Appointment
        fields = ['day', 'start_time', 'duration', 'reason', 'notes']
        widgets = {
            'day': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        }


class EmployeeForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'كلمة المرور'}),
        label='كلمة المرور'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'تأكيد كلمة المرور'}),
        label='تأكيد كلمة المرور'
    )

    class Meta:
        model = User
        fields = ['username', 'password', 'name', 'phone_number', 'email', 'branch']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'اسم المستخدم'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'الاسم الكامل'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'مثال: 20100xxxxxxx'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'البريد الإلكتروني'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'كلمتا المرور غير متطابقتين')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'employee'
        if commit:
            user.save()
        return user


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['name', 'address', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'اسم الفرع'}),
            'address': forms.Textarea(attrs={'class': 'form-textarea', 'placeholder': 'عنوان الفرع', 'rows': 2}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'رقم هاتف الفرع'}),
        }
