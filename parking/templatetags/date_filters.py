import re

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


@register.filter
def jalali_date_value(value):
    if not value:
        return ""

    jalali_date = jdatetime.date.fromgregorian(date=value)
    return jalali_date.strftime("%Y/%m/%d")


@register.filter
def plate_parts(value, vehicle_type=""):
    raw = str(value or "").strip()

    if not raw:
        return {
            "kind": "unknown",
            "raw": "-",
        }

    if vehicle_type == "motorcycle" or re.fullmatch(r"\d{8}", raw):
        return {
            "kind": "motorcycle",
            "raw": raw,
            "number": raw,
        }

    match = re.fullmatch(r"(\d{2})(.+?)(\d{3})-(\d{2})", raw)
    if match:
        return {
            "kind": "car",
            "raw": raw,
            "first": match.group(1),
            "letter": match.group(2),
            "middle": match.group(3),
            "region": match.group(4),
        }

    legacy_match = re.fullmatch(r"(\d{2})-(\d{3})(.+?)(\d{2})", raw)
    if legacy_match:
        return {
            "kind": "car",
            "raw": raw,
            "first": legacy_match.group(4),
            "letter": legacy_match.group(3),
            "middle": legacy_match.group(2),
            "region": legacy_match.group(1),
        }

    return {
        "kind": "unknown",
        "raw": raw,
    }
