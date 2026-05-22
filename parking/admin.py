from django.contrib import admin
from . import models 
from django.utils.html import format_html
from django.utils.safestring import mark_safe


@admin.register(models.Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_per_page = 20
    list_display = ['id', 'plate_number_display', 'owner_name', 'owner_phone', 'type', 'color']
    list_filter = ['type', 'color']
    search_fields = ['plate_number', 'owner_name__istartswith', 'owner_phone']

    def plate_number_display(self, obj):
        return format_html("<span style='direction:rtl; unicode-bidi:embed;'>{}</span>", obj.plate_number)

    plate_number_display.short_description = "پلاک"


class ParkingSpotInline(admin.TabularInline):
    model = models.ParkingSpot
    extra = 2
    fields = ['code', 'level', 'is_occupied']
    readonly_fields = ['is_occupied']


@admin.register(models.ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'total_capacity']
    search_fields = ['name']
    inlines = [ParkingSpotInline]


@admin.register(models.ParkingSpot)
class ParkingSpotAdmin(admin.ModelAdmin):
    list_per_page = 30
    list_display = ['id', 'parking_lot', 'code', 'level','is_occupied']
    list_filter = ['parking_lot', 'level','is_occupied']
    search_fields = ['parking_lot__name', 'code', 'level']


@admin.register(models.Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ['name', 'vehicle_type', 'is_active', 'first_hour_price', 'additional_hour_price', 'daily_price']
    list_editable = ['first_hour_price', 'additional_hour_price', 'daily_price', 'is_active']
    list_filter = ['vehicle_type', 'is_active']
    search_fields = ['name']

@admin.register(models.ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    list_per_page = 15
    list_display = [
        'id', 'entry_time', 'exit_time',
        'total_duration_minutes', 'status',
        'vehicle_preview', 'spot', 'calculated_fee'
    ]

    def vehicle_preview(self, obj):
        text = obj.__str__().replace("\n", "<br>")
        return mark_safe(text)

    vehicle_preview.short_description = 'وسیله نقلیه'   


@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_per_page = 15
    list_display = ['id', 'amount', 'payment_time', 'payment_method',
                    'payment_status', 'session']  
             
    list_editable = ['payment_method', 'payment_status']
    list_filter = ['payment_method', 'payment_status']
    list_select_related = ['session', 'session__vehicle']

@admin.register(models.Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'issue_time', 'session', 'payment', 'receipt_preview']
    list_select_related = ['payment', 'session__vehicle']
    readonly_fields = ['receipt_number', 'content', 'issue_time']
    search_fields = ['receipt_number', 'session__vehicle__plate_number']

    def receipt_preview(self, obj):
        text = obj.generate_content().replace("\n", "<br>")
        return mark_safe(text)

    receipt_preview.short_description = "متن رسید"

    def content(self, obj):
        return obj.generate_content()
    content.short_description = "متن رسید"

#History Models    
@admin.register(models.ParkingSessionHistory)
class ParkingSessionHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_id', 'vehicle', 'parking_lot', 'parking_spot', 'deleted_at')

@admin.register(models.PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_id', 'amount', 'payment_time', 'deleted_at')

@admin.register(models.ReceiptHistory)
class ReceiptHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_id', 'receipt_number', 'deleted_at')
