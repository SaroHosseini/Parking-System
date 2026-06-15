import math
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator


PERSIAN_PLATE_LETTERS = "ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی"
SPECIAL_PLATE_LETTERS = ("معلولین", "تشریفات", "D", "S")
PLATE_LETTER_PATTERN = (
    r'(?:[' + PERSIAN_PLATE_LETTERS + r']|'
    + '|'.join(SPECIAL_PLATE_LETTERS)
    + r')'
)
PERSIAN_NAME_LETTERS = "آابپتثجچحخدذرزژسشصضطظعغفقکكگلمنوهیيىۀةئؤء"


car_plate_validator = RegexValidator(
    regex=r'^[0-9]{2}' + PLATE_LETTER_PATTERN + r'[0-9]{3}-[0-9]{2}$',
    message=(
        "فرمت پلاک خودرو نامعتبر است. نمونه صحیح: 12ب345-67 "
        "(دو رقم، حرف پلاک، سه رقم، خط تیره، دو رقم)."
    ),
)


motorcycle_plate_validator = RegexValidator(
    regex=r'^[0-9]{8}$',
    message="پلاک موتورسیکلت را دقیقاً ۸ رقم وارد کنید.",
)


persian_name_validator = RegexValidator(
    regex=r'^[' + PERSIAN_NAME_LETTERS + r'\s‌]+$',
    message="این فیلد فقط می‌تواند شامل حروف فارسی باشد.",
)


class Customer(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'در انتظار بررسی'),
        (STATUS_APPROVED, 'تأیید شده'),
        (STATUS_REJECTED, 'رد شده'),
    ]

    name = models.CharField(
        "نام پارکینگ / مشتری",
        max_length=50,
        validators=[persian_name_validator],
    )
    owner_name = models.CharField(
        "نام مالک",
        max_length=50,
        validators=[persian_name_validator],
    )
    phone = models.CharField("شماره تماس", max_length=20)
    email = models.EmailField("ایمیل", blank=True)
    address = models.TextField("آدرس", blank=True)

    status = models.CharField(
        "وضعیت درخواست",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    created_at = models.DateTimeField("زمان ثبت درخواست", auto_now_add=True)
    approved_at = models.DateTimeField("زمان تأیید", null=True, blank=True)
    is_active = models.BooleanField("فعال است؟", default=False)

    class Meta:
        verbose_name = "مشتری"
        verbose_name_plural = "مشتریان"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.status == self.STATUS_APPROVED:
            self.is_active = True
            if not self.approved_at:
                self.approved_at = timezone.now()

        elif self.status in [self.STATUS_PENDING, self.STATUS_REJECTED]:
            self.is_active = False

        super().save(*args, **kwargs)

        if self.pk:
            should_activate_users = self.status == self.STATUS_APPROVED and self.is_active

            for customer_user in self.users.select_related('user').all():
                user = customer_user.user
                user.is_active = should_activate_users and customer_user.is_active
                user.save(update_fields=['is_active'])

    def __str__(self):
        return f"{self.name} - {self.owner_name}"

class CustomerUser(models.Model):
    ROLE_OWNER = 'owner'
    ROLE_OPERATOR = 'operator'

    ROLE_CHOICES = [
        (ROLE_OWNER, 'مالک'),
        (ROLE_OPERATOR, 'اپراتور'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile',
        verbose_name='کاربر',
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='users',
        verbose_name='مشتری',
    )

    role = models.CharField(
        "نقش",
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_OPERATOR,
    )

    parking_lot = models.ForeignKey(
        'ParkingLot',
        on_delete=models.SET_NULL,
        related_name='assigned_users',
        verbose_name='پارکینگ مجاز',
        null=True,
        blank=True,
    )
    
    is_active = models.BooleanField("فعال است؟", default=True)

    class Meta:
        verbose_name = "کاربر مشتری"
        verbose_name_plural = "کاربران مشتریان"
        ordering = ['customer', 'user__username']

    def clean(self):
        super().clean()

        if self.role == self.ROLE_OPERATOR and not self.parking_lot_id:
            raise ValidationError({
                'parking_lot': 'برای اپراتور انتخاب پارکینگ الزامی است.'
            })

        if self.parking_lot_id and self.customer_id and self.parking_lot.customer_id != self.customer_id:
            raise ValidationError({
                'parking_lot': 'پارکینگ انتخاب‌شده مربوط به این مشتری نیست.'
            })

    def save(self, *args, **kwargs):
        if self.role == self.ROLE_OWNER:
            self.parking_lot = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.customer.name} - {self.get_role_display()}"


class Vehicle(models.Model):
    VEHICLE_TYPE_CAR = 'car'
    VEHICLE_TYPE_MOTORCYCLE = 'motorcycle'

    VEHICLE_TYPE_CHOICES = [
        (VEHICLE_TYPE_CAR, 'سواری'),
        (VEHICLE_TYPE_MOTORCYCLE, 'موتورسیکلت'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='vehicles',
        verbose_name='مشتری',
    )

    plate_number = models.CharField(
        "شماره پلاک",
        max_length=25,
        help_text="خودرو: 12ب345-67، موتور: 8 رقم",
    )

    type = models.CharField(
        "نوع وسیله",
        max_length=20,
        choices=VEHICLE_TYPE_CHOICES,
        default=VEHICLE_TYPE_CAR,
    )

    color = models.CharField("رنگ", max_length=30, blank=True)

    def __str__(self):
        return f"{self.plate_number}"

    def clean(self):
        super().clean()

        plate = (self.plate_number or "").strip()

        if self.type == self.VEHICLE_TYPE_CAR:
            try:
                car_plate_validator(plate)
            except ValidationError as e:
                raise ValidationError({'plate_number': e.message})

        elif self.type == self.VEHICLE_TYPE_MOTORCYCLE:
            try:
                motorcycle_plate_validator(plate)
            except ValidationError as e:
                raise ValidationError({'plate_number': e.message})

    class Meta:
        verbose_name = 'وسیله نقلیه'
        verbose_name_plural = 'وسایل نقلیه'
        ordering = ['plate_number']
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'plate_number'],
                name='unique_vehicle_plate_per_customer'
            )
        ]


