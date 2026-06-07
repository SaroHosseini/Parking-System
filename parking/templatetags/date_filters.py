import jdatetime

from django import template
from django.utils import timezone


register = template.Library()


@register.filter
def jalali_gregorian(value):
    if not value:
        return "-"

    local_value = timezone.localtime(value)

    jalali_date = jdatetime.datetime.fromgregorian(datetime=local_value)

    jalali_str = jalali_date.strftime("%Y/%m/%d - %H:%M")
    gregorian_str = local_value.strftime("%Y/%m/%d - %H:%M")

    return f"{jalali_str} شمسی | {gregorian_str} میلادی"


@register.filter
def jalali_gregorian_date(value):
    if not value:
        return "-"

    jalali_date = jdatetime.date.fromgregorian(date=value)

    jalali_str = jalali_date.strftime("%Y/%m/%d")
    gregorian_str = value.strftime("%Y/%m/%d")

    return f"{jalali_str} شمسی | {gregorian_str} میلادی"