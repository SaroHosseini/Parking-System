from .models import Announcement, CustomerUser, ParkingLot


CURRENT_PARKING_LOT_SESSION_KEY = 'current_parking_lot_id'


def active_announcement(request):
    if not request.user.is_authenticated:
        return {}

    if request.user.is_staff or request.user.is_superuser:
        return {}

    announcement = (
        Announcement.objects
        .filter(is_active=True)
        .exclude(views__user=request.user)
        .order_by('-created_at')
        .first()
    )

    return {
        'active_announcement': announcement,
    }


def parking_scope(request):
    if not request.user.is_authenticated:
        return {}

    try:
        profile = request.user.customer_profile
    except CustomerUser.DoesNotExist:
        return {}

    if profile.role == CustomerUser.ROLE_OPERATOR:
        return {
            'current_parking_lot': profile.parking_lot,
            'topbar_parking_lots': ParkingLot.objects.none(),
            'can_switch_parking_lot': False,
        }

    if profile.role != CustomerUser.ROLE_OWNER:
        return {}

    parking_lots = ParkingLot.objects.filter(
        customer=profile.customer,
    ).order_by('name')

    selected_id = request.session.get(CURRENT_PARKING_LOT_SESSION_KEY)
    selected_parking_lot = None

    if selected_id:
        selected_parking_lot = parking_lots.filter(pk=selected_id).first()

    if selected_parking_lot is None:
        selected_parking_lot = parking_lots.first()

        if selected_parking_lot:
            request.session[CURRENT_PARKING_LOT_SESSION_KEY] = selected_parking_lot.pk

    return {
        'current_parking_lot': selected_parking_lot,
        'topbar_parking_lots': parking_lots,
        'can_switch_parking_lot': parking_lots.exists(),
    }