class ParkingLot(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='parking_lots',
        verbose_name='مشتری',
    )

    name = models.CharField("نام پارکینگ", max_length=20)

    car_capacity = models.PositiveIntegerField(
        "ظرفیت جایگاه خودرو",
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5000)],
    )
    motorcycle_capacity = models.PositiveIntegerField(
        "ظرفیت جایگاه موتور",
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
    )
    floor_count = models.PositiveIntegerField(
        "تعداد طبقات",
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    total_capacity = models.PositiveIntegerField("ظرفیت کل")

    def save(self, *args, **kwargs):
        self.total_capacity = self.car_capacity + self.motorcycle_capacity
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    class Meta:
        ordering = ['customer', 'name']
        verbose_name = 'پارکینگ'
        verbose_name_plural = 'پارکینگ‌ها'
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'name'],
                name='unique_parking_lot_name_per_customer'
            )
        ]


class ParkingSpot(models.Model):
    parking_lot = models.ForeignKey(
        ParkingLot,
        on_delete=models.CASCADE,
        related_name="spots",
        verbose_name="پارکینگ",
    )

    spot_type = models.CharField(
    "نوع جایگاه",
    max_length=20,
    choices=Vehicle.VEHICLE_TYPE_CHOICES,
    default=Vehicle.VEHICLE_TYPE_CAR
    )

    code = models.CharField('کد محل', max_length=255)
    level = models.CharField('طبقه', max_length=255)
    is_occupied = models.BooleanField("اشغال است؟", default=False)
    is_active = models.BooleanField(
    "فعال است؟",
    default=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['parking_lot', 'code'],
                condition=Q(is_active=True),
                name='unique_active_spot_code_per_lot'
            )
        ]
        verbose_name = "جایگاه پارک"
        verbose_name_plural = "جایگاه‌های پارک"
        ordering = ['parking_lot', 'level', 'code']

    def __str__(self):
        status = "🟢 آزاد در حال حاضر" if not self.is_occupied else "🔴 اشغال در حال حاضر"
        return f"{self.parking_lot.name} - {self.code} – طبقه {self.level} – {status}"


