import math
from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import RegexValidator

PERSIAN_PLATE_LETTERS = "ابپتثجچحخدذرزسشصضطظعغفقکگلمنوهی"


car_plate_validator = RegexValidator(
    regex=r'^[0-9]{2}[' + PERSIAN_PLATE_LETTERS + r'][0-9]{3}-[0-9]{2}$',
    message=(
        "فرمت پلاک خودرو نامعتبر است. نمونه صحیح: 12ب345-67 "
        "(دو رقم، یک حرف فارسی، سه رقم، خط تیره، دو رقم)."
    ),
)
motorcycle_plate_validator = RegexValidator(
    regex=r'^[0-9]{8}$',
    message="پلاک موتورسیکلت باید دقیقا ۸ رقم باشد.",
)


class Vehicle(models.Model):
    VEHICLE_TYPE_CAR = 'car'
    VEHICLE_TYPE_MOTORCYCLE = 'motorcycle'
    VEHICLE_TYPE_TRUCK = 'truck'

    VEHICLE_TYPE_CHOICES = [
        (VEHICLE_TYPE_CAR, 'سواری'),
        (VEHICLE_TYPE_MOTORCYCLE, 'موتورسیکلت'),
        (VEHICLE_TYPE_TRUCK, 'وانت/کامیون'),
                            ]
    
    plate_number = models.CharField(
        "شماره پلاک",
        max_length=15,
        unique=True,
        help_text="مثال: برای خودرو: 12ب345-67 ، برای موتور: 8 رقم",
    )
    owner_name = models.CharField("نام مالک", max_length=100, blank=True)
    owner_phone = models.CharField("تلفن مالک", max_length=11, blank=True)

    type = models.CharField(
        "نوع وسیله",
        max_length=20,
        choices=VEHICLE_TYPE_CHOICES,
        default='car',
    )
    color = models.CharField("رنگ", max_length=30, blank=True)

    def __str__(self):
        return f"{self.plate_number} - {self.owner_name or 'بدون نام'}"
    
    def clean(self):

        super().clean()

        plate = (self.plate_number or "").strip()

        
        if self.type == 'car':
            try:
                car_plate_validator(plate)
            except ValidationError as e:
                raise ValidationError({'plate_number' : e.message})
            
        elif self.type == 'motorcycle':
            try:
                motorcycle_plate_validator(plate)
            except ValidationError as e:
                raise ValidationError({'plate_number' : e.message})
        
    
class ParkingLot(models.Model):

    name = models.CharField("نام پارکینگ", max_length=100)
    total_capacity = models.PositiveIntegerField("ظرفیت کل")

    def __str__(self):
        return self.name
    

class ParkingSpot(models.Model):
    parking_lot = models.ForeignKey(
    ParkingLot,
    on_delete=models.CASCADE,
    related_name="spots",
    verbose_name="پارکینگ",
    )
    code = models.CharField('کد محل', max_length=255)
    level = models.CharField('طبقه', max_length=255)
    is_occupied = models.BooleanField("اشغال است؟", default=False)

    class Meta:
        unique_together = ("parking_lot", "code")
        verbose_name = "جایگاه پارک"
        verbose_name_plural = "جایگاه‌های پارک"

    def __str__(self):
        return f" کد جایگاه: {self.code} طبقه جایگاه: {self.level} وضعیت فعلی جایگاه: {self.is_occupied}"

class Tariff(models.Model):

    VEHICLE_TYPE_CAR = 'car'
    VEHICLE_TYPE_MOTORCYCLE = 'motorcycle'
    VEHICLE_TYPE_TRUCK = 'truck'

    VEHICLE_TYPE_CHOICES = [
        (VEHICLE_TYPE_CAR, 'سواری'),
        (VEHICLE_TYPE_MOTORCYCLE, 'موتورسیکلت'),
        (VEHICLE_TYPE_TRUCK, 'وانت/کامیون'),
                            ]


    name = models.CharField("نام تعرفه", max_length=100)
    vehicle_type = models.CharField(
        "نوع وسیله نقلیه",
        max_length=20,
        choices=VEHICLE_TYPE_CHOICES,
        default='car',
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
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "تعرفه"
        verbose_name_plural = "تعرفه‌ها"

    def __str__(self):
        return f"{self.name} - {self.get_vehicle_type_display()}"


class ParkingSession(models.Model):
    SESSION_STATUS_OPEN = 'open'
    SESSION_STATUS_CLOSED = 'closed'
    SESSION_STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (SESSION_STATUS_OPEN, "باز (در حال پارک)"),
        (SESSION_STATUS_CLOSED, 'بسته (خارج شده)'),
        (SESSION_STATUS_CANCELLED, 'لغو شده'),
                    ]

    entry_time = models.DateTimeField(default=timezone.now)
    exit_time = models.DateTimeField(null=True, blank=True)

    total_duration_minutes = models.PositiveIntegerField(
        "مدت کل (دقیقه)",
        null=True,
        blank=True,
        help_text="بعد از خروج محاسبه و ذخیره می‌شود.",
    )
    status = models.CharField(
        'وضعیت',
        choices=STATUS_CHOICES,
        max_length=255,
        default='open',)
    

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name='وسیله نقلیه')
    
    spot = models.ForeignKey(
        ParkingSpot,
        on_delete=models.PROTECT,
        related_name='sessions',
        verbose_name='جایگاه')
    
    calculated_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    class Meta:
        verbose_name = "سشن پارک"
        verbose_name_plural = "سشن‌های پارک"

    def calculate_duration(self):

        if self.entry_time and self.exit_time:
            duration = self.exit_time - self.entry_time
            minutes = int(duration.total_seconds() / 60)

            return max(minutes, 0)
        return None
    

    def get_applicable_tariff(self):

        return Tariff.objects.filter(
            vehicle_type= self.vehicle.type,
            is_active=True,
        ).first()


    def calculate_fee(self):

        if not self.total_duration_minutes:
            return Decimal("0.00")

        tariff = self.get_applicable_tariff()
        if not tariff:
            return Decimal("0.00")

        total_hours = math.ceil(self.total_duration_minutes / 60)

        if total_hours <= 1:
            return tariff.first_hour_price

        extra_hours = total_hours - 1
        return tariff.first_hour_price + (
            Decimal(extra_hours) * tariff.additional_hour_price
        )
    def save(self, *args, **kwargs):

        if self.exit_time:
            self.total_duration_minutes = self.calculate_duration()
            self.calculated_fee = self.calculate_fee()
            self.status = "closed"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"سشن #{self.id} - {self.vehicle.plate_number}"
    