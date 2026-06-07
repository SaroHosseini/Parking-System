import re

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm

from .models import (
    Customer,
    CustomerUser,
    Vehicle,
    ParkingLot,
    ParkingSpot,
    Tariff,
)


class CustomerRequestForm(forms.ModelForm):
    username = forms.RegexField(
        label='نام کاربری',
        regex=r'^[A-Za-z0-9_]+$',
        max_length=150,
        error_messages={
            'invalid': 'نام کاربری فقط باید شامل حروف انگلیسی، عدد و _ باشد.'
        }
    )

    password = forms.CharField(
        label='رمز عبور',
        widget=forms.PasswordInput,
        min_length=8,
        help_text='رمز عبور باید حداقل ۸ کاراکتر، یک حرف بزرگ انگلیسی و یک عدد داشته باشد.'
    )

    password_confirm = forms.CharField(
        label='تکرار رمز عبور',
        widget=forms.PasswordInput
    )

    class Meta:
        model = Customer
        fields = ['name', 'owner_name', 'phone', 'email', 'address']

        labels = {
            'name': 'نام پارکینگ / مجموعه',
            'owner_name': 'نام مالک یا مدیر',
            'phone': 'شماره تماس',
            'email': 'ایمیل',
            'address': 'آدرس پارکینگ',
        }

    def clean_username(self):
        username = self.cleaned_data['username']

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('این نام کاربری قبلاً ثبت شده است.')

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if not email:
            raise forms.ValidationError('وارد کردن ایمیل الزامی است.')

        if Customer.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('این ایمیل قبلاً برای یک درخواست ثبت شده است.')

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('این ایمیل قبلاً برای یک کاربر ثبت شده است.')

        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        if not phone:
            raise forms.ValidationError('وارد کردن شماره تماس الزامی است.')

        if not phone.isdigit():
            raise forms.ValidationError('شماره تماس فقط باید شامل عدد باشد.')

        if len(phone) != 11:
            raise forms.ValidationError('شماره تماس باید ۱۱ رقم باشد.')

        if Customer.objects.filter(phone=phone).exists():
            raise forms.ValidationError('این شماره تماس قبلاً ثبت شده است.')

        return phone

    def clean_password(self):
        password = self.cleaned_data.get('password')

        if len(password) < 8:
            raise forms.ValidationError('رمز عبور باید حداقل ۸ کاراکتر باشد.')

        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('رمز عبور باید حداقل یک حرف بزرگ انگلیسی داشته باشد.')

        if not re.search(r'[0-9]', password):
            raise forms.ValidationError('رمز عبور باید حداقل یک عدد داشته باشد.')

        return password

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('رمز عبور و تکرار آن یکسان نیستند.')

        return cleaned_data

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['plate_number', 'owner_name', 'owner_phone', 'type', 'color']

        labels = {
            'plate_number': 'شماره پلاک',
            'owner_name': 'نام مالک',
            'owner_phone': 'شماره تماس مالک',
            'type': 'نوع وسیله',
            'color': 'رنگ',
        }

class ParkingLotForm(forms.ModelForm):
    class Meta:
        model = ParkingLot
        fields = ['name', 'total_capacity']

        labels = {
            'name': 'نام پارکینگ',
            'total_capacity': 'ظرفیت کل',
        }

class ParkingSpotForm(forms.ModelForm):
    class Meta:
        model = ParkingSpot
        fields = ['parking_lot', 'code', 'level']

        labels = {
            'parking_lot': 'پارکینگ',
            'code': 'کد جایگاه',
            'level': 'طبقه',
        }

    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

        if customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(
                customer=customer
            ).order_by('name')

class TariffForm(forms.ModelForm):
    class Meta:
        model = Tariff
        fields = [
            'name',
            'vehicle_type',
            'first_hour_price',
            'additional_hour_price',
            'daily_price',
            'is_active',
        ]

        labels = {
            'name': 'نام تعرفه',
            'vehicle_type': 'نوع وسیله نقلیه',
            'first_hour_price': 'هزینه ساعت اول',
            'additional_hour_price': 'هزینه هر ساعت بعدی',
            'daily_price': 'هزینه شبانه‌روزی',
            'is_active': 'فعال',
        }

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        vehicle_type = cleaned_data.get('vehicle_type')
        is_active = cleaned_data.get('is_active')

        if self.customer and vehicle_type and is_active:
            duplicate_active_tariff = Tariff.objects.filter(
                customer=self.customer,
                vehicle_type=vehicle_type,
                is_active=True,
            )

            if self.instance.pk:
                duplicate_active_tariff = duplicate_active_tariff.exclude(
                    pk=self.instance.pk
                )

            if duplicate_active_tariff.exists():
                raise forms.ValidationError(
                    'برای این نوع وسیله نقلیه، یک تعرفه فعال دیگر وجود دارد.'
                )

        return cleaned_data                    

class CustomerLoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if user.is_superuser or user.is_staff:
            raise forms.ValidationError(
                'ورود مدیر سیستم از این صفحه مجاز نیست.',
                code='admin_not_allowed'
            )

        try:
            profile = user.customer_profile
        except CustomerUser.DoesNotExist:
            raise forms.ValidationError(
                'برای این کاربر حساب مشتری تعریف نشده است.',
                code='customer_profile_not_found'
            )

        if not profile.is_active:
            raise forms.ValidationError(
                'حساب کاربری شما غیرفعال است.',
                code='customer_user_inactive'
            )

        if not profile.customer.is_active:
            raise forms.ValidationError(
                'درخواست شما هنوز توسط مدیر سیستم تأیید نشده است.',
                code='customer_not_approved'
            )