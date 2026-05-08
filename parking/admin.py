from django.contrib import admin
from . import models 

@admin.register(models.Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    pass

@admin.register(models.ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    pass

@admin.register(models.ParkingSpot)
class ParkingSpotAdmin(admin.ModelAdmin):
    pass

@admin.register(models.Tariff)
class TarrifAdmin(admin.ModelAdmin):
    pass

@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    pass

@admin.register(models.Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    pass

@admin.register(models.ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    pass
