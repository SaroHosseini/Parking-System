from django.contrib import admin
from . import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe


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
        'created_at',
        'approved_at',
    ]
    list_filter = ['status', 'is_active', 'created_at']
    search_fields = ['name', 'owner_name', 'phone', 'email']
    readonly_fields = ['created_at', 'approved_at']
    list_editable = ['status']


@admin.register(models.CustomerUser)
class CustomerUserAdmin(admin.ModelAdmin):
    list_per_page = 20
    list_display = ['id', 'user', 'customer', 'role', 'is_active']
    list_filter = ['customer', 'role', 'is_active']
    search_fields = ['user__username', 'user__email', 'customer__name']


@admin.register(models.Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_per_page = 20
    list_display = ['id', 'customer', 'plate_number_display', 'owner_name', 'owner_phone', 'type', 'color']
    list_filter = ['customer', 'type', 'color']
    search_fields = ['plate_number', 'owner_name__istartswith', 'owner_phone', 'customer__name']
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
    list_display = ['id', 'customer', 'name', 'total_capacity']
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
        'entry_time',
        'exit_time',
        'total_duration_minutes',
        'status',
        'vehicle_preview',
        'spot',
        'calculated_fee',
    ]
    list_filter = ['vehicle__customer', 'status', 'spot__parking_lot', 'vehicle__type']
    search_fields = ['vehicle__plate_number', 'vehicle__owner_name', 'spot__code', 'vehicle__customer__name']
    readonly_fields = ['total_duration_minutes', 'calculated_fee']
    list_select_related = ['vehicle', 'vehicle__customer', 'spot', 'spot__parking_lot']

    def customer_display(self, obj):
        return obj.vehicle.customer if obj.vehicle else "-"

    customer_display.short_description = "مشتری"

    def vehicle_preview(self, obj):
        text = obj.__str__().replace("\n", "<br>")
        return mark_safe(text)

    vehicle_preview.short_description = 'وسیله نقلیه'


@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_per_page = 15
    list_display = [
        'id',
        'customer_display',
        'amount',
        'payment_time',
        'payment_method',
        'payment_status',
        'session',
    ]
    list_editable = ['payment_method', 'payment_status']
    list_filter = ['session__vehicle__customer', 'payment_method', 'payment_status', 'payment_time']
    search_fields = [
        'session__vehicle__plate_number',
        'session__vehicle__owner_name',
        'session__vehicle__owner_phone',
        'session__vehicle__customer__name',
    ]
    readonly_fields = ['amount', 'payment_time']
    list_select_related = ['session', 'session__vehicle', 'session__vehicle__customer']

    def customer_display(self, obj):
        return obj.session.vehicle.customer if obj.session and obj.session.vehicle else "-"

    customer_display.short_description = "مشتری"


@admin.register(models.Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_per_page = 15
    list_display = [
        'receipt_number',
        'customer_display',
        'issue_time',
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
        'session__vehicle__owner_name',
        'session__vehicle__customer__name',
        'payment__payment_method',
    ]
    readonly_fields = [
        'receipt_number',
        'issue_time',
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


# History Models

@admin.register(models.ParkingSessionHistory)
class ParkingSessionHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_id', 'customer', 'vehicle', 'parking_lot', 'parking_spot', 'deleted_at')
    list_filter = ['customer', 'deleted_at']
    search_fields = ['customer__name', 'vehicle__plate_number']


@admin.register(models.PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_id', 'customer', 'amount', 'payment_time', 'deleted_at')
    list_filter = ['customer', 'payment_status', 'deleted_at']
    search_fields = ['customer__name']


@admin.register(models.ReceiptHistory)
class ReceiptHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_id', 'customer', 'receipt_number', 'deleted_at')
    list_filter = ['customer', 'deleted_at']
    search_fields = ['customer__name', 'receipt_number']