from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    ParkingSession,
    Payment,
    Receipt,
    ParkingSessionHistory,
    PaymentHistory,
    ReceiptHistory,
)


def local_now():
    return timezone.localtime(timezone.now())


@receiver(pre_delete, sender=ParkingSession)
def save_parking_session_history(sender, instance, **kwargs):
    ParkingSessionHistory.objects.create(
        original_id=instance.id,
        customer=instance.vehicle.customer if instance.vehicle else None,
        vehicle=instance.vehicle,
        parking_lot=instance.spot.parking_lot if instance.spot else None,
        parking_spot=instance.spot if instance.spot else None,
        entry_time=instance.entry_time,
        exit_time=instance.exit_time,
        status=instance.status,
        calculated_fee=instance.calculated_fee,
        deleted_at=local_now(),
    )

    if instance.spot:
        other_open_session_exists = ParkingSession.objects.filter(
            spot=instance.spot,
            status=ParkingSession.SESSION_STATUS_OPEN
        ).exclude(pk=instance.pk).exists()

        if not other_open_session_exists:
            instance.spot.is_occupied = False
            instance.spot.save(update_fields=["is_occupied"])

@receiver(pre_delete, sender=Payment)
def save_payment_history(sender, instance, **kwargs):
    PaymentHistory.objects.create(
        original_id=instance.id,
        customer=instance.session.vehicle.customer if instance.session and instance.session.vehicle else None,
        amount=instance.amount,
        payment_time=instance.payment_time,
        payment_method=instance.payment_method,
        payment_status=instance.payment_status,
        session=instance.session,
        deleted_at=local_now(),
    )


@receiver(pre_delete, sender=Receipt)
def save_receipt_history(sender, instance, **kwargs):
    ReceiptHistory.objects.create(
        original_id=instance.id,
        customer=instance.session.vehicle.customer if instance.session and instance.session.vehicle else None,
        issue_time=instance.issue_time,
        receipt_number=instance.receipt_number,
        calculated_fee=instance.calculated_fee,
        session=instance.session,
        payment=instance.payment,
        content=instance.content,
        deleted_at=local_now(),
    )