from .models import Announcement


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
