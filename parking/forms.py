import re

import jdatetime

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Exists, OuterRef

from .models import (
    Customer,
    CustomerUser,
    Vehicle,
    ParkingLot,
    ParkingSpot,
    Tariff,
    ParkingSession,
    Payment,
    BugReport,
)


PERSIAN_DATE_ERROR = 'تاریخ را به صورت شمسی و با فرمت ۱۴۰۵/۰۳/۱۸ وارد کنید.'
USERNAME_PATTERN = r'^[A-Za-z0-9]+$'
USERNAME_HELP_TEXT = 'فقط حروف و اعداد انگلیسی، حداکثر ۶۰ کاراکتر.'
USERNAME_ERROR_MESSAGES = {
    'required': 'نام کاربری را وارد کنید.',
    'invalid': 'نام کاربری را فقط با حروف و اعداد انگلیسی وارد کنید.',
    'max_length': 'نام کاربری نمی‌تواند بیشتر از ۶۰ کاراکتر باشد.',
}
PERSIAN_NAME_PATTERN = r'^[آابپتثجچحخدذرزژسشصضطظعغفقکكگلمنوهیيىۀةئؤء\s‌]+$'
PERSIAN_NAME_HELP_TEXT = 'فقط حروف فارسی، حداکثر ۵۰ کاراکتر.'
VEHICLE_COLOR_CHOICES = [
    ('', 'انتخاب رنگ'),
    ('سفید', 'سفید'),
    ('مشکی', 'مشکی'),
    ('نقره‌ای', 'نقره‌ای'),
    ('خاکستری', 'خاکستری'),
    ('قرمز', 'قرمز'),
    ('آبی', 'آبی'),
    ('سبز', 'سبز'),
    ('زرد', 'زرد'),
    ('نارنجی', 'نارنجی'),
    ('قهوه‌ای', 'قهوه‌ای'),
    ('کرم', 'کرم'),
    ('سایر', 'سایر'),
]
PERSIAN_DIGIT_TRANSLATION = str.maketrans(
    '۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩',
    '01234567890123456789',
)


forms.Field.default_error_messages.update({
    'required': 'این فیلد را تکمیل کنید.',
})
forms.CharField.default_error_messages.update({
    'required': 'این فیلد را تکمیل کنید.',
    'max_length': 'طول متن از حد مجاز بیشتر است.',
    'min_length': 'طول متن از حد مجاز کمتر است.',
})
forms.ChoiceField.default_error_messages.update({
    'required': 'یک گزینه انتخاب کنید.',
    'invalid_choice': 'گزینه انتخاب‌شده معتبر نیست.',
})
forms.ModelChoiceField.default_error_messages.update({
    'required': 'یک گزینه انتخاب کنید.',
    'invalid_choice': 'گزینه انتخاب‌شده معتبر نیست.',
})
forms.IntegerField.default_error_messages.update({
    'required': 'این فیلد را تکمیل کنید.',
    'invalid': 'عدد معتبر وارد کنید.',
    'min_value': 'مقدار واردشده کمتر از حد مجاز است.',
    'max_value': 'مقدار واردشده بیشتر از حد مجاز است.',
})
forms.DecimalField.default_error_messages.update({
    'required': 'این مبلغ را وارد کنید.',
    'invalid': 'مبلغ را به صورت عددی وارد کنید.',
    'max_digits': 'تعداد رقم‌های مبلغ از حد مجاز بیشتر است.',
    'max_decimal_places': 'تعداد رقم‌های اعشار از حد مجاز بیشتر است.',
    'max_whole_digits': 'تعداد رقم‌های مبلغ از حد مجاز بیشتر است.',
})
forms.EmailField.default_error_messages.update({
    'required': 'ایمیل را وارد کنید.',
    'invalid': 'ایمیل معتبر وارد کنید.',
})


def normalize_digits(value):
    return str(value).translate(PERSIAN_DIGIT_TRANSLATION)


def clean_persian_name(value, field_label):
    value = (value or '').strip()

    if not value:
        raise forms.ValidationError(f'{field_label} را وارد کنید.')

    if len(value) > 50:
        raise forms.ValidationError(f'{field_label} نمی‌تواند بیشتر از ۵۰ کاراکتر باشد.')

    if not re.fullmatch(PERSIAN_NAME_PATTERN, value):
        raise forms.ValidationError(f'{field_label} را فقط با حروف فارسی وارد کنید.')

    return value


class JalaliDateField(forms.CharField):
    default_error_messages = {
        'invalid': PERSIAN_DATE_ERROR,
    }

    def __init__(self, *args, **kwargs):
        attrs = {
            'inputmode': 'numeric',
            'placeholder': '۱۴۰۵/۰۳/۱۸',
            'autocomplete': 'off',
            'dir': 'ltr',
            'class': 'jalali-date-input',
            'readonly': 'readonly',
            'data-jalali-datepicker': 'true',
            'aria-haspopup': 'dialog',
        }
        widget = kwargs.pop('widget', forms.TextInput(attrs=attrs))
        super().__init__(*args, widget=widget, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)

        if value in self.empty_values:
            return None

        normalized = normalize_digits(value).strip().replace('-', '/').replace('.', '/')
        parts = normalized.split('/')

        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise forms.ValidationError(self.error_messages['invalid'], code='invalid')

        try:
            year, month, day = [int(part) for part in parts]
            return jdatetime.date(year, month, day).togregorian()
        except (ValueError, TypeError):
            raise forms.ValidationError(self.error_messages['invalid'], code='invalid')


