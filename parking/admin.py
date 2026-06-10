from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from . import models
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .templatetags.date_filters import jalali_gregorian


def admin_dual_datetime(value):
    if not value:
        return "-"

    return jalali_gregorian(value)


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class ParkinoUserAdmin(DjangoUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
        'last_login_display',
        'date_joined_display',
    )
    readonly_fields = DjangoUserAdmin.readonly_fields + ('last_login_display', 'date_joined_display')

    def last_login_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'last_login', None))

    last_login_display.short_description = 'آخرین ورود'

    def date_joined_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'date_joined', None))

    date_joined_display.short_description = 'زمان عضویت'


@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_per_page = 20
    list_display = [
        'id',
        'name',
        'owner_name',
        'phone',
        'email',
        'status',
        'is_active',
        'created_at_display',
        'approved_at_display',
    ]
    list_filter = ['status', 'is_active', 'created_at']
    search_fields = ['name', 'owner_name', 'phone', 'email']
    readonly_fields = ['created_at', 'approved_at', 'created_at_display', 'approved_at_display']
    list_editable = ['status']

    def created_at_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'created_at', None))

    created_at_display.short_description = 'زمان ثبت'

    def approved_at_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'approved_at', None))

    approved_at_display.short_description = 'زمان تایید'


@admin.register(models.CustomerUser)
class CustomerUserAdmin(admin.ModelAdmin):
    list_per_page = 20
    list_display = ['id', 'user', 'customer', 'role', 'parking_lot', 'is_active', 'password_change_link']
    list_filter = ['customer', 'role', 'parking_lot', 'is_active']
    search_fields = ['user__username', 'user__email', 'customer__name', 'parking_lot__name']
    list_select_related = ['user', 'customer', 'parking_lot']
    readonly_fields = ['password_change_link']
    fields = ['user', 'customer', 'role', 'parking_lot', 'is_active', 'password_change_link']

    def password_change_link(self, obj):
        if not obj or not obj.user_id:
            return "-"

        url = reverse('admin:auth_user_password_change', args=[obj.user_id])
        return format_html('<a href="{}">تغییر رمز کاربر</a>', url)

    password_change_link.short_description = "تغییر رمز"


@admin.register(models.Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_per_page = 20
    list_display = ['id', 'customer', 'plate_number_display','type', 'color']
    list_filter = ['customer', 'type', 'color']
    search_fields = ['plate_number','customer__name']
    list_select_related = ['customer']

    def plate_number_display(self, obj):
        return format_html(
            "<span style='direction:rtl; unicode-bidi:embed;'>{}</span>",
            obj.plate_number
        )

    plate_number_display.short_description = "پلاک"


class ParkingSpotInline(admin.TabularInline):
    model = models.ParkingSpot
    extra = 2
    fields = ['code', 'level', 'is_occupied']
    readonly_fields = ['is_occupied']


@admin.register(models.ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'name', 'floor_count', 'total_capacity']
    list_filter = ['customer']
    search_fields = ['name', 'customer__name']
    list_select_related = ['customer']
    inlines = [ParkingSpotInline]


@admin.register(models.ParkingSpot)
class ParkingSpotAdmin(admin.ModelAdmin):
    list_per_page = 30
    list_display = ['id', 'parking_lot', 'customer_display', 'code', 'level', 'is_occupied']
    list_filter = ['parking_lot__customer', 'parking_lot', 'level', 'is_occupied']
    search_fields = ['parking_lot__customer__name', 'parking_lot__name', 'code', 'level']
    list_select_related = ['parking_lot', 'parking_lot__customer']

    def customer_display(self, obj):
        return obj.parking_lot.customer

    customer_display.short_description = "مشتری"


@admin.register(models.Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = [
        'customer',
        'name',
        'vehicle_type',
        'is_active',
        'first_hour_price',
        'additional_hour_price',
        'daily_price',
    ]
    list_editable = ['first_hour_price', 'additional_hour_price', 'daily_price', 'is_active']
    list_filter = ['customer', 'vehicle_type', 'is_active']
    search_fields = ['name', 'customer__name']
    list_select_related = ['customer']


@admin.register(models.ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    list_per_page = 15
    list_display = [
        'id',
        'customer_display',
        'entry_time_display',
        'exit_time_display',
        'total_duration_minutes',
        'status',
        'vehicle_preview',
        'spot',
        'calculated_fee',
    ]
    list_filter = ['vehicle__customer', 'status', 'spot__parking_lot', 'vehicle__type']
    search_fields = ['vehicle__plate_number','spot__code', 'vehicle__customer__name']
    readonly_fields = ['entry_time_display', 'exit_time_display', 'total_duration_minutes', 'calculated_fee']
    list_select_related = ['vehicle', 'vehicle__customer', 'spot', 'spot__parking_lot']

    def customer_display(self, obj):
        return obj.vehicle.customer if obj.vehicle else "-"

    customer_display.short_description = "مشتری"

    def vehicle_preview(self, obj):
        text = obj.__str__().replace("\n", "<br>")
        return mark_safe(text)

    vehicle_preview.short_description = 'وسیله نقلیه'

    def entry_time_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'entry_time', None))

    entry_time_display.short_description = 'زمان ورود'

    def exit_time_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'exit_time', None))

    exit_time_display.short_description = 'زمان خروج'