class Tariff(models.Model):
    VEHICLE_TYPE_CAR = 'car'
    VEHICLE_TYPE_MOTORCYCLE = 'motorcycle'

    VEHICLE_TYPE_CHOICES = [
        (VEHICLE_TYPE_CAR, 'سواری'),
        (VEHICLE_TYPE_MOTORCYCLE, 'موتورسیکلت'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='tariffs',
        verbose_name='مشتری',
    )

    name = models.CharField("نام تعرفه", max_length=100)

    vehicle_type = models.CharField(
        "نوع وسیله نقلیه",
        max_length=20,
        choices=VEHICLE_TYPE_CHOICES,
        default=VEHICLE_TYPE_CAR,
    )

    first_hour_price = models.DecimalField(
        "هزینه ساعت اول",
        max_digits=10,
        decimal_places=2,
    )

    additional_hour_price = models.DecimalField(
        "هزینه هر ساعت بعدی",
        max_digits=10,
        decimal_places=2,
    )

    daily_price = models.DecimalField(
        "هزینه شبانه‌روزی",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="هزینه توقف کامل ۲۴ ساعته",
    )

    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "تعرفه"
        verbose_name_plural = "تعرفه‌ها"
        ordering = ['customer', 'vehicle_type', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'vehicle_type'],
                condition=Q(is_active=True),
                name='unique_active_tariff_per_customer_vehicle_type'
            )
        ]

    def __str__(self):
        return f"{self.customer.name} - {self.name} - {self.get_vehicle_type_display()}"