class CustomerRequestForm(forms.ModelForm):
    username = forms.RegexField(
        label='نام کاربری',
        regex=USERNAME_PATTERN,
        max_length=60,
        help_text='example123',
        widget=forms.TextInput(attrs={
            'maxlength': '60',
            'autocomplete': 'username',
            'placeholder': 'example123',
        }),
        error_messages=USERNAME_ERROR_MESSAGES,
    )

    password = forms.CharField(
        label='رمز عبور',
        widget=forms.PasswordInput,
        min_length=8,
        help_text='حداقل ۸ کاراکتر، یک حرف بزرگ انگلیسی و یک عدد.',
        error_messages={
            'required': 'رمز عبور را وارد کنید.',
            'min_length': 'رمز عبور حداقل ۸ کاراکتر دارد.',
        }
    )

    password_confirm = forms.CharField(
        label='تکرار رمز عبور',
        widget=forms.PasswordInput,
        error_messages={'required': 'تکرار رمز عبور را وارد کنید.'}
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
        help_texts = {
            'name': PERSIAN_NAME_HELP_TEXT,
            'owner_name': PERSIAN_NAME_HELP_TEXT,
            'phone': '09120000000',
            'email': 'ایمیل فعال برای پیگیری درخواست.',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'maxlength': '50',
                'placeholder': 'پارکینگ آزادی',
            }),
            'owner_name': forms.TextInput(attrs={
                'maxlength': '50',
                'placeholder': 'محمد پسندیده',
            }),
            'phone': forms.TextInput(attrs={
                'maxlength': '11',
                'inputmode': 'numeric',
                'placeholder': '09120000000',
            }),
            'address': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'تهران، خیابان آزادی، پلاک ۱۲',
            }),
            'email': forms.EmailInput(attrs={
            'maxlength': '50',
            'placeholder': 'example@gmail.com',
            }),
        }
        error_messages = {
            'name': {
                'required': 'نام پارکینگ را وارد کنید.',
                'max_length': 'نام پارکینگ نمی‌تواند بیشتر از ۵۰ کاراکتر باشد.',
            },
            'owner_name': {
                'required': 'نام مالک یا مدیر را وارد کنید.',
                'max_length': 'نام مالک یا مدیر نمی‌تواند بیشتر از ۵۰ کاراکتر باشد.',
            },
            'email': {
                'required': 'ایمیل را وارد کنید.',
                'invalid': 'ایمیل وارد شده معتبر نیست.',
            },
            'phone': {
                'required': 'شماره تماس را وارد کنید.',
            },
            'address': {
                'required': 'آدرس پارکینگ را وارد کنید.',
            },
        }

    def clean_name(self):
        return clean_persian_name(self.cleaned_data.get('name'), 'نام پارکینگ')

    def clean_owner_name(self):
        return clean_persian_name(self.cleaned_data.get('owner_name'), 'نام مالک یا مدیر')

    def clean_username(self):
        username = self.cleaned_data.get('username')

        if not username:
            return username

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
            raise forms.ValidationError('شماره تماس را فقط با عدد وارد کنید.')

        if len(phone) != 11:
            raise forms.ValidationError('شماره تماس را ۱۱ رقمی وارد کنید.')

        if Customer.objects.filter(phone=phone).exists():
            raise forms.ValidationError('این شماره تماس قبلاً ثبت شده است.')

        return phone

    def clean_address(self):
        address = (self.cleaned_data.get('address') or '').strip()

        if not address:
            raise forms.ValidationError('آدرس پارکینگ را وارد کنید.')

        return address

    def clean_password(self):
        password = self.cleaned_data.get('password')

        if not password:
            return password

        if len(password) < 8:
            raise forms.ValidationError('رمز عبور حداقل ۸ کاراکتر دارد.')

        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('رمز عبور یک حرف بزرگ انگلیسی داشته باشد.')

        if not re.search(r'[0-9]', password):
            raise forms.ValidationError('رمز عبور یک عدد داشته باشد.')

        return password

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'رمز عبور و تکرار آن یکسان نیستند.')

        return cleaned_data


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['plate_number', 'type', 'color']

        labels = {
            'plate_number': 'شماره پلاک',
            'type': 'نوع وسیله',
            'color': 'رنگ',
        }


