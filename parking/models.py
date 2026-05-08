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
        default=VEHICLE_TYPE_CAR,
    )

    color = models.CharField("رنگ", max_length=30, blank=True)

    def __str__(self):
        return f"{self.plate_number} \n {self.owner_name or 'بدون نام'}"
    
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
            
    class Meta:
        verbose_name = 'وسیله نقلیه'
        verbose_name_plural = 'وسایل نقلیه'          
        ordering = ['owner_name', 'plate_number']
        
    
class ParkingLot(models.Model):

    name = models.CharField("نام پارکینگ", max_length=100)
    total_capacity = models.PositiveIntegerField("ظرفیت کل")

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
        verbose_name = 'پارکینگ'
        verbose_name_plural = 'پارکینگ ها '
        

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
        ordering = ['parking_lot', 'level', 'code']
    

    def __str__(self):
        status = "🟢 آزاد در حال حاضر" if not self.is_occupied else "🔴 اشغال در حال حاضر"
        return f" {self.code} – طبقه {self.level} – {status}"
    


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
        ordering = ['vehicle_type', 'name']

    def __str__(self):
        return f"{self.name} - {self.get_vehicle_type_display()}"



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

    amount = models.DecimalField('مقدار', max_digits=10, decimal_places=2)
    payment_time = models.DateTimeField('زمان پرداخت', auto_now_add=True)
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
        'ParkingSession',
        on_delete=models.SET_NULL,
        related_name='payments',
        verbose_name='سشن پارک',
        null=True
    )

    class Meta:
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت‌ها'
        ordering = ['-payment_time']

    def __str__(self):
        return f"پرداخت #{self.id} - {self.amount} - {self.get_payment_method_display()}"
    
    def save(self, *args, **kwargs):
        if self.payment_method and self.payment_status == Payment.PAYMENT_STATUS_OPEN:
            self.payment_status = Payment.PAYMENT_STATUS_CLOSED
        super().save(*args, **kwargs)

        if self.session:
            try_create_receipt(self.session)




