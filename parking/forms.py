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
    ParkingSession,
    Payment,
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
        fields = ['plate_number', 'owner_name', 'type', 'color']

        labels = {
            'plate_number': 'شماره پلاک',
            'owner_name': 'نام مالک',
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

class ParkingSessionEntryForm(forms.Form):
    plate_number = forms.CharField(
        label='شماره پلاک',
        max_length=15,
        help_text='برای خودرو: 12ب345-67 ، برای موتور: 8 رقم'
    )

    owner_name = forms.CharField(
        label='نام مالک',
        max_length=100,
        required=False
    )

    vehicle_type = forms.ChoiceField(
        label='نوع وسیله',
        choices=Vehicle.VEHICLE_TYPE_CHOICES
    )

    color = forms.CharField(
        label='رنگ',
        max_length=30,
        required=False
    )

    spot = forms.ModelChoiceField(
        label='جایگاه پارک',
        queryset=ParkingSpot.objects.none(),
        empty_label='انتخاب جایگاه آزاد'
    )

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

        if self.customer:
            self.fields['spot'].queryset = ParkingSpot.objects.filter(
                parking_lot__customer=self.customer,
                is_occupied=False
            ).select_related('parking_lot').order_by(
                'parking_lot__name',
                'level',
                'code'
            )

    def clean(self):
        cleaned_data = super().clean()

        plate_number = cleaned_data.get('plate_number')
        vehicle_type = cleaned_data.get('vehicle_type')
        spot = cleaned_data.get('spot')

        if self.customer and vehicle_type:
            active_tariff_exists = Tariff.objects.filter(
                customer=self.customer,
                vehicle_type=vehicle_type,
                is_active=True
            ).exists()

            if not active_tariff_exists:
                self.add_error(
                    'vehicle_type',
                    'برای این نوع وسیله نقلیه تعرفه فعال ثبت نشده است.'
                )

        if self.customer and spot:
            if spot.parking_lot.customer != self.customer:
                self.add_error(
                    'spot',
                    'این جایگاه مربوط به حساب شما نیست.'
                )

            if spot.is_occupied:
                self.add_error(
                    'spot',
                    'این جایگاه در حال حاضر اشغال است.'
                )

        if self.customer and plate_number and vehicle_type:
            temp_vehicle = Vehicle(
                customer=self.customer,
                plate_number=plate_number,
                type=vehicle_type
            )

            try:
                temp_vehicle.clean()
            except Exception as error:
                self.add_error('plate_number', error)

            existing_vehicle = Vehicle.objects.filter(
                customer=self.customer,
                plate_number=plate_number
            ).first()

            if existing_vehicle:
                open_session_exists = ParkingSession.objects.filter(
                    vehicle=existing_vehicle,
                    status=ParkingSession.SESSION_STATUS_OPEN
                ).exists()

                if open_session_exists:
                    self.add_error(
                        'plate_number',
                        'برای این وسیله نقلیه یک سشن باز وجود دارد.'
                    )

        return cleaned_data
    
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payment_method']

        labels = {
            'payment_method': 'روش پرداخت',
        }

    def clean_payment_method(self):
        payment_method = self.cleaned_data.get('payment_method')

        if not payment_method:
            raise forms.ValidationError('انتخاب روش پرداخت الزامی است.')

        return payment_method

class ReportFilterForm(forms.Form):
    start_date = forms.DateField(
        label='از تاریخ',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    end_date = forms.DateField(
        label='تا تاریخ',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    vehicle_type = forms.ChoiceField(
        label='نوع وسیله',
        required=False,
        choices=[('', 'همه انواع وسیله')] + list(Vehicle.VEHICLE_TYPE_CHOICES)
    )

    parking_lot = forms.ModelChoiceField(
        label='پارکینگ',
        required=False,
        queryset=ParkingLot.objects.none(),
        empty_label='همه پارکینگ‌ها'
    )

    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

        if customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(
                customer=customer
            ).order_by('name')


class CustomerUserCreateForm(forms.Form):
    username = forms.RegexField(
        label='نام کاربری',
        regex=r'^[A-Za-z0-9_]+$',
        max_length=150,
        error_messages={
            'invalid': 'نام کاربری فقط باید شامل حروف انگلیسی، عدد و _ باشد.'
        }
    )

    full_name = forms.CharField(
        label='نام کاربر',
        max_length=100,
        required=False
    )

    email = forms.EmailField(
        label='ایمیل',
        required=False
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

    role = forms.ChoiceField(
        label='نقش کاربر',
        choices=CustomerUser.ROLE_CHOICES,
        initial=CustomerUser.ROLE_OPERATOR
    )

    is_active = forms.BooleanField(
        label='فعال باشد؟',
        required=False,
        initial=True
    )

    def clean_username(self):
        username = self.cleaned_data['username']

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('این نام کاربری قبلاً ثبت شده است.')

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('این ایمیل قبلاً برای یک کاربر ثبت شده است.')

        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')

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


class CustomerUserUpdateForm(forms.ModelForm):
    full_name = forms.CharField(
        label='نام کاربر',
        max_length=100,
        required=False
    )

    email = forms.EmailField(
        label='ایمیل',
        required=False
    )

    class Meta:
        model = CustomerUser
        fields = ['role', 'is_active']

        labels = {
            'role': 'نقش کاربر',
            'is_active': 'فعال است؟',
        }

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)

        if self.user_instance:
            self.fields['full_name'].initial = self.user_instance.first_name
            self.fields['email'].initial = self.user_instance.email

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if email and self.user_instance:
            exists = User.objects.filter(
                email__iexact=email
            ).exclude(
                pk=self.user_instance.pk
            ).exists()

            if exists:
                raise forms.ValidationError('این ایمیل قبلاً برای یک کاربر دیگر ثبت شده است.')

        return email

# Advanced filter forms

class ParkingLotFilterForm(forms.Form):
    name = forms.CharField(
        label='نام پارکینگ',
        required=False
    )

    min_capacity = forms.IntegerField(
        label='حداقل ظرفیت',
        required=False
    )

    max_capacity = forms.IntegerField(
        label='حداکثر ظرفیت',
        required=False
    )


class ParkingSpotFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'همه وضعیت‌ها'),
        ('free', 'آزاد'),
        ('occupied', 'اشغال'),
    ]

    parking_lot = forms.ModelChoiceField(
        label='پارکینگ',
        required=False,
        queryset=ParkingLot.objects.none(),
        empty_label='همه پارکینگ‌ها'
    )

    code = forms.CharField(
        label='کد جایگاه',
        required=False
    )

    level = forms.CharField(
        label='طبقه',
        required=False
    )

    status = forms.ChoiceField(
        label='وضعیت',
        required=False,
        choices=STATUS_CHOICES
    )

    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

        if customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(
                customer=customer
            ).order_by('name')


class TariffFilterForm(forms.Form):
    ACTIVE_CHOICES = [
        ('', 'همه'),
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
    ]

    name = forms.CharField(
        label='نام تعرفه',
        required=False
    )

    vehicle_type = forms.ChoiceField(
        label='نوع وسیله',
        required=False,
        choices=[('', 'همه انواع وسیله')] + list(Vehicle.VEHICLE_TYPE_CHOICES)
    )

    is_active = forms.ChoiceField(
        label='وضعیت فعال بودن',
        required=False,
        choices=ACTIVE_CHOICES
    )


class ParkingSessionFilterForm(forms.Form):
    plate_number = forms.CharField(
        label='شماره پلاک',
        required=False
    )

    owner_name = forms.CharField(
        label='نام مالک',
        required=False
    )

    vehicle_type = forms.ChoiceField(
        label='نوع وسیله',
        required=False,
        choices=[('', 'همه انواع وسیله')] + list(Vehicle.VEHICLE_TYPE_CHOICES)
    )

    parking_lot = forms.ModelChoiceField(
        label='پارکینگ',
        required=False,
        queryset=ParkingLot.objects.none(),
        empty_label='همه پارکینگ‌ها'
    )

    status = forms.ChoiceField(
        label='وضعیت سشن',
        required=False,
        choices=[('', 'همه وضعیت‌ها')] + list(ParkingSession.STATUS_CHOICES)
    )

    entry_from = forms.DateField(
        label='ورود از تاریخ',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    entry_to = forms.DateField(
        label='ورود تا تاریخ',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    exit_from = forms.DateField(
        label='خروج از تاریخ',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    exit_to = forms.DateField(
        label='خروج تا تاریخ',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

        if customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(
                customer=customer
            ).order_by('name')


class PaymentFilterForm(forms.Form):
    plate_number = forms.CharField(
        label='شماره پلاک',
        required=False
    )

    owner_name = forms.CharField(
        label='نام مالک',
        required=False
    )

    parking_lot = forms.ModelChoiceField(
        label='پارکینگ',
        required=False,
        queryset=ParkingLot.objects.none(),
        empty_label='همه پارکینگ‌ها'
    )

    payment_method = forms.ChoiceField(
        label='روش پرداخت',
        required=False,
        choices=[('', 'همه روش‌ها')] + list(Payment.PAYMENT_METHOD_CHOICES)
    )

    payment_status = forms.ChoiceField(
        label='وضعیت پرداخت',
        required=False,
        choices=[('', 'همه وضعیت‌ها')] + list(Payment.PAYMENT_STATUS_CHOICES)
    )

    payment_from = forms.DateField(
        label='پرداخت از تاریخ',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    payment_to = forms.DateField(
        label='پرداخت تا تاریخ',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    min_amount = forms.DecimalField(
        label='حداقل مبلغ',
        required=False
    )

    max_amount = forms.DecimalField(
        label='حداکثر مبلغ',
        required=False
    )

    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

        if customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(
                customer=customer
            ).order_by('name')


class ReceiptFilterForm(forms.Form):
    receipt_number = forms.CharField(
        label='شماره رسید',
        required=False
    )

    plate_number = forms.CharField(
        label='شماره پلاک',
        required=False
    )

    owner_name = forms.CharField(
        label='نام مالک',
        required=False
    )

    parking_lot = forms.ModelChoiceField(
        label='پارکینگ',
        required=False,
        queryset=ParkingLot.objects.none(),
        empty_label='همه پارکینگ‌ها'
    )

    payment_method = forms.ChoiceField(
        label='روش پرداخت',
        required=False,
        choices=[('', 'همه روش‌ها')] + list(Payment.PAYMENT_METHOD_CHOICES)
    )

    issue_from = forms.DateField(
        label='صدور از تاریخ',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    issue_to = forms.DateField(
        label='صدور تا تاریخ',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

        if customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(
                customer=customer
            ).order_by('name')


class CustomerUserFilterForm(forms.Form):
    ACTIVE_CHOICES = [
        ('', 'همه'),
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
    ]

    username = forms.CharField(
        label='نام کاربری',
        required=False
    )

    full_name = forms.CharField(
        label='نام کاربر',
        required=False
    )

    email = forms.CharField(
        label='ایمیل',
        required=False
    )

    role = forms.ChoiceField(
        label='نقش',
        required=False,
        choices=[('', 'همه نقش‌ها')] + list(CustomerUser.ROLE_CHOICES)
    )

    is_active = forms.ChoiceField(
        label='وضعیت',
        required=False,
        choices=ACTIVE_CHOICES
    )

class CustomerUserPasswordForm(forms.Form):
    password = forms.CharField(
        label='رمز عبور جدید',
        widget=forms.PasswordInput,
        min_length=8,
        help_text='رمز عبور باید حداقل ۸ کاراکتر، یک حرف بزرگ انگلیسی و یک عدد داشته باشد.'
    )

    password_confirm = forms.CharField(
        label='تکرار رمز عبور جدید',
        widget=forms.PasswordInput
    )

    def clean_password(self):
        password = self.cleaned_data.get('password')

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
    
class AccountPasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label='رمز عبور فعلی',
        widget=forms.PasswordInput
    )

    new_password = forms.CharField(
        label='رمز عبور جدید',
        widget=forms.PasswordInput,
        min_length=8,
        help_text='رمز عبور باید حداقل ۸ کاراکتر، یک حرف بزرگ انگلیسی و یک عدد داشته باشد.'
    )

    new_password_confirm = forms.CharField(
        label='تکرار رمز عبور جدید',
        widget=forms.PasswordInput
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')

        if not self.user.check_password(old_password):
            raise forms.ValidationError('رمز عبور فعلی اشتباه است.')

        return old_password

    def clean_new_password(self):
        new_password = self.cleaned_data.get('new_password')

        if not re.search(r'[A-Z]', new_password):
            raise forms.ValidationError('رمز عبور باید حداقل یک حرف بزرگ انگلیسی داشته باشد.')

        if not re.search(r'[0-9]', new_password):
            raise forms.ValidationError('رمز عبور باید حداقل یک عدد داشته باشد.')

        return new_password

    def clean(self):
        cleaned_data = super().clean()

        new_password = cleaned_data.get('new_password')
        new_password_confirm = cleaned_data.get('new_password_confirm')

        if new_password and new_password_confirm and new_password != new_password_confirm:
            raise forms.ValidationError('رمز عبور جدید و تکرار آن یکسان نیستند.')

        return cleaned_data   

class CustomerSettingsForm(forms.ModelForm):
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

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        if not phone:
            raise forms.ValidationError('وارد کردن شماره تماس الزامی است.')

        if not phone.isdigit():
            raise forms.ValidationError('شماره تماس فقط باید شامل عدد باشد.')

        if len(phone) != 11:
            raise forms.ValidationError('شماره تماس باید ۱۱ رقم باشد.')

        exists = Customer.objects.filter(
            phone=phone
        ).exclude(
            pk=self.instance.pk
        ).exists()

        if exists:
            raise forms.ValidationError('این شماره تماس قبلاً ثبت شده است.')

        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if not email:
            raise forms.ValidationError('وارد کردن ایمیل الزامی است.')

        customer_exists = Customer.objects.filter(
            email__iexact=email
        ).exclude(
            pk=self.instance.pk
        ).exists()

        if customer_exists:
            raise forms.ValidationError('این ایمیل قبلاً برای یک پارکینگ دیگر ثبت شده است.')

        user_exists = User.objects.filter(
            email__iexact=email
        ).exclude(
            customer_profile__customer=self.instance
        ).exists()

        if user_exists:
            raise forms.ValidationError('این ایمیل قبلاً برای یک کاربر دیگر ثبت شده است.')

        return email         