class ParkingLotForm(forms.ModelForm):
    class Meta:
        model = ParkingLot
        fields = ['name', 'car_capacity', 'motorcycle_capacity', 'floor_count']

        labels = {
            'name': 'نام پارکینگ',
            'car_capacity': 'ظرفیت جایگاه خودرو',
            'motorcycle_capacity': 'ظرفیت جایگاه موتور',
            'floor_count': 'تعداد طبقات',
        }

        error_messages = {
            'name': {
                'required': 'نام پارکینگ را وارد کنید.',
                'max_length': 'نام پارکینگ نمی‌تواند بیشتر از ۲۰ حرف باشد.',
            },
            'car_capacity': {
                'required': 'ظرفیت جایگاه خودرو را وارد کنید.',
                'invalid': 'ظرفیت جایگاه خودرو را عدد صحیح وارد کنید.',
                'min_value': 'ظرفیت جایگاه خودرو نمی‌تواند منفی باشد.',
                'max_value': 'ظرفیت جایگاه خودرو نمی‌تواند بیشتر از ۵۰۰۰ باشد.',
            },
            'motorcycle_capacity': {
                'required': 'ظرفیت جایگاه موتور را وارد کنید.',
                'invalid': 'ظرفیت جایگاه موتور را عدد صحیح وارد کنید.',
                'min_value': 'ظرفیت جایگاه موتور نمی‌تواند منفی باشد.',
                'max_value': 'ظرفیت جایگاه موتور نمی‌تواند بیشتر از ۱۰۰۰ باشد.',
            },
            'floor_count': {
                'required': 'تعداد طبقات را وارد کنید.',
                'invalid': 'تعداد طبقات را عدد صحیح وارد کنید.',
                'min_value': 'تعداد طبقات حداقل ۱ است.',
                'max_value': 'تعداد طبقات نمی‌تواند بیشتر از ۲۰ باشد.',
            },
        }

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)
        self.fields['name'].max_length = 20
        self.fields['name'].widget.attrs.update({
            'maxlength': '20',
            'placeholder': 'نمکی',
        })
        self.fields['car_capacity'].min_value = 0
        self.fields['car_capacity'].max_value = 5000
        self.fields['car_capacity'].widget.attrs.update({
            'min': '0',
            'max': '5000',
            'placeholder': 'حداکثر ۵۰۰۰',
        })
        self.fields['motorcycle_capacity'].min_value = 0
        self.fields['motorcycle_capacity'].max_value = 1000
        self.fields['motorcycle_capacity'].widget.attrs.update({
            'min': '0',
            'max': '1000',
            'placeholder': 'حداکثر ۱۰۰۰',
        })
        self.fields['floor_count'].min_value = 1
        self.fields['floor_count'].max_value = 20
        self.fields['floor_count'].widget.attrs.update({
            'min': '1',
            'max': '20',
            'placeholder': '۱ تا ۲۰',
        })

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()

        if name and len(name) > 20:
            raise forms.ValidationError('نام پارکینگ نمی‌تواند بیشتر از ۲۰ حرف باشد.')

        if self.customer and name:
            duplicate = ParkingLot.objects.filter(
                customer=self.customer,
                name__iexact=name
            )

            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)

            if duplicate.exists():
                raise forms.ValidationError('پارکینگی با این نام قبلاً ثبت شده است.')

        return name

    def clean(self):
        cleaned_data = super().clean()

        car_capacity = cleaned_data.get('car_capacity') or 0
        motorcycle_capacity = cleaned_data.get('motorcycle_capacity') or 0
        floor_count = cleaned_data.get('floor_count') or 0

        if car_capacity < 0:
            self.add_error('car_capacity', 'ظرفیت خودرو نمی‌تواند منفی باشد.')
        elif car_capacity > 5000:
            self.add_error('car_capacity', 'ظرفیت جایگاه خودرو نمی‌تواند بیشتر از ۵۰۰۰ باشد.')

        if motorcycle_capacity < 0:
            self.add_error('motorcycle_capacity', 'ظرفیت موتور نمی‌تواند منفی باشد.')
        elif motorcycle_capacity > 1000:
            self.add_error('motorcycle_capacity', 'ظرفیت جایگاه موتور نمی‌تواند بیشتر از ۱۰۰۰ باشد.')

        if floor_count < 1:
            self.add_error('floor_count', 'تعداد طبقات حداقل ۱ است.')
        elif floor_count > 20:
            self.add_error('floor_count', 'تعداد طبقات نمی‌تواند بیشتر از ۲۰ باشد.')

        if self.instance.pk:
            current_car_spots = ParkingSpot.objects.filter(
                parking_lot=self.instance,
                spot_type=Vehicle.VEHICLE_TYPE_CAR,
                is_active=True
            ).count()

            current_motorcycle_spots = ParkingSpot.objects.filter(
                parking_lot=self.instance,
                spot_type=Vehicle.VEHICLE_TYPE_MOTORCYCLE,
                is_active=True
            ).count()

            if car_capacity < current_car_spots:
                self.add_error(
                    'car_capacity',
                    f'ظرفیت خودرو نمی‌تواند کمتر از تعداد جایگاه‌های خودروی فعال باشد. تعداد فعلی: {current_car_spots}'
                )

            if motorcycle_capacity < current_motorcycle_spots:
                self.add_error(
                    'motorcycle_capacity',
                    f'ظرفیت موتور نمی‌تواند کمتر از تعداد جایگاه‌های موتور فعال باشد. تعداد فعلی: {current_motorcycle_spots}'
                )

            current_levels_count = (
                ParkingSpot.objects
                .filter(parking_lot=self.instance, is_active=True)
                .values('level')
                .distinct()
                .count()
            )

            if floor_count < current_levels_count:
                self.add_error(
                    'floor_count',
                    f'تعداد طبقات نمی‌تواند کمتر از تعداد طبقات دارای جایگاه فعال باشد. تعداد فعلی: {current_levels_count}'
                )

        return cleaned_data


class ParkingSpotAutoGenerateForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.parking_lot = kwargs.pop('parking_lot')
        super().__init__(*args, **kwargs)

        floor_count = max(self.parking_lot.floor_count or 1, 1)
        car_distribution = self._distribute_capacity(self.parking_lot.car_capacity, floor_count)
        motorcycle_distribution = self._distribute_capacity(self.parking_lot.motorcycle_capacity, floor_count)
        self.floor_rows = []

        for floor_number in range(1, floor_count + 1):
            car_field_name = self._field_name('car', floor_number)
            motorcycle_field_name = self._field_name('motorcycle', floor_number)

            self.fields[car_field_name] = forms.IntegerField(
                label=f'خودرو - طبقه {floor_number}',
                min_value=0,
                initial=car_distribution[floor_number - 1],
            )
            self.fields[motorcycle_field_name] = forms.IntegerField(
                label=f'موتور - طبقه {floor_number}',
                min_value=0,
                initial=motorcycle_distribution[floor_number - 1],
            )
            self.floor_rows.append({
                'floor_number': floor_number,
                'level_label': f'طبقه {floor_number}',
                'car_field': self[car_field_name],
                'motorcycle_field': self[motorcycle_field_name],
            })

    @staticmethod
    def _field_name(vehicle_type, floor_number):
        return f'{vehicle_type}_spots_floor_{floor_number}'

    @staticmethod
    def _distribute_capacity(capacity, floor_count):
        base_count = capacity // floor_count
        remainder = capacity % floor_count

        return [
            base_count + (1 if index < remainder else 0)
            for index in range(floor_count)
        ]

    def clean(self):
        cleaned_data = super().clean()

        floor_count = max(self.parking_lot.floor_count or 1, 1)
        car_counts_by_floor = {}
        motorcycle_counts_by_floor = {}

        for floor_number in range(1, floor_count + 1):
            car_counts_by_floor[floor_number] = cleaned_data.get(
                self._field_name('car', floor_number)
            ) or 0
            motorcycle_counts_by_floor[floor_number] = cleaned_data.get(
                self._field_name('motorcycle', floor_number)
            ) or 0

        car_total = sum(car_counts_by_floor.values())
        motorcycle_total = sum(motorcycle_counts_by_floor.values())

        if car_total == 0 and motorcycle_total == 0:
            raise forms.ValidationError('حداقل برای خودرو یا موتور یک جایگاه وارد کنید.')

        if car_total > self.parking_lot.car_capacity:
            raise forms.ValidationError(
                f'تعداد کل جایگاه‌های خودرو ({car_total}) از ظرفیت خودرو ({self.parking_lot.car_capacity}) بیشتر است.'
            )

        if motorcycle_total > self.parking_lot.motorcycle_capacity:
            raise forms.ValidationError(
                f'تعداد کل جایگاه‌های موتور ({motorcycle_total}) از ظرفیت موتور ({self.parking_lot.motorcycle_capacity}) بیشتر است.'
            )

        cleaned_data['car_total'] = car_total
        cleaned_data['motorcycle_total'] = motorcycle_total
        cleaned_data['car_counts_by_floor'] = car_counts_by_floor
        cleaned_data['motorcycle_counts_by_floor'] = motorcycle_counts_by_floor

        return cleaned_data

class ParkingSpotForm(forms.ModelForm):
    class Meta:
        model = ParkingSpot
        fields = ['parking_lot', 'code', 'level', 'spot_type']

        labels = {
            'parking_lot': 'پارکینگ',
            'code': 'کد جایگاه',
            'level': 'طبقه',
            'spot_type': 'نوع جایگاه',
        }

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

        if self.customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(
                customer=self.customer
            ).order_by('name')

    def clean(self):
        cleaned_data = super().clean()

        parking_lot = cleaned_data.get('parking_lot')
        spot_type = cleaned_data.get('spot_type')
        code = cleaned_data.get('code')
        if parking_lot and code:
            duplicate_code = ParkingSpot.objects.filter(
                parking_lot=parking_lot,
                code__iexact=code,
                is_active=True
            )

            if self.instance.pk:
                duplicate_code = duplicate_code.exclude(pk=self.instance.pk)

            if duplicate_code.exists():
                self.add_error(
                    'code',
                    'برای این پارکینگ، جایگاه فعالی با این کد قبلاً ثبت شده است.'
                )

        if not parking_lot or not spot_type:
            return cleaned_data

        if self.customer and parking_lot.customer != self.customer:
            self.add_error('parking_lot', 'این پارکینگ مربوط به حساب شما نیست.')
            return cleaned_data

        existing_spots = ParkingSpot.objects.filter(
            parking_lot=parking_lot,
            spot_type=spot_type,
            is_active=True
        )

        if self.instance.pk:
            existing_spots = existing_spots.exclude(pk=self.instance.pk)

        current_count = existing_spots.count()

        if spot_type == Vehicle.VEHICLE_TYPE_CAR:
            allowed_capacity = parking_lot.car_capacity
            label = 'خودرو'
        else:
            allowed_capacity = parking_lot.motorcycle_capacity
            label = 'موتور'

        if current_count >= allowed_capacity:
            self.add_error(
                'spot_type',
                f'ظرفیت جایگاه‌های {label} در این پارکینگ تکمیل شده است.'
            )

        return cleaned_data