@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_per_page = 15
    list_display = [
        'id',
        'customer_display',
        'amount',
        'payment_time_display',
        'payment_method',
        'payment_status',
        'session',
    ]
    list_editable = ['payment_method', 'payment_status']
    list_filter = ['session__vehicle__customer', 'payment_method', 'payment_status', 'payment_time']
    search_fields = [
        'session__vehicle__plate_number',
        'session__vehicle__customer__name',
    ]
    readonly_fields = ['amount', 'payment_time', 'payment_time_display']
    list_select_related = ['session', 'session__vehicle', 'session__vehicle__customer']

    def customer_display(self, obj):
        return obj.session.vehicle.customer if obj.session and obj.session.vehicle else "-"

    customer_display.short_description = "مشتری"

    def payment_time_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'payment_time', None))

    payment_time_display.short_description = 'زمان پرداخت'


@admin.register(models.Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_per_page = 15
    list_display = [
        'receipt_number',
        'customer_display',
        'issue_time_display',
        'session',
        'payment',
        'receipt_preview',
    ]
    list_filter = [
        'session__vehicle__customer',
        'issue_time',
        'payment__payment_method',
        'payment__payment_status',
    ]
    search_fields = [
        'receipt_number',
        'session__vehicle__plate_number',
        'session__vehicle__customer__name',
        'payment__payment_method',
    ]
    readonly_fields = [
        'receipt_number',
        'issue_time',
        'issue_time_display',
        'calculated_fee',
        'content',
        'receipt_preview',
    ]
    list_select_related = ['payment', 'session', 'session__vehicle', 'session__vehicle__customer']

    def customer_display(self, obj):
        return obj.session.vehicle.customer if obj.session and obj.session.vehicle else "-"

    customer_display.short_description = "مشتری"

    def receipt_preview(self, obj):
        text = obj.generate_content().replace("\n", "<br>")
        return mark_safe(text)

    receipt_preview.short_description = "متن رسید"

    def issue_time_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'issue_time', None))

    issue_time_display.short_description = 'زمان صدور'


@admin.register(models.BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'subject',
        'customer',
        'username',
        'role',
        'phone',
        'status',
        'created_at_display',
    ]
    list_filter = ['status', 'customer', 'role', 'created_at']
    search_fields = ['subject', 'description', 'username', 'phone', 'customer__name']
    readonly_fields = [
        'customer',
        'user',
        'username',
        'role',
        'phone',
        'subject',
        'description',
        'created_at',
        'updated_at',
        'created_at_display',
        'updated_at_display',
    ]
    list_select_related = ['customer', 'user']
    list_editable = ['status']
    list_per_page = 20

    def created_at_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'created_at', None))

    created_at_display.short_description = 'زمان ثبت'

    def updated_at_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'updated_at', None))

    updated_at_display.short_description = 'آخرین بروزرسانی'


@admin.register(models.Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'title',
        'is_active',
        'created_at_display',
        'updated_at_display',
        'seen_count',
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_active']
    readonly_fields = [
        'created_at',
        'updated_at',
        'created_at_display',
        'updated_at_display',
        'seen_count',
    ]
    fields = [
        'title',
        'description',
        'is_active',
        'seen_count',
        'created_at_display',
        'updated_at_display',
    ]
    list_per_page = 20

    def created_at_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'created_at', None))

    created_at_display.short_description = 'زمان ایجاد'

    def updated_at_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'updated_at', None))

    updated_at_display.short_description = 'آخرین بروزرسانی'

    def seen_count(self, obj):
        if not obj or not obj.pk:
            return 0

        return obj.views.count()

    seen_count.short_description = 'تعداد مشاهده'


@admin.register(models.AnnouncementView)
class AnnouncementViewAdmin(admin.ModelAdmin):
    list_display = ['id', 'announcement', 'user', 'seen_at_display']
    list_filter = ['announcement', 'seen_at']
    search_fields = ['announcement__title', 'user__username']
    readonly_fields = ['announcement', 'user', 'seen_at', 'seen_at_display']
    list_select_related = ['announcement', 'user']
    list_per_page = 30

    def seen_at_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'seen_at', None))

    seen_at_display.short_description = 'زمان مشاهده'


# History Models

@admin.register(models.ParkingSessionHistory)
class ParkingSessionHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_id', 'customer', 'vehicle', 'parking_lot', 'parking_spot', 'deleted_at_display')
    list_filter = ['customer', 'deleted_at']
    search_fields = ['customer__name', 'vehicle__plate_number']

    def deleted_at_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'deleted_at', None))

    deleted_at_display.short_description = 'زمان حذف'


@admin.register(models.PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_id', 'customer', 'amount', 'payment_time_display', 'deleted_at_display')
    list_filter = ['customer', 'payment_status', 'deleted_at']
    search_fields = ['customer__name']

    def payment_time_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'payment_time', None))

    payment_time_display.short_description = 'زمان پرداخت'

    def deleted_at_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'deleted_at', None))

    deleted_at_display.short_description = 'زمان حذف'


@admin.register(models.ReceiptHistory)
class ReceiptHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_id', 'customer', 'receipt_number', 'issue_time_display', 'deleted_at_display')
    list_filter = ['customer', 'deleted_at']
    search_fields = ['customer__name', 'receipt_number']

    def issue_time_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'issue_time', None))

    issue_time_display.short_description = 'زمان صدور'

    def deleted_at_display(self, obj):
        return admin_dual_datetime(getattr(obj, 'deleted_at', None))

    deleted_at_display.short_description = 'زمان حذف'