class ParkingSession(models.Model):
    SESSION_STATUS_OPEN = 'open'
    SESSION_STATUS_CLOSED = 'closed'
    SESSION_STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (SESSION_STATUS_OPEN, "باز (در حال پارک)"),
        (SESSION_STATUS_CLOSED, "بسته (خارج شده)"),
        (SESSION_STATUS_CANCELLED, "لغو شده"),
    ]

    entry_time = models.DateTimeField("زمان ورود", default=timezone.now)
    exit_time = models.DateTimeField("زمان خروج", null=True, blank=True)

    total_duration_minutes = models.PositiveIntegerField(
        "مدت کل (دقیقه)",
        null=True,
        blank=True,
        help_text="بعد از خروج محاسبه و ذخیره می‌شود.",
    )

    status = models.CharField(
        "وضعیت",
        choices=STATUS_CHOICES,
        max_length=20,
        default=SESSION_STATUS_OPEN,
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name='وسیله نقلیه',
    )

    spot = models.ForeignKey(
        ParkingSpot,
        on_delete=models.PROTECT,
        related_name='sessions',
        verbose_name='جایگاه',
    )

    calculated_fee = models.DecimalField(
        "هزینه محاسبه‌شده",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='پس از ثبت خروج خودکار محاسبه می‌شود',
    )

    class Meta:
        verbose_name = "خودروی فعال"
        verbose_name_plural = "خودروهای فعال"
        ordering = ['-entry_time']
        constraints = [
            models.UniqueConstraint(
                fields=['vehicle'],
                condition=Q(status='open'),
                name='unique_open_session_per_vehicle'
            ),
            models.UniqueConstraint(
                fields=['spot'],
                condition=Q(status='open'),
                name='unique_open_session_per_spot'
            ),
        ]

    def clean(self):
        super().clean()

        if self.vehicle_id and self.spot_id:
            if self.vehicle.customer != self.spot.parking_lot.customer:
                raise ValidationError(
                    'وسیله نقلیه و جایگاه پارک به یک مشتری متصل نیستند.'
                )

            if self.vehicle.type != self.spot.spot_type:
                raise ValidationError(
                    'نوع جایگاه با نوع وسیله نقلیه هماهنگ نیست.'
                )

            if self.status == self.SESSION_STATUS_OPEN and not self.spot.is_active:
                raise ValidationError(
                    'برای جایگاه غیرفعال، خودروی فعال ثبت نمی‌شود.'
                )

            if self.status == self.SESSION_STATUS_OPEN:
                other_open_session_for_spot = ParkingSession.objects.filter(
                    spot=self.spot,
                    status=self.SESSION_STATUS_OPEN,
                ).exclude(pk=self.pk).exists()

                if other_open_session_for_spot:
                    raise ValidationError(
                        'این جایگاه در خودروهای فعال استفاده شده است.'
                    )

                other_open_session_for_vehicle = ParkingSession.objects.filter(
                    vehicle=self.vehicle,
                    status=self.SESSION_STATUS_OPEN,
                ).exclude(pk=self.pk).exists()

                if other_open_session_for_vehicle:
                    raise ValidationError(
                        f"پلاک {self.vehicle.plate_number} در خودروهای فعال ثبت شده است."
                    )

        if self.entry_time and self.exit_time and self.exit_time < self.entry_time:
            raise ValidationError(
                'زمان خروج نمی‌تواند قبل از زمان ورود باشد.'
            )

    def calculate_duration(self):
        if self.entry_time and self.exit_time:
            duration = self.exit_time - self.entry_time
            total_seconds = duration.total_seconds()

            if total_seconds < 0:
                return None

            minutes = math.ceil(total_seconds / 60)
            return max(minutes, 1)

        return None

    def get_applicable_tariff(self):
        return Tariff.objects.filter(
            customer=self.vehicle.customer,
            vehicle_type=self.vehicle.type,
            is_active=True,
        ).first()

    def calculate_fee(self):
        if self.total_duration_minutes is None:
            return Decimal("0.00")

        tariff = self.get_applicable_tariff()

        if not tariff:
            return Decimal("0.00")

        total_hours = math.ceil(self.total_duration_minutes / 60)

        full_days = total_hours // 24
        remaining_hours = total_hours % 24

        total_fee = Decimal("0.00")

        if full_days > 0:
            total_fee += Decimal(full_days) * tariff.daily_price

        if remaining_hours == 0:
            return total_fee

        if remaining_hours <= 1:
            total_fee += tariff.first_hour_price
        else:
            total_fee += tariff.first_hour_price
            total_fee += Decimal(remaining_hours - 1) * tariff.additional_hour_price

        return total_fee

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        old_exit_time = None
        old_spot = None

        if not is_new:
            old_session = ParkingSession.objects.filter(pk=self.pk).first()

            if old_session:
                old_exit_time = old_session.exit_time
                old_spot = old_session.spot

        is_being_closed_now = (
            self.exit_time is not None and
            old_exit_time is None and
            self.status != self.SESSION_STATUS_CANCELLED
        )

        if is_being_closed_now:
            self.total_duration_minutes = self.calculate_duration()
            self.calculated_fee = self.calculate_fee()
            self.status = self.SESSION_STATUS_CLOSED

        self.full_clean()

        super().save(*args, **kwargs)

        if old_spot and old_spot != self.spot:
            old_spot_has_open_session = ParkingSession.objects.filter(
                spot=old_spot,
                status=self.SESSION_STATUS_OPEN,
            ).exists()

            if not old_spot_has_open_session and old_spot.is_occupied:
                old_spot.is_occupied = False
                old_spot.save(update_fields=['is_occupied'])

        if self.spot:
            if self.status == self.SESSION_STATUS_OPEN:
                if not self.spot.is_occupied:
                    self.spot.is_occupied = True
                    self.spot.save(update_fields=['is_occupied'])
            else:
                current_spot_has_other_open_session = ParkingSession.objects.filter(
                    spot=self.spot,
                    status=self.SESSION_STATUS_OPEN,
                ).exclude(pk=self.pk).exists()

                if not current_spot_has_other_open_session and self.spot.is_occupied:
                    self.spot.is_occupied = False
                    self.spot.save(update_fields=['is_occupied'])

        if is_being_closed_now:
            Payment.objects.get_or_create(
                session=self,
                defaults={
                    'amount': self.calculated_fee,
                    'payment_status': Payment.PAYMENT_STATUS_OPEN,
                }
            )

        try_create_receipt(self)

    def __str__(self):
        vehicle_plate = self.vehicle.plate_number if self.vehicle else "نامشخص"
        return f"پلاک: {vehicle_plate}"