class TariffForm(forms.ModelForm):
    decimal_error_messages = {
        'required': 'وارد کردن این مبلغ الزامی است.',
        'invalid': 'مبلغ را به صورت عددی وارد کنید.',
        'min_value': 'مبلغ نمی‌تواند منفی باشد.',
        'max_digits': 'مبلغ وارد شده بیش از حد مجاز است. حداکثر ۸ رقم قبل از اعشار و ۲ رقم بعد از اعشار مجاز است.',
        'max_decimal_places': 'حداکثر ۲ رقم بعد از اعشار مجاز است.',
        'max_whole_digits': 'حداکثر ۸ رقم قبل از اعشار مجاز است.',
    }

    first_hour_price = forms.DecimalField(
        label='هزینه ساعت اول',
        max_digits=10,
        decimal_places=2,
        min_value=0,
        error_messages=decimal_error_messages,
    )

    additional_hour_price = forms.DecimalField(
        label='هزینه هر ساعت بعدی',
        max_digits=10,
        decimal_places=2,
        min_value=0,
        error_messages=decimal_error_messages,
    )

    daily_price = forms.DecimalField(
        label='هزینه شبانه‌روزی',
        max_digits=10,
        decimal_places=2,
        min_value=0,
        help_text='هزینه توقف کامل ۲۴ ساعته',
        error_messages=decimal_error_messages,
    )

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
                self.add_error(
                    'vehicle_type',
                    'برای این نوع وسیله نقلیه، یک تعرفه فعال دیگر وجود دارد.'
                )

        return cleaned_data