class Receipt(models.Model):

    archived_vehicle_plate = models.CharField("شماره پلاک آرشیوی", max_length=20, blank=True, null=True)
    archived_spot_code = models.CharField("کد جایگاه آرشیوی", max_length=50, blank=True, null=True)

    archived_entry_time = models.DateTimeField("زمان ورود آرشیوی", null=True, blank=True)
    archived_exit_time = models.DateTimeField("زمان خروج آرشیوی", null=True, blank=True)

    archived_payment_method = models.CharField("روش پرداخت آرشیوی", max_length=50, blank=True, null=True)
    archived_payment_status = models.CharField("وضعیت پرداخت آرشیوی", max_length=20, blank=True, null=True)

    issue_time = models.DateTimeField('زمان صدور رسید', default=timezone.now)
    receipt_number = models.CharField(
        'شماره رسید',
        max_length=50,
        unique=True,
        editable=False,
        blank=True
    )
    
    calculated_fee = models.DecimalField(
        'مبلغ روی رسید',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    session = models.OneToOneField(
        'ParkingSession',
        on_delete=models.SET_NULL,
        related_name='receipt',
        verbose_name='سشن پارک',
        null=True
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
        return f"رسید #{self.receipt_number}"

    def generate_receipt_number(self):
        return timezone.now().strftime("%H%M%S")

    def generate_content(self):
        entry = self.archived_entry_time
        exit_time = self.archived_exit_time

        entry_str = entry.strftime('%Y-%m-%d %H:%M') if entry else "نامشخص"
        exit_str = exit_time.strftime('%Y-%m-%d %H:%M') if exit_time else "نامشخص"

        lines = [
            f"شماره رسید: {self.receipt_number}",
            f"زمان ورود: {entry_str}",
            f"زمان خروج: {exit_str}",
            f"شماره پلاک: {self.archived_vehicle_plate or 'نامشخص'}",
            f"کد جایگاه: {self.archived_spot_code or 'نامشخص'}",
            f"وضعیت پرداخت: {self.archived_payment_status or 'پرداخت حذف شده'}",
            f"روش پرداخت: {self.archived_payment_method or 'پرداخت حذف شده'}",
            f"مبلغ قابل پرداخت: {self.calculated_fee} تومان",
        ]

        if not self.session:
            lines.append("سشن: حذف شده")

        if not self.payment:
            lines.append("پرداخت: حذف شده")

        return "\n".join(lines)


    def save(self, *args, **kwargs):
        session = self.session
        payment = self.payment

        if self.calculated_fee is None:
            if session and session.calculated_fee is not None:
                self.calculated_fee = session.calculated_fee
            elif session:
                self.calculated_fee = session.calculate_fee()
            else:
                self.calculated_fee = Decimal("0.00")

        if session:
            self.archived_vehicle_plate = session.vehicle.plate_number if session.vehicle else "نامشخص"
            self.archived_spot_code = session.spot.code if session.spot else "نامشخص"
            self.archived_entry_time = session.entry_time
            self.archived_exit_time = session.exit_time

        if payment:
            self.archived_payment_method = payment.get_payment_method_display()
            self.archived_payment_status = payment.get_payment_status_display()

        if not self.receipt_number:
            self.receipt_number = self.generate_receipt_number()

        self.content = self.generate_content()

        super().save(*args, **kwargs)


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
        help_text="بعد از خروج محاسبه و ذخیره می‌شود."
    )
    status = models.CharField(
        "وضعیت",
        choices=STATUS_CHOICES,
        max_length=20,
        default=SESSION_STATUS_OPEN
    )
    vehicle = models.ForeignKey(
        Vehicle, 
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name='وسیله نقلیه'
    )
    spot = models.ForeignKey(
        ParkingSpot,
        on_delete=models.PROTECT,
        related_name='sessions',
        verbose_name='جایگاه'
    )
    calculated_fee = models.DecimalField(
        "هزینه محاسبه‌شده",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='پس از ثبت خروج خودکار محاسبه می‌شود'
    )

    class Meta:
        verbose_name = "سشن پارک"
        verbose_name_plural = "سشن‌های پارک"
        ordering = ['-entry_time']

    def calculate_duration(self):
        if self.entry_time and self.exit_time:
            duration = self.exit_time - self.entry_time
            minutes = math.ceil(duration.total_seconds() / 60)
            return max(minutes, 1)
        return None

    def get_applicable_tariff(self):
        return Tariff.objects.filter(
            vehicle_type=self.vehicle.type,
            is_active=True
        ).first()

    def calculate_fee(self):
        if self.total_duration_minutes is None:
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
        is_new = self.pk is None
        old_exit = None
        old_spot = None

        if not is_new:
            old_obj = ParkingSession.objects.filter(pk=self.pk).first()
            if old_obj:
                old_exit = old_obj.exit_time
                old_spot = old_obj.spot

        if is_new and self.spot.is_occupied:
            raise ValidationError(f"جایگاه {self.spot.code} در حال حاضر اشغال است!")


        if self.exit_time and old_exit is None:
            self.total_duration_minutes = self.calculate_duration()
            self.calculated_fee = self.calculate_fee()
            self.status = self.SESSION_STATUS_CLOSED

        super().save(*args, **kwargs)


        if old_spot and old_spot != self.spot:
            old_spot.is_occupied = False
            old_spot.save(update_fields=["is_occupied"])


        if is_new:
            self.spot.is_occupied = True
            self.spot.save(update_fields=["is_occupied"])


        if self.exit_time and old_exit is None:
            self.spot.is_occupied = False
            self.spot.save(update_fields=["is_occupied"])

            if not Payment.objects.filter(session=self).exists():
                Payment.objects.create(
                    session=self,
                    amount=self.calculated_fee,
                    payment_status=Payment.PAYMENT_STATUS_OPEN,
                )

        try_create_receipt(self)


    def __str__(self):
        vehicle_plate = self.vehicle.plate_number if self.vehicle else "نامشخص"

        return f"پلاک: {vehicle_plate} \n مالک: {self.vehicle.owner_name}"




def try_create_receipt(session):
    if not session:
        return

    if session.status != ParkingSession.SESSION_STATUS_CLOSED or not session.exit_time:
        return

    if Receipt.objects.filter(session=session).exists():
        return

    payment = Payment.objects.filter(
        session=session,
        payment_status=Payment.PAYMENT_STATUS_CLOSED
    ).order_by("-payment_time").first()

    if not payment:
        return

    receipt_number = timezone.now().strftime("%H%M%S")

    Receipt.objects.create(
        session=session,
        payment=payment,
        calculated_fee=payment.amount,
        receipt_number=receipt_number,
    )