class Payment(models.Model):
    PAYMENT_METHOD_POS = 'pos'
    PAYMENT_METHOD_CASH = 'cash'
    PAYMENT_METHOD_CARD_TO_CARD_TRANSFER = 'card_to_card_transfer'
    PAYMENT_METHOD_ONLINE = 'online_gateway'

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_POS, 'پرداخت با کارتخوان'),
        (PAYMENT_METHOD_CASH, 'پرداخت نقدی'),
        (PAYMENT_METHOD_CARD_TO_CARD_TRANSFER, 'پرداخت با کارت به کارت'),
        (PAYMENT_METHOD_ONLINE, 'پرداخت با درگاه آنلاین'),
    ]

    PAYMENT_STATUS_OPEN = 'open'
    PAYMENT_STATUS_CLOSED = 'closed'
    PAYMENT_STATUS_CANCELLED = 'cancelled'

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_OPEN, 'باز'),
        (PAYMENT_STATUS_CLOSED, 'بسته شده'),
        (PAYMENT_STATUS_CANCELLED, 'لغو شده'),
    ]

    amount = models.DecimalField('مقدار', max_digits=10, decimal_places=2, blank=True)

    payment_time = models.DateTimeField(
        "زمان پرداخت",
        null=True,
        blank=True
    )

    payment_method = models.CharField(
        'نحوه پرداخت',
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True,
    )

    payment_status = models.CharField(
        'وضعیت پرداخت',
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_OPEN,
    )

    session = models.ForeignKey(
        ParkingSession,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='خودروی فعال',
    )

    class Meta:
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت‌ها'
        ordering = ['-payment_time']

    def __str__(self):
        return f"پرداخت #{self.id} - {self.amount} - {self.get_payment_method_display()}"

    def _get_session_for_validation(self):
        if not self.session_id:
            return None

        try:
            return self.session
        except ParkingSession.DoesNotExist:
            return None


    def clean(self):
        super().clean()

        session = self._get_session_for_validation()

        if session is None:
            raise ValidationError({
                'session': 'پرداخت به خودروی فعال متصل نیست.'
            })

        if session.status != ParkingSession.SESSION_STATUS_CLOSED:
            raise ValidationError({
                'session': 'پرداخت برای خودروی دارای خروج ثبت می‌شود.'
            })

        if session.calculated_fee is None:
            raise ValidationError({
                'session': 'هزینه توقف هنوز محاسبه نشده است.'
            })

        if self.payment_status == self.PAYMENT_STATUS_CLOSED and not self.payment_method:
            raise ValidationError({
                'payment_method': 'برای بستن پرداخت، انتخاب روش پرداخت الزامی است.'
            })

    def save(self, *args, **kwargs):
        session = self._get_session_for_validation()

        if session is not None:
            self.amount = session.calculated_fee

        payment_is_being_closed = (
            self.payment_method and
            self.payment_status == self.PAYMENT_STATUS_OPEN
        )

        if payment_is_being_closed:
            self.payment_status = self.PAYMENT_STATUS_CLOSED
            self.payment_time = timezone.now()

        if self.payment_status == self.PAYMENT_STATUS_CLOSED and not self.payment_time:
            self.payment_time = timezone.now()

        self.full_clean()

        super().save(*args, **kwargs)

        if self.session_id:
            try_create_receipt(self.session)