class CustomerLoginForm(AuthenticationForm):
    username = forms.RegexField(
        label='نام کاربری',
        regex=USERNAME_PATTERN,
        max_length=60,
        widget=forms.TextInput(attrs={
            'maxlength': '60',
            'autocomplete': 'username',
            'placeholder': 'example123',
        }),
        error_messages=USERNAME_ERROR_MESSAGES,
    )
    password = forms.CharField(
        label='گذرواژه',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
        error_messages={'required': 'گذرواژه را وارد کنید.'},
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if not username or not password:
            return self.cleaned_data

        user = User.objects.filter(username__iexact=username).first()

        if user is None:
            self.add_error('username', 'کاربری با این نام کاربری وجود ندارد.')
            return self.cleaned_data

        if not user.check_password(password):
            self.add_error('password', 'گذرواژه وارد شده اشتباه است.')
            return self.cleaned_data

        self.user_cache = user
        self.confirm_login_allowed(user)

        return self.cleaned_data

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                'حساب کاربری شما غیرفعال است.',
                code='inactive',
            )

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
        max_length=25,
        widget=forms.HiddenInput(attrs={'data-plate-hidden': 'true'}),
        error_messages={
            'required': 'شماره پلاک را تکمیل کنید.',
            'max_length': 'شماره پلاک طولانی است.',
        },
    )

    vehicle_type = forms.ChoiceField(
        label='نوع وسیله',
        choices=Vehicle.VEHICLE_TYPE_CHOICES
    )

    color = forms.ChoiceField(
        label='رنگ',
        choices=VEHICLE_COLOR_CHOICES,
        required=False,
    )

    spot = forms.ModelChoiceField(
        label='جایگاه پارک',
        queryset=ParkingSpot.objects.none(),
        empty_label='انتخاب جایگاه آزاد',
        widget=forms.HiddenInput,
        error_messages={
            'invalid_choice': 'جایگاه انتخاب‌شده معتبر نیست یا با نوع وسیله انتخاب‌شده هماهنگ نیست.'
        }
    )
    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        self.parking_lots = kwargs.pop('parking_lots', None)
        super().__init__(*args, **kwargs)

        vehicle_type = None

        if self.data:
            vehicle_type = self.data.get('vehicle_type')

        if self.customer:
            open_session_for_same_spot_code = ParkingSession.objects.filter(
                status=ParkingSession.SESSION_STATUS_OPEN,
                spot__parking_lot=OuterRef('parking_lot'),
                spot__code=OuterRef('code'),
            )

            spots = ParkingSpot.objects.filter(
                parking_lot__customer=self.customer,
                is_active=True,
                is_occupied=False
            ).annotate(
                has_open_session=Exists(open_session_for_same_spot_code)
            ).filter(
                has_open_session=False
            ).select_related('parking_lot')

            if self.parking_lots is not None:
                spots = spots.filter(parking_lot__in=self.parking_lots)

            if vehicle_type:
                spots = spots.filter(spot_type=vehicle_type)

            self.fields['spot'].queryset = spots.order_by(
                'parking_lot__name',
                'level',
                'code'
            )

            self.fields['spot'].label_from_instance = lambda obj: (
                f"{obj.parking_lot.name} - {obj.code} - {obj.get_spot_type_display()}"
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

            if self.parking_lots is not None and not self.parking_lots.filter(pk=spot.parking_lot_id).exists():
                self.add_error(
                    'spot',
                    'شما به این پارکینگ دسترسی ندارید.'
                )

            if spot.is_occupied:
                self.add_error(
                    'spot',
                    'این جایگاه در حال حاضر اشغال است.'
                )

            if ParkingSession.objects.filter(
                spot__parking_lot=spot.parking_lot,
                spot__code=spot.code,
                status=ParkingSession.SESSION_STATUS_OPEN
            ).exists():
                self.add_error(
                    'spot',
                    'این جایگاه در خودروهای فعال استفاده شده است.'
                )

            if vehicle_type and spot.spot_type != vehicle_type:
                self.add_error(
                    'spot',
                    'نوع جایگاه با نوع وسیله نقلیه انتخاب‌شده هماهنگ نیست.'
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
                if hasattr(error, 'message_dict'):
                    for field, messages in error.message_dict.items():
                        self.add_error(field if field in self.fields else None, messages)
                else:
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
                        'این وسیله نقلیه در خودروهای فعال ثبت شده است.'
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
    start_date = JalaliDateField(
        label='از تاریخ',
        required=False,
    )

    end_date = JalaliDateField(
        label='تا تاریخ',
        required=False,
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
        parking_lots = kwargs.pop('parking_lots', None)
        super().__init__(*args, **kwargs)

        if parking_lots is not None:
            self.fields['parking_lot'].queryset = parking_lots.order_by('name')
        elif customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(customer=customer).order_by('name')


class CustomerUserCreateForm(forms.Form):
    username = forms.RegexField(
        label='نام کاربری',
        regex=USERNAME_PATTERN,
        max_length=60,
        help_text=USERNAME_HELP_TEXT,
        widget=forms.TextInput(attrs={
            'maxlength': '60',
            'autocomplete': 'username',
            'placeholder': 'operator12',
        }),
        error_messages=USERNAME_ERROR_MESSAGES,
    )

    full_name = forms.CharField(
        label='نام کاربر',
        max_length=100,
        required=False,
        help_text='نام نمایشی کاربر در پنل. این فیلد اختیاری است.',
        widget=forms.TextInput(attrs={'placeholder': 'رایان حیدری'})
    )

    email = forms.EmailField(
        label='ایمیل',
        required=False,
        help_text='ایمیل کاربر اختیاری است و در صورت ورود، یکتا باشد.',
        widget=forms.EmailInput(attrs={'placeholder': 'user@example.com'})
    )

    password = forms.CharField(
        label='رمز عبور',
        widget=forms.PasswordInput,
        min_length=8,
        help_text='حداقل ۸ کاراکتر، یک حرف بزرگ انگلیسی و یک عدد.',
        error_messages={
            'required': 'رمز عبور را وارد کنید.',
            'min_length': 'رمز عبور حداقل ۸ کاراکتر دارد.',
        }
    )

    password_confirm = forms.CharField(
        label='تکرار رمز عبور',
        widget=forms.PasswordInput,
        help_text='رمز عبور را دوباره وارد کنید.',
        error_messages={'required': 'تکرار رمز عبور را وارد کنید.'}
    )

    role = forms.ChoiceField(
        label='نقش کاربر',
        choices=CustomerUser.ROLE_CHOICES,
        initial=CustomerUser.ROLE_OPERATOR,
        help_text='مالک به کل پنل دسترسی دارد؛ اپراتور فقط پارکینگ مجاز خودش را می‌بیند.',
        error_messages={'required': 'نقش کاربر را انتخاب کنید.'}
    )

    parking_lot = forms.ModelChoiceField(
        label='پارکینگ مجاز اپراتور',
        required=False,
        queryset=ParkingLot.objects.none(),
        empty_label='انتخاب پارکینگ',
        help_text='برای نقش اپراتور انتخاب پارکینگ الزامی است.',
    )

    is_active = forms.BooleanField(
        label='فعال باشد؟',
        required=False,
        initial=True,
        help_text='با غیرفعال کردن، کاربر امکان ورود به پنل را ندارد.'
    )

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

        if self.customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(
                customer=self.customer
            ).order_by('name')

    def clean_username(self):
        username = self.cleaned_data.get('username')

        if not username:
            return username

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

        if not password:
            return password

        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('رمز عبور یک حرف بزرگ انگلیسی داشته باشد.')

        if not re.search(r'[0-9]', password):
            raise forms.ValidationError('رمز عبور یک عدد داشته باشد.')

        return password

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'رمز عبور و تکرار آن یکسان نیستند.')

        role = cleaned_data.get('role')
        parking_lot = cleaned_data.get('parking_lot')

        if role == CustomerUser.ROLE_OPERATOR and not parking_lot:
            self.add_error('parking_lot', 'برای اپراتور انتخاب پارکینگ الزامی است.')

        if role == CustomerUser.ROLE_OWNER:
            cleaned_data['parking_lot'] = None

        return cleaned_data


class CustomerUserUpdateForm(forms.ModelForm):
    full_name = forms.CharField(
        label='نام کاربر',
        max_length=100,
        required=False,
        help_text='نام نمایشی کاربر در پنل. این فیلد اختیاری است.',
        widget=forms.TextInput(attrs={'placeholder': 'رایان حیدری'})
    )

    email = forms.EmailField(
        label='ایمیل',
        required=False,
        help_text='ایمیل کاربر اختیاری است و در صورت ورود، یکتا باشد.',
        widget=forms.EmailInput(attrs={'placeholder': 'user@example.com'})
    )

    class Meta:
        model = CustomerUser
        fields = ['role', 'parking_lot', 'is_active']

        labels = {
            'role': 'نقش کاربر',
            'parking_lot': 'پارکینگ مجاز اپراتور',
            'is_active': 'فعال است؟',
        }
        help_texts = {
            'role': 'مالک به کل پنل دسترسی دارد؛ اپراتور فقط پارکینگ مجاز خودش را می‌بیند.',
            'parking_lot': 'برای نقش اپراتور انتخاب پارکینگ الزامی است.',
            'is_active': 'با غیرفعال کردن، کاربر امکان ورود به پنل را ندارد.',
        }

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        self.customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)

        self.fields['parking_lot'].required = False

        if self.customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(
                customer=self.customer
            ).order_by('name')

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

    def clean(self):
        cleaned_data = super().clean()

        role = cleaned_data.get('role')
        parking_lot = cleaned_data.get('parking_lot')

        if role == CustomerUser.ROLE_OPERATOR and not parking_lot:
            self.add_error('parking_lot', 'برای اپراتور انتخاب پارکینگ الزامی است.')

        if role == CustomerUser.ROLE_OWNER:
            cleaned_data['parking_lot'] = None

        return cleaned_data


class BugReportForm(forms.ModelForm):
    class Meta:
        model = BugReport
        fields = ['subject', 'description']
        labels = {
            'subject': 'موضوع مشکل',
            'description': 'توضیحات مشکل',
        }
        widgets = {
            'subject': forms.TextInput(attrs={
                'maxlength': '120',
                'placeholder': 'خطا در ثبت پرداخت',
            }),
            'description': forms.Textarea(attrs={
                'rows': '5',
                'placeholder': 'مشکل را کوتاه و دقیق توضیح دهید.',
            }),
        }
        error_messages = {
            'subject': {
                'required': 'موضوع مشکل را وارد کنید.',
                'max_length': 'موضوع مشکل نمی‌تواند بیشتر از ۱۲۰ حرف باشد.',
            },
            'description': {
                'required': 'توضیحات مشکل را وارد کنید.',
            },
        }

    def clean_subject(self):
        subject = (self.cleaned_data.get('subject') or '').strip()

        if not subject:
            raise forms.ValidationError('موضوع مشکل را وارد کنید.')

        return subject

    def clean_description(self):
        description = (self.cleaned_data.get('description') or '').strip()

        if not description:
            raise forms.ValidationError('توضیحات مشکل را وارد کنید.')

        if len(description) < 10:
            raise forms.ValidationError('توضیحات مشکل حداقل ۱۰ حرف دارد.')

        return description

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

    spot_type = forms.ChoiceField(
    label='نوع جایگاه',
    required=False,
    choices=[('', 'همه نوع‌ها')] + list(Vehicle.VEHICLE_TYPE_CHOICES)
    )

    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)
        parking_lots = kwargs.pop('parking_lots', None)
        super().__init__(*args, **kwargs)

        if parking_lots is not None:
            self.fields['parking_lot'].queryset = parking_lots.order_by('name')
        elif customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(customer=customer).order_by('name')


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
        label='وضعیت خودرو',
        required=False,
        choices=[('', 'همه وضعیت‌ها')] + list(ParkingSession.STATUS_CHOICES)
    )

    entry_from = JalaliDateField(
        label='ورود از',
        required=False,
    )

    entry_to = JalaliDateField(
        label='ورود تا',
        required=False,
    )

    exit_from = JalaliDateField(
        label='خروج از',
        required=False,
    )

    exit_to = JalaliDateField(
        label='خروج تا',
        required=False,
    )

    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)
        parking_lots = kwargs.pop('parking_lots', None)
        super().__init__(*args, **kwargs)

        if parking_lots is not None:
            self.fields['parking_lot'].queryset = parking_lots.order_by('name')
        elif customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(customer=customer).order_by('name')