class Receipt(models.Model):
    issue_time = models.DateTimeField('زمان صدور رسید', default=timezone.now)

    receipt_number = models.CharField(
        'شماره رسید',
        max_length=50,
        unique=True,
        editable=False,
        blank=True,
    )

    calculated_fee = models.DecimalField(
        'مبلغ روی رسید',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    session = models.OneToOneField(
        ParkingSession,
        on_delete=models.SET_NULL,
        related_name='receipt',
        verbose_name='خودروی فعال',
        null=True,
    )

    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        related_name='receipt',
        verbose_name='پرداخت',
        null=True,
        blank=True,
    )

    content = models.TextField(
        'متن رسید',
        blank=True,
        null=True,
        help_text='متن آماده چاپ شامل زمان ورود و خروج، کد جایگاه، شماره پلاک، شماره رسید، روش پرداخت و هزینه',
    )

    class Meta:
        verbose_name = 'رسید'
        verbose_name_plural = 'رسیدها'
        ordering = ['-issue_time']

    def __str__(self):
        return f"رسید #{self.receipt_number} - خودروی فعال {self.session_id}"

    def generate_receipt_number(self):
        local_time = timezone.localtime(timezone.now())
        milliseconds = local_time.microsecond // 1000
        return local_time.strftime("%y%m%d%H%M%S") + f"{milliseconds:03d}"

    def generate_content(self):
        session = self.session

        if not session:
            lines = [
                f"شماره رسید: {self.receipt_number}",
                f"خودروی فعال: حذف شده",
                f"وضعیت پرداخت: {self.payment.get_payment_status_display() if self.payment else 'حذف شده'}",
                f"مبلغ قابل پرداخت: {self.calculated_fee or 'نامشخص'} تومان",
                f"روش پرداخت: {self.payment.get_payment_method_display() if self.payment else 'حذف شده'}",
            ]
            return "\n".join(lines)

        vehicle_plate = session.vehicle.plate_number if session.vehicle else "نامشخص"
        spot_code = session.spot.code if session.spot else "نامشخص"

        entry = session.entry_time
        exit_time = session.exit_time

        entry_str = timezone.localtime(entry).strftime('%Y-%m-%d %H:%M') if entry else 'نامشخص'
        exit_str = timezone.localtime(exit_time).strftime('%Y-%m-%d %H:%M') if exit_time else 'نامشخص'

        fee = self.calculated_fee or session.calculated_fee or Decimal("0.00")

        payment_method = self.payment.get_payment_method_display() if self.payment else 'حذف شده'
        payment_status = self.payment.get_payment_status_display() if self.payment else 'حذف شده'

        lines = [
            f"زمان ورود: {entry_str}",
            f"زمان خروج: {exit_str}",
            f"شماره رسید: {self.receipt_number}",
            f"شماره پلاک: {vehicle_plate}",
            f"کد جایگاه: {spot_code}",
            f"وضعیت پرداخت: {payment_status}",
            f"مبلغ قابل پرداخت: {fee} تومان",
            f"روش پرداخت: {payment_method}",
        ]

        return "\n".join(lines)

    def save(self, *args, **kwargs):
        session = self.session

        if self.calculated_fee is None:
            if session and session.calculated_fee is not None:
                self.calculated_fee = session.calculated_fee
            elif session:
                self.calculated_fee = session.calculate_fee()
            else:
                self.calculated_fee = Decimal("0.00")

        if not self.receipt_number:
            self.receipt_number = self.generate_receipt_number()

        self.content = self.generate_content()

        super().save(*args, **kwargs)


def try_create_receipt(session):
    if not session:
        return

    if session.status != ParkingSession.SESSION_STATUS_CLOSED or not session.exit_time:
        return

    payment = (
        Payment.objects
        .filter(session=session, payment_status=Payment.PAYMENT_STATUS_CLOSED)
        .order_by("-payment_time")
        .first()
    )

    if not payment:
        return

    receipt, created = Receipt.objects.get_or_create(
        session=session,
        defaults={
            "payment": payment,
            "calculated_fee": payment.amount or session.calculated_fee or Decimal("0.00"),
        }
    )

    if not created:
        receipt.payment = payment

        if payment.amount is not None:
            receipt.calculated_fee = payment.amount
        elif session.calculated_fee is not None:
            receipt.calculated_fee = session.calculated_fee
        else:
            receipt.calculated_fee = Decimal("0.00")

    receipt.save()