class PaymentFilterForm(forms.Form):
    plate_number = forms.CharField(
        label='شماره پلاک',
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

    payment_from = JalaliDateField(
        label='پرداخت از تاریخ',
        required=False,
    )

    payment_to = JalaliDateField(
        label='پرداخت تا تاریخ',
        required=False,
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
        parking_lots = kwargs.pop('parking_lots', None)
        super().__init__(*args, **kwargs)

        if parking_lots is not None:
            self.fields['parking_lot'].queryset = parking_lots.order_by('name')
        elif customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(customer=customer).order_by('name')


class ReceiptFilterForm(forms.Form):
    receipt_number = forms.CharField(
        label='شماره رسید',
        required=False
    )

    plate_number = forms.CharField(
        label='شماره پلاک',
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

    issue_from = JalaliDateField(
        label='صدور از تاریخ',
        required=False,
    )

    issue_to = JalaliDateField(
        label='صدور تا تاریخ',
        required=False,
    )

    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)
        parking_lots = kwargs.pop('parking_lots', None)
        super().__init__(*args, **kwargs)

        if parking_lots is not None:
            self.fields['parking_lot'].queryset = parking_lots.order_by('name')
        elif customer:
            self.fields['parking_lot'].queryset = ParkingLot.objects.filter(customer=customer).order_by('name')


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
        help_text='حداقل ۸ کاراکتر، یک حرف بزرگ انگلیسی و یک عدد.',
        error_messages={
            'required': 'رمز عبور جدید را وارد کنید.',
            'min_length': 'رمز عبور حداقل ۸ کاراکتر دارد.',
        }
    )

    password_confirm = forms.CharField(
        label='تکرار رمز عبور جدید',
        widget=forms.PasswordInput,
        help_text='رمز جدید را دوباره وارد کنید.',
        error_messages={'required': 'تکرار رمز عبور جدید را وارد کنید.'}
    )

    def clean_password(self):
        password = self.cleaned_data.get('password')

        if not password:
            return password

        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('رمز عبور یک حرف بزرگ انگلیسی داشته باشد.')

        if not re.search(r'[0-9]', password):
            raise forms.ValidationError('رمز عبور یک عدد داشته باشد.')

        return password

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'رمز عبور و تکرار آن یکسان نیستند.')

        return cleaned_data    
    
class AccountPasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label='رمز عبور فعلی',
        widget=forms.PasswordInput,
        help_text='برای تأیید هویت، رمز فعلی حساب را وارد کنید.',
        error_messages={'required': 'رمز عبور فعلی را وارد کنید.'}
    )

    new_password = forms.CharField(
        label='رمز عبور جدید',
        widget=forms.PasswordInput,
        min_length=8,
        help_text='حداقل ۸ کاراکتر، یک حرف بزرگ انگلیسی و یک عدد.',
        error_messages={
            'required': 'رمز عبور جدید را وارد کنید.',
            'min_length': 'رمز عبور حداقل ۸ کاراکتر دارد.',
        }
    )

    new_password_confirm = forms.CharField(
        label='تکرار رمز عبور جدید',
        widget=forms.PasswordInput,
        help_text='رمز جدید را دوباره وارد کنید.',
        error_messages={'required': 'تکرار رمز عبور جدید را وارد کنید.'}
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')

        if not old_password:
            return old_password

        if not self.user.check_password(old_password):
            raise forms.ValidationError('رمز عبور فعلی اشتباه است.')

        return old_password

    def clean_new_password(self):
        new_password = self.cleaned_data.get('new_password')

        if not new_password:
            return new_password

        if not re.search(r'[A-Z]', new_password):
            raise forms.ValidationError('رمز عبور یک حرف بزرگ انگلیسی داشته باشد.')

        if not re.search(r'[0-9]', new_password):
            raise forms.ValidationError('رمز عبور یک عدد داشته باشد.')

        return new_password

    def clean(self):
        cleaned_data = super().clean()

        new_password = cleaned_data.get('new_password')
        new_password_confirm = cleaned_data.get('new_password_confirm')

        if new_password and new_password_confirm and new_password != new_password_confirm:
            self.add_error('new_password_confirm', 'رمز عبور جدید و تکرار آن یکسان نیستند.')

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
        help_texts = {
            'name': PERSIAN_NAME_HELP_TEXT,
            'owner_name': PERSIAN_NAME_HELP_TEXT,
            'phone': 'شماره تماس ۱۱ رقمی، مثل 09113284955.',
            'email': 'ایمیل فعال برای پیگیری حساب.',
            'address': 'تهران، خیابان آزادی، پلاک ۱۲',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'maxlength': '50',
                'placeholder': 'پارکینگ آزادی',
            }),
            'owner_name': forms.TextInput(attrs={
                'maxlength': '50',
                'placeholder': 'محمد پسندیده',
            }),
            'phone': forms.TextInput(attrs={
                'maxlength': '11',
                'inputmode': 'numeric',
                'placeholder': '09113284955',
            }),
            'address': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'تهران، خیابان آزادی، پلاک ۱۲',
            }),
        }
        error_messages = {
            'name': {
                'required': 'نام پارکینگ را وارد کنید.',
                'max_length': 'نام پارکینگ نمی‌تواند بیشتر از ۵۰ کاراکتر باشد.',
            },
            'owner_name': {
                'required': 'نام مالک یا مدیر را وارد کنید.',
                'max_length': 'نام مالک یا مدیر نمی‌تواند بیشتر از ۵۰ کاراکتر باشد.',
            },
            'email': {
                'required': 'ایمیل را وارد کنید.',
                'invalid': 'ایمیل وارد شده معتبر نیست.',
            },
            'phone': {
                'required': 'شماره تماس را وارد کنید.',
            },
            'address': {
                'required': 'آدرس پارکینگ را وارد کنید.',
            },
        }

    def clean_name(self):
        return clean_persian_name(self.cleaned_data.get('name'), 'نام پارکینگ')

    def clean_owner_name(self):
        return clean_persian_name(self.cleaned_data.get('owner_name'), 'نام مالک یا مدیر')

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        if not phone:
            raise forms.ValidationError('وارد کردن شماره تماس الزامی است.')

        if not phone.isdigit():
            raise forms.ValidationError('شماره تماس را فقط با عدد وارد کنید.')

        if len(phone) != 11:
            raise forms.ValidationError('شماره تماس را ۱۱ رقمی وارد کنید.')

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

    def clean_address(self):
        address = (self.cleaned_data.get('address') or '').strip()

        if not address:
            raise forms.ValidationError('آدرس پارکینگ را وارد کنید.')

        return address