class BugReport(models.Model):
    STATUS_REVIEWING = 'reviewing'
    STATUS_RESOLVED = 'resolved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_REVIEWING, 'در حال بررسی'),
        (STATUS_RESOLVED, 'حل شده'),
        (STATUS_REJECTED, 'رد شده'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='bug_reports',
        verbose_name='مشتری',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='bug_reports',
        verbose_name='کاربر',
        null=True,
        blank=True,
    )
    username = models.CharField('نام کاربری', max_length=150)
    role = models.CharField('نقش', max_length=50, blank=True)
    phone = models.CharField('شماره تماس', max_length=20, blank=True)
    subject = models.CharField('موضوع', max_length=120)
    description = models.TextField('توضیحات')
    status = models.CharField(
        'وضعیت',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_REVIEWING,
    )
    created_at = models.DateTimeField('زمان ثبت', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = 'گزارش مشکل'
        verbose_name_plural = 'باگ‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.subject} - {self.username}'


class Announcement(models.Model):
    title = models.CharField('عنوان اطلاعیه', max_length=120)
    description = models.TextField('متن توضیحات')
    is_active = models.BooleanField('فعال است؟', default=True)
    created_at = models.DateTimeField('زمان ایجاد', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین بروزرسانی', auto_now=True)

    class Meta:
        verbose_name = 'اطلاعیه'
        verbose_name_plural = 'اطلاعیه‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class AnnouncementView(models.Model):
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='views',
        verbose_name='اطلاعیه',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='announcement_views',
        verbose_name='کاربر',
    )
    seen_at = models.DateTimeField('زمان مشاهده', auto_now_add=True)

    class Meta:
        verbose_name = 'مشاهده اطلاعیه'
        verbose_name_plural = 'مشاهده‌های اطلاعیه'
        ordering = ['-seen_at']
        constraints = [
            models.UniqueConstraint(
                fields=['announcement', 'user'],
                name='unique_announcement_view_per_user',
            )
        ]

    def __str__(self):
        return f'{self.announcement} - {self.user}'


# History Models

class ParkingSessionHistory(models.Model):
    original_id = models.IntegerField('شناسه اصلی خودروی فعال')

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='مشتری',
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='وسیله نقلیه',
    )

    parking_lot = models.ForeignKey(
        ParkingLot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='پارکینگ',
    )

    parking_spot = models.ForeignKey(
        ParkingSpot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='جای پارک',
    )

    entry_time = models.DateTimeField(verbose_name='زمان ورود')
    exit_time = models.DateTimeField(null=True, blank=True, verbose_name='زمان خروج')
    status = models.CharField(max_length=20, verbose_name='وضعیت')

    calculated_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='هزینه محاسبه‌شده',
    )

    deleted_at = models.DateTimeField(default=timezone.now, verbose_name='زمان حذف')

    deleted_by = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name='حذف شده توسط',
    )

    class Meta:
        verbose_name = 'تاریخچه خودروی فعال'
        verbose_name_plural = 'تاریخچه خودروهای فعال'

    def __str__(self):
        return f'History of session {self.original_id} at {self.deleted_at}'


class PaymentHistory(models.Model):
    original_id = models.IntegerField("شناسه اصلی پرداخت")

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='مشتری',
    )

    amount = models.DecimalField('مقدار', max_digits=10, decimal_places=2, blank=True)
    payment_time = models.DateTimeField('زمان پرداخت',null=True,blank=True,)

    payment_method = models.CharField(
        'نحوه پرداخت',
        max_length=50,
        choices=Payment.PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True,
    )

    payment_status = models.CharField(
        'وضعیت پرداخت',
        max_length=20,
        choices=Payment.PAYMENT_STATUS_CHOICES,
    )

    session = models.ForeignKey(
        ParkingSession,
        on_delete=models.SET_NULL,
        related_name='payment_histories',
        verbose_name='خودروی فعال',
        null=True,
        blank=True,
    )

    deleted_at = models.DateTimeField('زمان حذف', default=timezone.now)

    deleted_by = models.CharField(
        'حذف توسط',
        max_length=150,
        null=True,
        blank=True,
        help_text='نام کاربری فردی که پرداخت را حذف کرده است',
    )

    class Meta:
        verbose_name = 'تاریخچه پرداخت'
        verbose_name_plural = 'تاریخچه پرداخت‌ها'
        ordering = ['-deleted_at']

    def __str__(self):
        return f"History of payment #{self.original_id}"


class ReceiptHistory(models.Model):
    original_id = models.IntegerField("شناسه اصلی رسید")

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='مشتری',
    )

    issue_time = models.DateTimeField('زمان صدور رسید')
    receipt_number = models.CharField('شماره رسید', max_length=50)

    calculated_fee = models.DecimalField(
        'مبلغ روی رسید',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    session = models.ForeignKey(
        ParkingSession,
        on_delete=models.SET_NULL,
        related_name='receipt_histories',
        verbose_name='خودروی فعال',
        null=True,
        blank=True,
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        related_name='receipt_histories',
        verbose_name='پرداخت',
        null=True,
        blank=True,
    )

    content = models.TextField(
        'متن رسید',
        blank=True,
        null=True,
    )

    deleted_at = models.DateTimeField('زمان حذف', default=timezone.now)

    deleted_by = models.CharField(
        'حذف توسط',
        max_length=150,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'تاریخچه رسید'
        verbose_name_plural = 'تاریخچه رسیدها'
        ordering = ['-deleted_at']

    def __str__(self):
        return f"History of receipt #{self.receipt_number} (orig_id={self.original_id})"
