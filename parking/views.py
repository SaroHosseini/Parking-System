import random
import re
from urllib.parse import urlparse

from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Sum, Avg, Count, Q, Exists, OuterRef
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth import update_session_auth_hash
from datetime import timedelta
from django.urls import Resolver404, resolve, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .models import (
    ParkingSpot,
    ParkingSession,
    Payment,
    Customer,
    CustomerUser,
    Vehicle,
    ParkingLot,
    Tariff,
    Receipt,
    BugReport,
    Announcement,
    AnnouncementView,
)

from .forms import (
    CustomerRequestForm,
    ParkingLotForm,
    ParkingSpotForm,
    TariffForm,
    ParkingSessionEntryForm,
    PaymentForm,
    ReportFilterForm,
    CustomerUserCreateForm,
    CustomerUserUpdateForm,
    ParkingSpotFilterForm,
    TariffFilterForm,
    ParkingSessionFilterForm,
    PaymentFilterForm,
    ReceiptFilterForm,
    CustomerUserFilterForm,
    CustomerUserPasswordForm,
    AccountPasswordChangeForm,
    CustomerSettingsForm,
    ParkingSpotAutoGenerateForm,
    BugReportForm,
)


def get_user_profile(user):
    if not user.is_authenticated:
        return None

    if user.is_superuser or user.is_staff:
        return None

    try:
        return user.customer_profile
    except CustomerUser.DoesNotExist:
        return None


def get_user_customer(user):
    profile = get_user_profile(user)

    if profile is None:
        return None

    if not profile.is_active:
        return None

    if not profile.customer.is_active:
        return None

    return profile.customer


def site_url(path=''):
    return f"{settings.SITE_URL}{path}"


def robots_txt(request):
    content = '\n'.join([
        'User-agent: *',
        'Allow: /',
        'Disallow: /dashboard/',
        'Disallow: /sessions/',
        'Disallow: /payments/',
        'Disallow: /receipts/',
        'Disallow: /reports/',
        'Disallow: /users/',
        'Disallow: /settings/',
        f'Sitemap: {site_url("/sitemap.xml")}',
        '',
    ])
    return HttpResponse(content, content_type='text/plain; charset=utf-8')


def sitemap_xml(request):
    today = timezone.localdate().isoformat()
    urls = [
        {
            'loc': site_url(reverse('parking:home')),
            'priority': '1.0',
            'changefreq': 'weekly',
        },
        {
            'loc': site_url(reverse('parking:customer_request')),
            'priority': '0.8',
            'changefreq': 'monthly',
        },
        {
            'loc': site_url(reverse('parking:login')),
            'priority': '0.6',
            'changefreq': 'monthly',
        },
    ]
    urlset = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for row in urls:
        urlset.extend([
            '  <url>',
            f'    <loc>{row["loc"]}</loc>',
            f'    <lastmod>{today}</lastmod>',
            f'    <changefreq>{row["changefreq"]}</changefreq>',
            f'    <priority>{row["priority"]}</priority>',
            '  </url>',
        ])

    urlset.append('</urlset>')
    return HttpResponse('\n'.join(urlset), content_type='application/xml; charset=utf-8')


def custom_page_not_found(request, exception=None, unmatched_path=None):
    return render(request, 'parking/404.html', status=404)


def custom_bad_request(request, exception=None):
    return render(request, 'parking/400.html', status=400)


def custom_permission_denied(request, exception=None):
    return render(request, 'parking/403.html', status=403)


def custom_server_error(request):
    return render(request, 'parking/500.html', status=500)


@require_POST
def bug_report_create(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            'ok': False,
            'message': 'برای ثبت گزارش مشکل ابتدا وارد حساب کاربری شوید.',
        }, status=403)

    customer = get_user_customer(request.user)

    if customer is None:
        return JsonResponse({
            'ok': False,
            'message': 'حساب کاربری شما برای ثبت گزارش مشکل فعال نیست.',
        }, status=403)

    form = BugReportForm(request.POST)

    if not form.is_valid():
        return JsonResponse({
            'ok': False,
            'message': 'اطلاعات فرم را کامل و درست وارد کنید.',
            'errors': {
                field: [str(error) for error in errors]
                for field, errors in form.errors.items()
            },
        }, status=400)

    profile = get_user_profile(request.user)
    role = profile.get_role_display() if profile else ''

    BugReport.objects.create(
        customer=customer,
        user=request.user,
        username=request.user.username,
        role=role,
        phone=customer.phone or '',
        subject=form.cleaned_data['subject'],
        description=form.cleaned_data['description'],
        status=BugReport.STATUS_REVIEWING,
    )

    return JsonResponse({
        'ok': True,
        'message': 'پیام گزارش مشکل ثبت شد. باتشکر.',
    })


@require_POST
def announcement_seen(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({
            'ok': False,
            'message': 'برای مشاهده اطلاعیه ابتدا وارد حساب کاربری شوید.',
        }, status=403)

    announcement = Announcement.objects.filter(pk=pk, is_active=True).first()

    if announcement is None:
        return JsonResponse({
            'ok': False,
            'message': 'این اطلاعیه فعال نیست.',
        }, status=404)

    AnnouncementView.objects.get_or_create(
        announcement=announcement,
        user=request.user,
    )

    return JsonResponse({'ok': True})


@require_POST
def current_parking_lot_select(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None or not is_owner(request.user):
        return redirect('parking:dashboard')

    parking_lot_id = request.POST.get('parking_lot')
    selected_parking_lot = ParkingLot.objects.filter(
        customer=customer,
        pk=parking_lot_id,
    ).first()

    if selected_parking_lot:
        request.session[CURRENT_PARKING_LOT_SESSION_KEY] = selected_parking_lot.pk

    next_url = request.POST.get('next') or reverse('parking:dashboard')

    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse('parking:dashboard')

    if selected_parking_lot:
        try:
            resolved_next = resolve(urlparse(next_url).path)
        except Resolver404:
            resolved_next = None

        if resolved_next and resolved_next.namespace == 'parking':
            if resolved_next.url_name == 'parking_spot_auto_generate':
                next_url = reverse(
                    'parking:parking_spot_auto_generate',
                    kwargs={'pk': selected_parking_lot.pk},
                )

    return redirect(next_url)


def is_owner(user):
    profile = get_user_profile(user)

    if profile is None:
        return False

    if not profile.is_active or not profile.customer.is_active:
        return False

    return profile.role == CustomerUser.ROLE_OWNER


def is_operator(user):
    profile = get_user_profile(user)

    if profile is None:
        return False

    if not profile.is_active or not profile.customer.is_active:
        return False

    return profile.role == CustomerUser.ROLE_OPERATOR


CURRENT_PARKING_LOT_SESSION_KEY = 'current_parking_lot_id'


def get_current_owner_parking_lot(user, customer, request=None):
    profile = get_user_profile(user)

    if not profile or profile.role != CustomerUser.ROLE_OWNER:
        return None

    parking_lots = ParkingLot.objects.filter(customer=customer).order_by('name')

    if request is None:
        return parking_lots.first()

    selected_id = request.session.get(CURRENT_PARKING_LOT_SESSION_KEY)
    selected_parking_lot = None

    if selected_id:
        selected_parking_lot = parking_lots.filter(pk=selected_id).first()

    if selected_parking_lot is None:
        selected_parking_lot = parking_lots.first()

        if selected_parking_lot:
            request.session[CURRENT_PARKING_LOT_SESSION_KEY] = selected_parking_lot.pk

    return selected_parking_lot


def get_accessible_parking_lots(user, customer, request=None):
    parking_lots = ParkingLot.objects.filter(customer=customer)
    profile = get_user_profile(user)

    if profile and profile.role == CustomerUser.ROLE_OPERATOR:
        if profile.parking_lot_id:
            return parking_lots.filter(pk=profile.parking_lot_id)

        return parking_lots.none()

    if profile and profile.role == CustomerUser.ROLE_OWNER and request is not None:
        current_parking_lot = get_current_owner_parking_lot(user, customer, request)

        if current_parking_lot:
            return parking_lots.filter(pk=current_parking_lot.pk)

        return parking_lots.none()

    return parking_lots


def scope_to_accessible_parking_lots(queryset, user, customer, lookup, request=None):
    accessible_parking_lots = get_accessible_parking_lots(user, customer, request)
    return queryset.filter(**{f'{lookup}__in': accessible_parking_lots})


def paginate_queryset(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()

    if 'page' in query_params:
        query_params.pop('page')
    if 'partial' in query_params:
        query_params.pop('partial')

    return page_obj, query_params.urlencode()


def parse_plate_filter_tokens(value):
    value = (value or '').strip()

    if not value:
        return []

    if not value.startswith('plate-filter:'):
        return [value]

    tokens = []

    for pair in value.removeprefix('plate-filter:').split(';'):
        if '=' not in pair:
            continue

        key, token = pair.split('=', 1)
        token = token.strip()

        if key in {'first', 'letter', 'middle', 'region', 'motor'} and token:
            tokens.append(token)

    return tokens


def apply_plate_filter(queryset, value, lookup):
    for token in parse_plate_filter_tokens(value):
        queryset = queryset.filter(**{f'{lookup}__icontains': token})

    return queryset

PERSIAN_TO_LATIN = {
    'آ': 'A', 'ا': 'A', 'ب': 'B', 'پ': 'P', 'ت': 'T', 'ث': 'S',
    'ج': 'J', 'چ': 'CH', 'ح': 'H', 'خ': 'KH', 'د': 'D', 'ذ': 'Z',
    'ر': 'R', 'ز': 'Z', 'ژ': 'ZH', 'س': 'S', 'ش': 'SH', 'ص': 'S',
    'ض': 'Z', 'ط': 'T', 'ظ': 'Z', 'ع': 'A', 'غ': 'GH', 'ف': 'F',
    'ق': 'GH', 'ک': 'K', 'گ': 'G', 'ل': 'L', 'م': 'M', 'ن': 'N',
    'و': 'V', 'ه': 'H', 'ی': 'Y',
}

PERSIAN_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')


def to_persian_digits(value):
    return str(value).translate(PERSIAN_DIGITS)


def make_parking_lot_code_prefix(name):
    letters = []

    for char in name.strip():
        if char in PERSIAN_TO_LATIN:
            letters.append(PERSIAN_TO_LATIN[char])
        elif char.isascii() and char.isalpha():
            letters.append(char.upper())

        if len(letters) >= 2:
            break

    while len(letters) < 2:
        letters.append('X')

    return ''.join(letters[:2])


def natural_sort_key(value):
    parts = re.split(r'(\d+)', str(value or ''))
    return [
        int(part) if part.isdigit() else part.casefold()
        for part in parts
    ]


def parking_spot_sort_key(spot):
    return (
        natural_sort_key(spot.parking_lot.name),
        natural_sort_key(spot.level),
        natural_sort_key(spot.code),
    )


HELP_CONTACT = {
    'phone': '09113284955',
    'email': 'parkino.shop@gmail.com',
    'telegram': '@ParkinoShop',
    'telegram_url': 'https://t.me/ParkinoShop',
}


HELP_FAQS = [
    {
        'question': 'برای شروع کار با پارکینو از کجا شروع کنم؟',
        'answer': 'ابتدا پارکینگ، ظرفیت‌ها و جایگاه‌ها را تکمیل کنید، سپس تعرفه فعال هر نوع وسیله را بسازید و بعد اپراتورها را به پارکینگ مربوط وصل کنید.',
    },
    {
        'question': 'چرا هنگام ثبت وسیله نقلیه بعضی جایگاه‌ها نمایش داده نمی‌شوند؟',
        'answer': 'فقط جایگاه‌های فعال، آزاد و هماهنگ با نوع وسیله نمایش داده می‌شوند. جایگاهی که خودروی فعال دارد از انتخاب حذف می‌شود.',
    },
    {
        'question': 'اپراتور چه بخش‌هایی را می‌بیند؟',
        'answer': 'اپراتور فقط اطلاعات پارکینگ مجاز خودش را می‌بیند و می‌تواند ورود، خروج، پرداخت، رسید و مشاهده جایگاه‌ها را انجام دهد.',
    },
    {
        'question': 'اگر رمز مالک یا اپراتور فراموش شد چه کار کنم؟',
        'answer': 'مالک می‌تواند رمز اپراتورها را از بخش کاربران تغییر دهد. برای مالک، امکان تغییر رمز از مدیریت سیستم فراهم شده است.',
    },
    {
        'question': 'گزارش مشکل چه کاربردی دارد؟',
        'answer': 'از دکمه گزارش مشکل در بالای پنل، موضوع و توضیح را ثبت کنید تا همراه با نام کاربری، نقش و شماره تماس در مدیریت سیستم بررسی شود.',
    },
]


HELP_SECTIONS = [
    {
        'slug': 'dashboard',
        'title': 'داشبورد',
        'eyebrow': 'مرکز کنترل',
        'summary': 'داشبورد خلاصه وضعیت روزانه پارکینگ، ظرفیت، خودروهای فعال، پرداخت‌های در انتظار و مسیرهای سریع را نشان می‌دهد.',
        'steps': [
            'برای عملیات روزانه از دکمه‌های سریع بالای داشبورد استفاده کنید.',
            'کارت‌های آمار، وضعیت امروز پارکینگ را بدون ورود به صفحات جدا نشان می‌دهند.',
            'لیست‌های پایین داشبورد برای بررسی سریع خودروهای فعال و پرداخت‌های در انتظار هستند.',
        ],
        'tips': [
            'اگر اپراتور هستید، فقط آمار پارکینگ مجاز خودتان را می‌بینید.',
            'برای بررسی جزئیات، از لینک‌های داخل هر کارت یا جدول استفاده کنید.',
        ],
    },
    {
        'slug': 'vehicle-entry',
        'title': 'ثبت وسیله نقلیه',
        'eyebrow': 'ورود و خروج',
        'summary': 'در این بخش پلاک، نوع وسیله، رنگ و جایگاه آزاد انتخاب می‌شود و یک خودروی فعال ساخته می‌شود.',
        'steps': [
            'پلاک را با فرم پلاک ایرانی وارد کنید.',
            'نوع وسیله و رنگ را انتخاب کنید تا جایگاه‌های مرتبط نمایش داده شوند.',
            'در بخش انتخاب جایگاه، جستجو کنید و فقط از بین جایگاه‌های آزاد انتخاب کنید.',
            'پس از ثبت، خودرو در لیست خودروهای فعال نمایش داده می‌شود.',
        ],
        'tips': [
            'جایگاهی که خودروی فعال دارد از ابتدا در لیست انتخاب نمایش داده نمی‌شود.',
            'برای موتور و سواری، جایگاه‌ها جداگانه فیلتر می‌شوند.',
        ],
    },
    {
        'slug': 'active-vehicles',
        'title': 'خودروهای فعال',
        'eyebrow': 'کنترل روزانه',
        'summary': 'این صفحه خودروهایی را نشان می‌دهد که هنوز خروج آن‌ها ثبت نشده یا وضعیت عملیاتی دارند.',
        'steps': [
            'از فیلترها برای پیدا کردن پلاک، نوع وسیله، وضعیت یا بازه ورود و خروج استفاده کنید.',
            'برای پایان توقف از ثبت خروج استفاده کنید.',
            'برای مشاهده اطلاعات کامل هر رکورد، وارد جزئیات شوید.',
            'اگر ورود اشتباه ثبت شده، در صورت نیاز از لغو استفاده کنید.',
        ],
        'tips': [
            'ثبت خروج، هزینه توقف را محاسبه و مسیر پرداخت و رسید را آماده می‌کند.',
            'فیلترهای تاریخ بر اساس تاریخ شمسی کار می‌کنند.',
        ],
    },
    {
        'slug': 'payments',
        'title': 'پرداخت‌ها',
        'eyebrow': 'مالی',
        'summary': 'در پرداخت‌ها وضعیت پرداخت هر خروج، روش پرداخت، مبلغ و ارتباط با رسید مدیریت می‌شود.',
        'steps': [
            'پرداخت‌های در انتظار را بررسی کنید.',
            'روش پرداخت را انتخاب و وضعیت را ثبت کنید.',
            'بعد از پرداخت موفق، رسید مربوط قابل مشاهده و چاپ است.',
        ],
        'tips': [
            'برای جستجوی دقیق‌تر از فیلتر پلاک، پارکینگ، روش پرداخت و بازه تاریخ استفاده کنید.',
            'اگر پرداختی اشتباه ثبت شد، جزئیات پرداخت را بررسی و اصلاح کنید.',
        ],
    },
    {
        'slug': 'receipts',
        'title': 'رسیدها',
        'eyebrow': 'چاپ و بایگانی',
        'summary': 'رسیدها سند نهایی پرداخت و خروج هستند و اطلاعات پلاک، زمان‌ها، مبلغ و روش پرداخت را نمایش می‌دهند.',
        'steps': [
            'رسید مورد نظر را با شماره رسید، پلاک یا تاریخ پیدا کنید.',
            'جزئیات رسید را باز کنید.',
            'برای چاپ، وارد صفحه چاپ رسید شوید؛ خود رسید همیشه روشن و مناسب چاپ است.',
        ],
        'tips': [
            'در حالت چاپ، دکمه‌ها حذف می‌شوند و فقط رسید چاپ می‌شود.',
        ],
    },
    {
        'slug': 'parking-lots',
        'title': 'پارکینگ‌ها',
        'eyebrow': 'زیرساخت',
        'summary': 'در این بخش پارکینگ‌ها، ظرفیت خودرو و موتور و تعداد طبقات مدیریت می‌شوند.',
        'owner_only': True,
        'steps': [
            'نام پارکینگ، ظرفیت خودرو، ظرفیت موتور و تعداد طبقات را ثبت کنید.',
            'بعد از ساخت پارکینگ، جایگاه‌ها را دستی یا خودکار بسازید.',
            'برای اپراتورها، پارکینگ مجاز را از بخش کاربران مشخص کنید.',
        ],
        'tips': [
            'ظرفیت‌ها باید با تعداد جایگاه‌های فعال هماهنگ باشند.',
            'کاهش ظرفیت زیر تعداد جایگاه‌های فعال پذیرفته نمی‌شود.',
        ],
    },
    {
        'slug': 'parking-spots',
        'title': 'جایگاه‌ها',
        'eyebrow': 'نقشه ظرفیت',
        'summary': 'جایگاه‌ها محل‌های قابل انتخاب برای ورود وسیله هستند و به تفکیک پارکینگ، طبقه و نوع وسیله مدیریت می‌شوند.',
        'steps': [
            'برای ساخت سریع، از ساخت خودکار جایگاه‌ها استفاده کنید.',
            'برای اصلاح موردی، جایگاه را از جدول ویرایش کنید.',
            'جایگاه غیرفعال در انتخاب ثبت وسیله نقلیه نمایش داده نمی‌شود.',
        ],
        'tips': [
            'اپراتور فقط امکان مشاهده جایگاه‌ها را دارد و تغییرات زیرساختی مخصوص مالک است.',
            'کد جایگاه‌ها بهتر است کوتاه، یکتا و قابل جستجو باشد.',
        ],
    },
    {
        'slug': 'tariffs',
        'title': 'تعرفه‌ها',
        'eyebrow': 'قیمت‌گذاری',
        'summary': 'تعرفه‌ها هزینه ساعت اول، ساعت‌های بعدی و توقف شبانه‌روزی هر نوع وسیله را مشخص می‌کنند.',
        'owner_only': True,
        'steps': [
            'برای هر نوع وسیله یک تعرفه فعال نگه دارید.',
            'مبلغ‌ها را با رقم معتبر وارد کنید.',
            'اگر تعرفه‌ای دیگر استفاده نمی‌شود، آن را غیرفعال یا حذف کنید.',
        ],
        'tips': [
            'تعرفه فعال روی محاسبه هزینه خروج اثر مستقیم دارد.',
        ],
    },
    {
        'slug': 'reports',
        'title': 'گزارش‌ها',
        'eyebrow': 'تحلیل عملکرد',
        'summary': 'گزارش‌ها وضعیت ورود و خروج، درآمد، پرداخت‌ها، اشغال فضا و تفکیک خودرو و موتور را در بازه انتخابی نشان می‌دهند.',
        'owner_only': True,
        'steps': [
            'بازه تاریخ شمسی را انتخاب کنید.',
            'در صورت نیاز، پارکینگ یا نوع وسیله را محدود کنید.',
            'خلاصه آمار، روش‌های پرداخت و آخرین خروج‌ها را بررسی کنید.',
        ],
        'tips': [
            'صفحه‌بندی آخرین خروج‌ها فقط همان جدول را به‌روزرسانی می‌کند.',
        ],
    },
    {
        'slug': 'users',
        'title': 'کاربران و نقش‌ها',
        'eyebrow': 'کنترل دسترسی',
        'summary': 'در این بخش مالک‌ها و اپراتورها ساخته و مدیریت می‌شوند و برای اپراتور پارکینگ مجاز تعیین می‌شود.',
        'owner_only': True,
        'steps': [
            'برای اپراتور جدید، نام کاربری، ایمیل، نقش و پارکینگ مجاز را وارد کنید.',
            'در صورت فراموشی رمز، از تغییر رمز همان کاربر استفاده کنید.',
            'کاربر غیرفعال امکان استفاده از پنل را ندارد.',
        ],
        'tips': [
            'نام کاربری با حروف و اعداد انگلیسی ثبت می‌شود.',
            'اپراتور بدون پارکینگ مجاز به داده عملیاتی دسترسی ندارد.',
        ],
    },
    {
        'slug': 'settings',
        'title': 'اطلاعات کاربری',
        'eyebrow': 'حساب و مجموعه',
        'summary': 'در اطلاعات کاربری، نام مجموعه، نام مالک، شماره تماس و ایمیل حساب مالک تکمیل می‌شود.',
        'owner_only': True,
        'steps': [
            'نام مجموعه و نام مالک یا مدیر را با حروف فارسی وارد کنید.',
            'شماره تماس و ایمیل فعال را برای پیگیری حساب ثبت کنید.',
            'پس از ذخیره موفق، اطلاعات نمایشی پنل و رسیدها به‌روز می‌شود.',
        ],
        'tips': [
            'آدرس هر پارکینگ از بخش پارکینگ‌ها مدیریت می‌شود.',
            'اگر فرم خطا داشته باشد، اطلاعات حساب تا ذخیره موفق تغییر نمی‌کند.',
        ],
    },
]


def get_visible_help_sections(user):
    owner_user = is_owner(user)
    return [
        section
        for section in HELP_SECTIONS
        if owner_user or not section.get('owner_only')
    ]


def help_faq(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    if request.user.is_superuser or request.user.is_staff:
        return redirect('parking:home')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:customer_request')

    return render(request, 'parking/help_faq.html', {
        'customer': customer,
        'faqs': HELP_FAQS,
        'help_sections': get_visible_help_sections(request.user),
        'help_contact': HELP_CONTACT,
    })


def help_section(request, slug):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    if request.user.is_superuser or request.user.is_staff:
        return redirect('parking:home')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:customer_request')

    sections = get_visible_help_sections(request.user)
    section = next((item for item in sections if item['slug'] == slug), None)

    if section is None:
        raise Http404('Help section not found')

    return render(request, 'parking/help_section.html', {
        'customer': customer,
        'section': section,
        'help_sections': sections,
        'help_contact': HELP_CONTACT,
    })


def home(request):
    if request.user.is_authenticated and get_user_customer(request.user):
        return redirect('parking:dashboard')

    today_entries = random.randint(200, 1000)
    successful_payments = today_entries - random.randint(20, 50)

    hero_stats = {
        'today_entries': to_persian_digits(today_entries),
        'free_spots': to_persian_digits(random.randint(50, 250)),
        'successful_payments': to_persian_digits(successful_payments),
        'average_duration': to_persian_digits(random.randint(50, 150)),
    }

    return render(request, 'parking/home.html', {
        'hero_stats': hero_stats,
    })

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    if request.user.is_superuser or request.user.is_staff:
        return redirect('parking:home')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:customer_request')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)
    today = timezone.localdate()

    spots = ParkingSpot.objects.select_related(
        'parking_lot',
        'parking_lot__customer',
    ).filter(
        parking_lot__customer=customer,
        is_active=True,
    )
    spots = spots.filter(parking_lot__in=accessible_parking_lots)

    sessions = ParkingSession.objects.select_related(
        'vehicle',
        'spot',
        'spot__parking_lot',
    ).filter(
        vehicle__customer=customer
    )
    sessions = sessions.filter(spot__parking_lot__in=accessible_parking_lots)

    payments = Payment.objects.select_related(
        'session',
        'session__vehicle',
        'session__spot',
        'session__spot__parking_lot',
    ).filter(
        session__vehicle__customer=customer
    )
    payments = payments.filter(session__spot__parking_lot__in=accessible_parking_lots)

    receipts = Receipt.objects.select_related(
        'session',
        'session__vehicle',
    ).filter(
        session__vehicle__customer=customer
    )
    receipts = receipts.filter(session__spot__parking_lot__in=accessible_parking_lots)

    latest_payment = payments.order_by('-payment_time').first()
    latest_receipt = receipts.order_by('-issue_time').first()
    total_spots = spots.count()
    occupied_spots = spots.filter(is_occupied=True).count()
    available_spots = spots.filter(is_occupied=False).count()

    car_spots = spots.filter(
    spot_type=Vehicle.VEHICLE_TYPE_CAR
    )

    motorcycle_spots = spots.filter(
        spot_type=Vehicle.VEHICLE_TYPE_MOTORCYCLE
    )

    car_total_spots = car_spots.count()
    car_occupied_spots = car_spots.filter(is_occupied=True).count()
    car_available_spots = car_spots.filter(is_occupied=False).count()

    motorcycle_total_spots = motorcycle_spots.count()
    motorcycle_occupied_spots = motorcycle_spots.filter(is_occupied=True).count()
    motorcycle_available_spots = motorcycle_spots.filter(is_occupied=False).count()

    open_sessions_count = sessions.filter(
        status=ParkingSession.SESSION_STATUS_OPEN
    ).count()

    open_car_sessions_count = sessions.filter(
    status=ParkingSession.SESSION_STATUS_OPEN,
    vehicle__type=Vehicle.VEHICLE_TYPE_CAR
    ).count()

    open_motorcycle_sessions_count = sessions.filter(
        status=ParkingSession.SESSION_STATUS_OPEN,
        vehicle__type=Vehicle.VEHICLE_TYPE_MOTORCYCLE
    ).count()

    closed_sessions_count = sessions.filter(
        status=ParkingSession.SESSION_STATUS_CLOSED
    ).count()

    cancelled_sessions_count = sessions.filter(
        status=ParkingSession.SESSION_STATUS_CANCELLED
    ).count()

    today_entries_count = sessions.filter(
        entry_time__date=today
    ).count()

    today_exits_count = sessions.filter(
        exit_time__date=today,
        status=ParkingSession.SESSION_STATUS_CLOSED
    ).count()

    open_payments_count = payments.filter(
        payment_status=Payment.PAYMENT_STATUS_OPEN
    ).count()

    today_income = payments.filter(
        payment_status=Payment.PAYMENT_STATUS_CLOSED,
        payment_time__date=today
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    today_receipts_count = receipts.filter(
        issue_time__date=today
    ).count()

    active_sessions = sessions.filter(
        status=ParkingSession.SESSION_STATUS_OPEN
    ).order_by('-entry_time')[:10]

    open_payments = payments.filter(
        payment_status=Payment.PAYMENT_STATUS_OPEN
    ).order_by('-payment_time')[:10]

    monthly_report_start = today - timedelta(days=30)
    monthly_report_end = today

    context = {
        'customer': customer,
        'user_profile': get_user_profile(request.user),
        'is_owner_user': is_owner(request.user),

        'total_spots': total_spots,
        'occupied_spots': occupied_spots,
        'available_spots': available_spots,

        'open_sessions_count': open_sessions_count,
        'closed_sessions_count': closed_sessions_count,
        'cancelled_sessions_count': cancelled_sessions_count,

        'today_entries_count': today_entries_count,
        'today_exits_count': today_exits_count,
        'open_payments_count': open_payments_count,
        'today_income': today_income,
        'today_receipts_count': today_receipts_count,

        'parking_lots_count': accessible_parking_lots.count(),
        'users_count': CustomerUser.objects.filter(customer=customer).count(),

        'active_sessions': active_sessions,
        'open_payments': open_payments,
        'latest_payment': latest_payment,
        'latest_receipt': latest_receipt,
        'monthly_report_start': monthly_report_start,
        'monthly_report_end': monthly_report_end,
        'car_total_spots': car_total_spots,
        'car_occupied_spots': car_occupied_spots,
        'car_available_spots': car_available_spots,

        'motorcycle_total_spots': motorcycle_total_spots,
        'motorcycle_occupied_spots': motorcycle_occupied_spots,
        'motorcycle_available_spots': motorcycle_available_spots,

        'open_car_sessions_count': open_car_sessions_count,
        'open_motorcycle_sessions_count': open_motorcycle_sessions_count,
    }

    return render(request, 'parking/dashboard.html', context)

def customer_request_view(request):
    if request.user.is_authenticated:
        if get_user_customer(request.user):
            return redirect('parking:dashboard')

        if request.user.is_superuser or request.user.is_staff:
            return redirect('parking:home')

    request_id = request.session.get('customer_request_id')

    if request_id and Customer.objects.filter(id=request_id).exists():
        return redirect('parking:request_status')

    if request.method == 'POST':
        form = CustomerRequestForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                customer = form.save(commit=False)
                customer.status = Customer.STATUS_PENDING
                customer.is_active = False
                customer.save()

                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password'],
                    email=customer.email,
                    first_name=customer.owner_name,
                )

                user.is_active = False
                user.save(update_fields=['is_active'])

                CustomerUser.objects.create(
                    user=user,
                    customer=customer,
                    role=CustomerUser.ROLE_OWNER,
                    is_active=True,
                )

                request.session['customer_request_id'] = customer.id

            return redirect('parking:request_status')

    else:
        form = CustomerRequestForm()

    return render(request, 'parking/customer_request.html', {
        'form': form,
    })


def request_status_view(request):
    request_id = request.session.get('customer_request_id')

    if not request_id:
        return redirect('parking:customer_request')

    customer = get_object_or_404(Customer, id=request_id)

    return render(request, 'parking/request_status.html', {
        'customer': customer,
    })


def request_success_view(request):
    return render(request, 'parking/request_success.html')


def parking_lot_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    parking_lots = ParkingLot.objects.filter(
        customer=customer,
    ).order_by('name')

    page_obj, query_string = paginate_queryset(request, parking_lots, per_page=10)

    return render(request, 'parking/parking_lot_list.html', {
        'parking_lots': page_obj,
        'customer': customer,
        'page_obj': page_obj,
        'query_string': query_string,
    })


def parking_lot_create(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    if request.method == 'POST':
        form = ParkingLotForm(request.POST, customer=customer)

        if form.is_valid():
            parking_lot = form.save(commit=False)
            parking_lot.customer = customer
            parking_lot.save()
            request.session[CURRENT_PARKING_LOT_SESSION_KEY] = parking_lot.pk

            return redirect('parking:parking_lot_list')

    else:
        form = ParkingLotForm(customer=customer)

    return render(request, 'parking/parking_lot_form.html', {
        'form': form,
        'title': 'ثبت پارکینگ جدید',
    })


def parking_lot_update(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    parking_lot = get_object_or_404(
        ParkingLot,
        pk=pk,
        customer=customer,
    )

    if request.method == 'POST':
        form = ParkingLotForm(request.POST, instance=parking_lot, customer=customer)

        if form.is_valid():
            form.save()
            return redirect('parking:parking_lot_list')

    else:
        form = ParkingLotForm(instance=parking_lot, customer=customer)

    return render(request, 'parking/parking_lot_form.html', {
        'form': form,
        'title': 'ویرایش پارکینگ',
    })

def parking_spot_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    can_manage_spots = is_owner(request.user)
    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    filter_form = ParkingSpotFilterForm(
        request.GET or None,
        customer=customer,
        parking_lots=accessible_parking_lots,
    )

    parking_spots = ParkingSpot.objects.select_related(
        'parking_lot',
        'parking_lot__customer',
    ).filter(
        parking_lot__customer=customer,
        parking_lot__in=accessible_parking_lots,
        is_active=True,
    )

    selected_parking_lot = None

    if filter_form.is_valid():
        parking_lot = filter_form.cleaned_data.get('parking_lot')
        code = filter_form.cleaned_data.get('code')
        level = filter_form.cleaned_data.get('level')
        status = filter_form.cleaned_data.get('status')
        spot_type = filter_form.cleaned_data.get('spot_type')

        if parking_lot:
            selected_parking_lot = parking_lot
            parking_spots = parking_spots.filter(parking_lot=parking_lot)

        if code:
            parking_spots = parking_spots.filter(code__icontains=code)

        if level:
            parking_spots = parking_spots.filter(level__icontains=level)

        if spot_type:
            parking_spots = parking_spots.filter(spot_type=spot_type)

        if status == 'free':
            parking_spots = parking_spots.filter(is_occupied=False)

        if status == 'occupied':
            parking_spots = parking_spots.filter(is_occupied=True)

    capacity_parking_lots = ParkingLot.objects.filter(
        customer=customer,
        pk__in=accessible_parking_lots.values('pk'),
    ).annotate(
        car_spots_count=Count(
            'spots',
            filter=Q(
                spots__spot_type=Vehicle.VEHICLE_TYPE_CAR,
                spots__is_active=True,
            )
        ),
        motorcycle_spots_count=Count(
            'spots',
            filter=Q(
                spots__spot_type=Vehicle.VEHICLE_TYPE_MOTORCYCLE,
                spots__is_active=True,
            )
        ),
    ).order_by('name')

    if selected_parking_lot:
        capacity_parking_lots = capacity_parking_lots.filter(
            pk=selected_parking_lot.pk
        )

    auto_generate_lot = capacity_parking_lots.first()
    capacity_rows = []

    for parking_lot in capacity_parking_lots:
        remaining_car_spots = parking_lot.car_capacity - parking_lot.car_spots_count
        remaining_motorcycle_spots = parking_lot.motorcycle_capacity - parking_lot.motorcycle_spots_count

        capacity_rows.append({
            'parking_lot': parking_lot,

            'car_capacity': parking_lot.car_capacity,
            'car_spots_count': parking_lot.car_spots_count,
            'remaining_car_spots': remaining_car_spots,

            'motorcycle_capacity': parking_lot.motorcycle_capacity,
            'motorcycle_spots_count': parking_lot.motorcycle_spots_count,
            'remaining_motorcycle_spots': remaining_motorcycle_spots,
        })

    parking_spots = sorted(parking_spots, key=parking_spot_sort_key)

    page_obj, query_string = paginate_queryset(request, parking_spots, per_page=10)

    return render(request, 'parking/parking_spot_list.html', {
        'parking_spots': page_obj,
        'capacity_rows': capacity_rows,
        'customer': customer,
        'filter_form': filter_form,
        'can_manage_spots': can_manage_spots,
        'auto_generate_lot': auto_generate_lot,
        'page_obj': page_obj,
        'query_string': query_string,
    })

def parking_spot_create(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    if request.method == 'POST':
        accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)
        form = ParkingSpotForm(
            request.POST,
            customer=customer,
            parking_lots=accessible_parking_lots,
        )

        if form.is_valid():
            form.save()
            return redirect('parking:parking_spot_list')

    else:
        accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)
        form = ParkingSpotForm(
            customer=customer,
            parking_lots=accessible_parking_lots,
        )

    return render(request, 'parking/parking_spot_form.html', {
        'form': form,
        'title': 'ثبت جایگاه پارک جدید',
    })


def parking_spot_update(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    parking_spot = get_object_or_404(
        ParkingSpot,
        pk=pk,
        parking_lot__customer=customer,
        parking_lot__in=accessible_parking_lots,
    )

    if request.method == 'POST':
        form = ParkingSpotForm(
            request.POST,
            instance=parking_spot,
            customer=customer,
            parking_lots=accessible_parking_lots,
        )

        if form.is_valid():
            form.save()
            return redirect('parking:parking_spot_list')

    else:
        form = ParkingSpotForm(
            instance=parking_spot,
            customer=customer,
            parking_lots=accessible_parking_lots,
        )

    return render(request, 'parking/parking_spot_form.html', {
        'form': form,
        'title': 'ویرایش جایگاه پارک',
    })


def tariff_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    current_parking_lot = get_current_owner_parking_lot(
        request.user,
        customer,
        request,
    )

    if current_parking_lot is None:
        return redirect('parking:parking_lot_list')

    filter_form = TariffFilterForm(request.GET or None)

    tariffs = Tariff.objects.filter(
        customer=customer,
        parking_lot=current_parking_lot,
    )

    if filter_form.is_valid():
        name = filter_form.cleaned_data.get('name')
        vehicle_type = filter_form.cleaned_data.get('vehicle_type')
        is_active = filter_form.cleaned_data.get('is_active')

        if name:
            tariffs = tariffs.filter(name__icontains=name)

        if vehicle_type:
            tariffs = tariffs.filter(vehicle_type=vehicle_type)

        if is_active == 'active':
            tariffs = tariffs.filter(is_active=True)

        if is_active == 'inactive':
            tariffs = tariffs.filter(is_active=False)

    tariffs = tariffs.order_by('vehicle_type', 'name')

    page_obj, query_string = paginate_queryset(request, tariffs, per_page=10)

    return render(request, 'parking/tariff_list.html', {
        'tariffs': page_obj,
        'customer': customer,
        'current_tariff_parking_lot': current_parking_lot,
        'filter_form': filter_form,
        'page_obj': page_obj,
        'query_string': query_string,
    })


def tariff_create(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    current_parking_lot = get_current_owner_parking_lot(
        request.user,
        customer,
        request,
    )

    if current_parking_lot is None:
        return redirect('parking:parking_lot_list')

    if request.method == 'POST':
        form = TariffForm(
            request.POST,
            customer=customer,
            parking_lot=current_parking_lot,
        )

        if form.is_valid():
            tariff = form.save(commit=False)
            tariff.customer = customer
            tariff.parking_lot = current_parking_lot
            tariff.save()

            return redirect('parking:tariff_list')

    else:
        form = TariffForm(
            customer=customer,
            parking_lot=current_parking_lot,
        )

    return render(request, 'parking/tariff_form.html', {
        'form': form,
        'title': 'ثبت تعرفه جدید',
        'current_tariff_parking_lot': current_parking_lot,
    })


def tariff_update(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    current_parking_lot = get_current_owner_parking_lot(
        request.user,
        customer,
        request,
    )

    if current_parking_lot is None:
        return redirect('parking:parking_lot_list')

    tariff = get_object_or_404(
        Tariff,
        pk=pk,
        customer=customer,
        parking_lot=current_parking_lot,
    )

    if request.method == 'POST':
        form = TariffForm(
            request.POST,
            instance=tariff,
            customer=customer,
            parking_lot=current_parking_lot,
        )

        if form.is_valid():
            form.save()
            return redirect('parking:tariff_list')

    else:
        form = TariffForm(
            instance=tariff,
            customer=customer,
            parking_lot=current_parking_lot,
        )

    return render(request, 'parking/tariff_form.html', {
        'form': form,
        'title': 'ویرایش تعرفه',
        'current_tariff_parking_lot': current_parking_lot,
    })


def tariff_delete(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    current_parking_lot = get_current_owner_parking_lot(
        request.user,
        customer,
        request,
    )

    if current_parking_lot is None:
        return redirect('parking:parking_lot_list')

    tariff = get_object_or_404(
        Tariff,
        pk=pk,
        customer=customer,
        parking_lot=current_parking_lot,
    )

    if request.method == 'POST':
        tariff.delete()

    return redirect('parking:tariff_list')


@never_cache
def parking_session_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)
    filter_form = ParkingSessionFilterForm(
        request.GET or None,
        customer=customer,
        parking_lots=accessible_parking_lots,
    )

    sessions = ParkingSession.objects.select_related(
        'vehicle',
        'spot',
        'spot__parking_lot',
    ).filter(
        vehicle__customer=customer
    )
    sessions = sessions.filter(spot__parking_lot__in=accessible_parking_lots)

    if filter_form.is_valid():
        plate_number = filter_form.cleaned_data.get('plate_number')
        vehicle_type = filter_form.cleaned_data.get('vehicle_type')
        parking_lot = filter_form.cleaned_data.get('parking_lot')
        status = filter_form.cleaned_data.get('status')
        entry_from = filter_form.cleaned_data.get('entry_from')
        entry_to = filter_form.cleaned_data.get('entry_to')
        exit_from = filter_form.cleaned_data.get('exit_from')
        exit_to = filter_form.cleaned_data.get('exit_to')

        if plate_number:
            sessions = apply_plate_filter(sessions, plate_number, 'vehicle__plate_number')


        if vehicle_type:
            sessions = sessions.filter(vehicle__type=vehicle_type)

        if parking_lot:
            sessions = sessions.filter(spot__parking_lot=parking_lot)

        if status:
            sessions = sessions.filter(status=status)

        if entry_from:
            sessions = sessions.filter(entry_time__date__gte=entry_from)

        if entry_to:
            sessions = sessions.filter(entry_time__date__lte=entry_to)

        if exit_from:
            sessions = sessions.filter(exit_time__date__gte=exit_from)

        if exit_to:
            sessions = sessions.filter(exit_time__date__lte=exit_to)

    sessions = sessions.order_by('-entry_time')

    page_obj, query_string = paginate_queryset(request, sessions, per_page=10)

    return render(request, 'parking/parking_session_list.html', {
        'sessions': page_obj,
        'customer': customer,
        'filter_form': filter_form,
        'page_obj': page_obj,
        'query_string': query_string,
    })


@never_cache
def parking_session_create(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    if request.method == 'POST':
        form = ParkingSessionEntryForm(
            request.POST,
            customer=customer,
            parking_lots=accessible_parking_lots,
        )

        if form.is_valid():
            plate_number = form.cleaned_data['plate_number']
            vehicle_type = form.cleaned_data['vehicle_type']
            color = form.cleaned_data.get('color')
            spot = form.cleaned_data['spot']

            vehicle, created = Vehicle.objects.get_or_create(
                customer=customer,
                plate_number=plate_number,
                defaults={
                    'type': vehicle_type,
                    'color': color,
                }
            )

            if not created:
                vehicle.type = vehicle_type
                vehicle.color = color
                vehicle.save()

            ParkingSession.objects.create(
                vehicle=vehicle,
                spot=spot,
                status=ParkingSession.SESSION_STATUS_OPEN,
            )

            return redirect('parking:parking_session_list')

    else:
        form = ParkingSessionEntryForm(customer=customer, parking_lots=accessible_parking_lots)

    return render(request, 'parking/parking_session_form.html', {
        'form': form,
        'title': 'ثبت وسیله نقلیه',
    })


@never_cache
def parking_session_close(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    session = get_object_or_404(
        ParkingSession,
        pk=pk,
        vehicle__customer=customer,
        spot__parking_lot__in=accessible_parking_lots,
    )

    if session.status != ParkingSession.SESSION_STATUS_OPEN:
        messages.info(request, 'خروج این خودرو قبلا ثبت شده است.')
        return redirect('parking:parking_session_detail', pk=session.id)

    tariff = session.get_applicable_tariff()
    tariff_missing = tariff is None

    preview_exit_time = timezone.now()
    original_exit_time = session.exit_time
    original_duration = session.total_duration_minutes
    session.exit_time = preview_exit_time
    preview_duration = session.calculate_duration()
    session.total_duration_minutes = preview_duration
    preview_fee = session.calculate_fee()
    session.exit_time = original_exit_time
    session.total_duration_minutes = original_duration

    if request.method == 'POST':
        if tariff_missing:
            return render(request, 'parking/parking_session_close.html', {
                'session': session,
                'preview_exit_time': preview_exit_time,
                'preview_duration': preview_duration,
                'preview_fee': preview_fee,
                'tariff_missing': tariff_missing,
            })

        session.exit_time = timezone.now()
        session.save()

        payment = Payment.objects.filter(
            session=session,
            payment_status=Payment.PAYMENT_STATUS_OPEN,
        ).order_by('-id').first()

        if payment:
            return redirect('parking:payment_update', pk=payment.id)

        return redirect('parking:parking_session_detail', pk=session.id)

    return render(request, 'parking/parking_session_close.html', {
        'session': session,
        'preview_exit_time': preview_exit_time,
        'preview_duration': preview_duration,
        'preview_fee': preview_fee,
        'tariff_missing': tariff_missing,
    })

def parking_session_cancel(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    session = get_object_or_404(
        ParkingSession.objects.select_related(
            'vehicle',
            'spot',
            'spot__parking_lot',
        ),
        pk=pk,
        vehicle__customer=customer,
        spot__parking_lot__in=accessible_parking_lots,
        status=ParkingSession.SESSION_STATUS_OPEN,
    )

    if request.method == 'POST':
        session.status = ParkingSession.SESSION_STATUS_CANCELLED
        session.save()

        session.spot.is_occupied = False
        session.spot.save(update_fields=['is_occupied'])

        return redirect('parking:parking_session_list')

    return render(request, 'parking/parking_session_cancel.html', {
        'session': session,
        'customer': customer,
    })

@never_cache
def parking_session_detail(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    session = get_object_or_404(
        ParkingSession.objects.select_related(
            'vehicle',
            'spot',
            'spot__parking_lot',
        ).prefetch_related(
            'payments'
        ),
        pk=pk,
        vehicle__customer=customer,
        spot__parking_lot__in=accessible_parking_lots,
    )

    payment = session.payments.order_by('-payment_time').first()

    receipt = None
    if hasattr(session, 'receipt'):
        receipt = session.receipt

    return render(request, 'parking/parking_session_detail.html', {
        'session': session,
        'payment': payment,
        'receipt': receipt,
        'customer': customer,
    })

@never_cache
def payment_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)
    filter_form = PaymentFilterForm(
        request.GET or None,
        customer=customer,
        parking_lots=accessible_parking_lots,
    )

    payments = Payment.objects.select_related(
        'session',
        'session__vehicle',
        'session__spot',
        'session__spot__parking_lot',
    ).filter(
        session__vehicle__customer=customer
    )
    payments = payments.filter(session__spot__parking_lot__in=accessible_parking_lots)

    if filter_form.is_valid():
        plate_number = filter_form.cleaned_data.get('plate_number')
        parking_lot = filter_form.cleaned_data.get('parking_lot')
        payment_method = filter_form.cleaned_data.get('payment_method')
        payment_status = filter_form.cleaned_data.get('payment_status')
        payment_from = filter_form.cleaned_data.get('payment_from')
        payment_to = filter_form.cleaned_data.get('payment_to')
        min_amount = filter_form.cleaned_data.get('min_amount')
        max_amount = filter_form.cleaned_data.get('max_amount')

        if plate_number:
            payments = apply_plate_filter(payments, plate_number, 'session__vehicle__plate_number')

        if parking_lot:
            payments = payments.filter(session__spot__parking_lot=parking_lot)

        if payment_method:
            payments = payments.filter(payment_method=payment_method)

        if payment_status:
            payments = payments.filter(payment_status=payment_status)

        if payment_from:
            payments = payments.filter(payment_time__date__gte=payment_from)

        if payment_to:
            payments = payments.filter(payment_time__date__lte=payment_to)

        if min_amount is not None:
            payments = payments.filter(amount__gte=min_amount)

        if max_amount is not None:
            payments = payments.filter(amount__lte=max_amount)

    payments = payments.order_by('-payment_time')

    page_obj, query_string = paginate_queryset(request, payments, per_page=10)

    return render(request, 'parking/payment_list.html', {
        'payments': page_obj,
        'customer': customer,
        'is_owner_user': is_owner(request.user),
        'filter_form': filter_form,
        'page_obj': page_obj,
        'query_string': query_string,
    })

def payment_update(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    payment = get_object_or_404(
        Payment,
        pk=pk,
        session__vehicle__customer=customer,
        session__spot__parking_lot__in=accessible_parking_lots,
        payment_status=Payment.PAYMENT_STATUS_OPEN,
    )

    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)

        if form.is_valid():
            payment = form.save()

            receipt = Receipt.objects.filter(
                payment=payment,
                session=payment.session,
            ).order_by('-issue_time').first()

            if receipt:
                receipt_print_url = reverse('parking:receipt_print', kwargs={'pk': receipt.id})
                return redirect(f'{receipt_print_url}?auto=1')

            return redirect('parking:receipt_list')

    else:
        form = PaymentForm(instance=payment)

    return render(request, 'parking/payment_form.html', {
        'form': form,
        'payment': payment,
    })

@never_cache
def receipt_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)
    filter_form = ReceiptFilterForm(
        request.GET or None,
        customer=customer,
        parking_lots=accessible_parking_lots,
    )

    receipts = Receipt.objects.select_related(
        'session',
        'session__vehicle',
        'session__spot',
        'session__spot__parking_lot',
        'payment',
    ).filter(
        session__vehicle__customer=customer
    )
    receipts = receipts.filter(session__spot__parking_lot__in=accessible_parking_lots)

    if filter_form.is_valid():
        receipt_number = filter_form.cleaned_data.get('receipt_number')
        plate_number = filter_form.cleaned_data.get('plate_number')
        parking_lot = filter_form.cleaned_data.get('parking_lot')
        payment_method = filter_form.cleaned_data.get('payment_method')
        issue_from = filter_form.cleaned_data.get('issue_from')
        issue_to = filter_form.cleaned_data.get('issue_to')

        if receipt_number:
            receipts = receipts.filter(receipt_number__icontains=receipt_number)

        if plate_number:
            receipts = apply_plate_filter(receipts, plate_number, 'session__vehicle__plate_number')


        if parking_lot:
            receipts = receipts.filter(session__spot__parking_lot=parking_lot)

        if payment_method:
            receipts = receipts.filter(payment__payment_method=payment_method)

        if issue_from:
            receipts = receipts.filter(issue_time__date__gte=issue_from)

        if issue_to:
            receipts = receipts.filter(issue_time__date__lte=issue_to)

    receipts = receipts.order_by('-issue_time')

    page_obj, query_string = paginate_queryset(request, receipts, per_page=10)

    return render(request, 'parking/receipt_list.html', {
        'receipts': page_obj,
        'customer': customer,
        'filter_form': filter_form,
        'page_obj': page_obj,
        'query_string': query_string,
    })


def receipt_detail(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    receipt = get_object_or_404(
        Receipt.objects.select_related(
            'session',
            'session__vehicle',
            'session__spot',
            'session__spot__parking_lot',
            'payment',
        ),
        pk=pk,
        session__vehicle__customer=customer,
        session__spot__parking_lot__in=accessible_parking_lots,
    )

    return render(request, 'parking/receipt_detail.html', {
        'receipt': receipt,
        'customer': customer,
    })

def receipt_print(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    receipt = get_object_or_404(
        Receipt.objects.select_related(
            'session',
            'session__vehicle',
            'session__spot',
            'session__spot__parking_lot',
            'payment',
        ),
        pk=pk,
        session__vehicle__customer=customer,
        session__spot__parking_lot__in=accessible_parking_lots,
    )

    auto_print = request.GET.get('auto') == '1'

    return render(request, 'parking/receipt_print.html', {
        'receipt': receipt,
        'customer': customer,
        'auto_print': auto_print,
    })

@never_cache
def report_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    today = timezone.localdate()

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    form = ReportFilterForm(
        request.GET or None,
        customer=customer,
        parking_lots=accessible_parking_lots,
    )

    start_date = today
    end_date = today
    vehicle_type = ''
    parking_lot = None

    if form.is_valid():
        start_date = form.cleaned_data.get('start_date') or today
        end_date = form.cleaned_data.get('end_date') or today
        vehicle_type = form.cleaned_data.get('vehicle_type') or ''
        parking_lot = form.cleaned_data.get('parking_lot')

    sessions = ParkingSession.objects.select_related(
        'vehicle',
        'spot',
        'spot__parking_lot',
    ).filter(
        vehicle__customer=customer
    )
    sessions = sessions.filter(spot__parking_lot__in=accessible_parking_lots)

    payments = Payment.objects.select_related(
        'session',
        'session__vehicle',
        'session__spot',
        'session__spot__parking_lot',
    ).filter(
        session__vehicle__customer=customer
    )
    payments = payments.filter(session__spot__parking_lot__in=accessible_parking_lots)

    spots = ParkingSpot.objects.select_related(
        'parking_lot',
        'parking_lot__customer',
    ).filter(
        parking_lot__customer=customer,
        parking_lot__in=accessible_parking_lots,
        is_active=True,
    )

    if vehicle_type:
        sessions = sessions.filter(vehicle__type=vehicle_type)
        payments = payments.filter(session__vehicle__type=vehicle_type)

    if parking_lot:
        sessions = sessions.filter(spot__parking_lot=parking_lot)
        payments = payments.filter(session__spot__parking_lot=parking_lot)
        spots = spots.filter(parking_lot=parking_lot)

    entries_in_range = sessions.filter(
        entry_time__date__gte=start_date,
        entry_time__date__lte=end_date,
    )

    exits_in_range = sessions.filter(
        exit_time__date__gte=start_date,
        exit_time__date__lte=end_date,
        status=ParkingSession.SESSION_STATUS_CLOSED,
    )

    successful_payments = payments.filter(
        payment_status=Payment.PAYMENT_STATUS_CLOSED,
        payment_time__date__gte=start_date,
        payment_time__date__lte=end_date,
    )

    total_income = successful_payments.aggregate(
        total=Sum('amount')
    )['total'] or 0

    car_entries_count = entries_in_range.filter(
    vehicle__type=Vehicle.VEHICLE_TYPE_CAR
    ).count()

    motorcycle_entries_count = entries_in_range.filter(
        vehicle__type=Vehicle.VEHICLE_TYPE_MOTORCYCLE
    ).count()

    car_exits_count = exits_in_range.filter(
        vehicle__type=Vehicle.VEHICLE_TYPE_CAR
    ).count()

    motorcycle_exits_count = exits_in_range.filter(
        vehicle__type=Vehicle.VEHICLE_TYPE_MOTORCYCLE
    ).count()

    car_income = successful_payments.filter(
        session__vehicle__type=Vehicle.VEHICLE_TYPE_CAR
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    motorcycle_income = successful_payments.filter(
        session__vehicle__type=Vehicle.VEHICLE_TYPE_MOTORCYCLE
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    average_duration = exits_in_range.aggregate(
        average=Avg('total_duration_minutes')
    )['average'] or 0

    total_spots = spots.count()
    occupied_spots = spots.filter(is_occupied=True).count()
    free_spots = spots.filter(is_occupied=False).count()

    car_spots = spots.filter(
    spot_type=Vehicle.VEHICLE_TYPE_CAR
    )

    motorcycle_spots = spots.filter(
        spot_type=Vehicle.VEHICLE_TYPE_MOTORCYCLE
    )

    car_total_spots = car_spots.count()
    car_occupied_spots = car_spots.filter(is_occupied=True).count()
    car_free_spots = car_spots.filter(is_occupied=False).count()

    motorcycle_total_spots = motorcycle_spots.count()
    motorcycle_occupied_spots = motorcycle_spots.filter(is_occupied=True).count()
    motorcycle_free_spots = motorcycle_spots.filter(is_occupied=False).count()

    occupancy_rate = 0

    if total_spots > 0:
        occupancy_rate = round((occupied_spots / total_spots) * 100, 2)

    active_sessions_count = sessions.filter(
        status=ParkingSession.SESSION_STATUS_OPEN
    ).count()

    vehicle_type_rows = []

    vehicle_type_stats = entries_in_range.values(
        'vehicle__type'
    ).annotate(
        count=Count('id')
    ).order_by('vehicle__type')

    vehicle_type_labels = dict(Vehicle.VEHICLE_TYPE_CHOICES)

    for row in vehicle_type_stats:
        vehicle_type_rows.append({
            'label': vehicle_type_labels.get(
                row['vehicle__type'],
                row['vehicle__type']
            ),
            'count': row['count'],
        })

    payment_method_rows = []

    payment_method_stats = successful_payments.values(
        'payment_method'
    ).annotate(
        count=Count('id'),
        total=Sum('amount'),
    ).order_by('payment_method')

    payment_method_labels = dict(Payment.PAYMENT_METHOD_CHOICES)

    for row in payment_method_stats:
        payment_method_rows.append({
            'label': payment_method_labels.get(
                row['payment_method'],
                row['payment_method'] or 'نامشخص'
            ),
            'count': row['count'],
            'total': row['total'] or 0,
        })

    closed_sessions_page, closed_sessions_query_string = paginate_queryset(
        request,
        exits_in_range.order_by('-exit_time'),
        per_page=2,
    )

    context = {
        'customer': customer,
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'entries_count': entries_in_range.count(),
        'exits_count': exits_in_range.count(),
        'successful_payments_count': successful_payments.count(),
        'total_income': total_income,
        'average_duration': round(average_duration, 2),
        'active_sessions_count': active_sessions_count,
        'total_spots': total_spots,
        'occupied_spots': occupied_spots,
        'free_spots': free_spots,
        'occupancy_rate': occupancy_rate,
        'vehicle_type_rows': vehicle_type_rows,
        'payment_method_rows': payment_method_rows,
        'closed_sessions': closed_sessions_page,
        'closed_sessions_page': closed_sessions_page,
        'closed_sessions_query_string': closed_sessions_query_string,
        'closed_sessions_total': exits_in_range.count(),
        'car_total_spots': car_total_spots,
        'car_occupied_spots': car_occupied_spots,
        'car_free_spots': car_free_spots,

        'motorcycle_total_spots': motorcycle_total_spots,
        'motorcycle_occupied_spots': motorcycle_occupied_spots,
        'motorcycle_free_spots': motorcycle_free_spots,

        'car_entries_count': car_entries_count,
        'motorcycle_entries_count': motorcycle_entries_count,
        'car_exits_count': car_exits_count,
        'motorcycle_exits_count': motorcycle_exits_count,

        'car_income': car_income,
        'motorcycle_income': motorcycle_income,
    }

    if request.GET.get('partial') == 'closed_sessions' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'parking/partials/report_closed_sessions_table.html', context)

    return render(request, 'parking/report_dashboard.html', context)


def customer_user_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)
    filter_form = CustomerUserFilterForm(request.GET or None)

    users = CustomerUser.objects.select_related(
        'user',
        'customer',
        'parking_lot',
    ).filter(
        customer=customer
    ).filter(
        Q(role=CustomerUser.ROLE_OWNER) |
        Q(parking_lot__in=accessible_parking_lots)
    )

    if filter_form.is_valid():
        username = filter_form.cleaned_data.get('username')
        full_name = filter_form.cleaned_data.get('full_name')
        email = filter_form.cleaned_data.get('email')
        role = filter_form.cleaned_data.get('role')
        is_active = filter_form.cleaned_data.get('is_active')

        if username:
            users = users.filter(user__username__icontains=username)

        if full_name:
            users = users.filter(user__first_name__icontains=full_name)

        if email:
            users = users.filter(user__email__icontains=email)

        if role:
            users = users.filter(role=role)

        if is_active == 'active':
            users = users.filter(is_active=True, user__is_active=True)

        if is_active == 'inactive':
            users = users.filter(
                Q(is_active=False) |
                Q(user__is_active=False)
            )

    users = users.order_by('role', 'user__username')

    page_obj, query_string = paginate_queryset(request, users, per_page=10)

    return render(request, 'parking/customer_user_list.html', {
        'users': page_obj,
        'customer': customer,
        'filter_form': filter_form,
        'page_obj': page_obj,
        'query_string': query_string,
    })


def customer_user_create(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    if request.method == 'POST':
        accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)
        form = CustomerUserCreateForm(
            request.POST,
            customer=customer,
            parking_lots=accessible_parking_lots,
        )

        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                email=form.cleaned_data.get('email') or '',
                first_name=form.cleaned_data.get('full_name') or '',
            )

            user.is_active = form.cleaned_data.get('is_active')
            user.save(update_fields=['is_active'])

            CustomerUser.objects.create(
                user=user,
                customer=customer,
                role=form.cleaned_data['role'],
                parking_lot=form.cleaned_data.get('parking_lot'),
                is_active=form.cleaned_data.get('is_active'),
            )

            return redirect('parking:customer_user_list')

    else:
        accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)
        form = CustomerUserCreateForm(
            customer=customer,
            parking_lots=accessible_parking_lots,
        )

    return render(request, 'parking/customer_user_form.html', {
        'form': form,
        'title': 'افزودن کاربر جدید',
    })


def customer_user_update(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    customer_user = get_object_or_404(
        CustomerUser.objects.select_related('user', 'customer', 'parking_lot').filter(
            Q(role=CustomerUser.ROLE_OWNER) |
            Q(parking_lot__in=accessible_parking_lots)
        ),
        pk=pk,
        customer=customer,
    )

    if customer_user.user == request.user:
        return redirect('parking:customer_user_list')

    if request.method == 'POST':
        form = CustomerUserUpdateForm(
            request.POST,
            instance=customer_user,
            user_instance=customer_user.user,
            customer=customer,
            parking_lots=accessible_parking_lots,
        )

        if form.is_valid():
            user = customer_user.user
            user.first_name = form.cleaned_data.get('full_name') or ''
            user.email = form.cleaned_data.get('email') or ''
            user.is_active = form.cleaned_data.get('is_active')
            user.save(update_fields=['first_name', 'email', 'is_active'])

            form.save()

            return redirect('parking:customer_user_list')

    else:
        form = CustomerUserUpdateForm(
            instance=customer_user,
            user_instance=customer_user.user,
            customer=customer,
            parking_lots=accessible_parking_lots,
        )

    return render(request, 'parking/customer_user_form.html', {
        'form': form,
        'title': 'ویرایش کاربر',
        'customer_user': customer_user,
    })

def customer_user_change_password(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    customer_user = get_object_or_404(
        CustomerUser.objects.select_related('user', 'customer', 'parking_lot').filter(
            Q(role=CustomerUser.ROLE_OWNER) |
            Q(parking_lot__in=accessible_parking_lots)
        ),
        pk=pk,
        customer=customer,
    )

    if customer_user.user == request.user:
        return redirect('parking:customer_user_list')

    if request.method == 'POST':
        form = CustomerUserPasswordForm(request.POST)

        if form.is_valid():
            user = customer_user.user
            user.set_password(form.cleaned_data['password'])
            user.save(update_fields=['password'])

            return redirect('parking:customer_user_list')

    else:
        form = CustomerUserPasswordForm()

    return render(request, 'parking/customer_user_password_form.html', {
        'form': form,
        'customer_user': customer_user,
    })

def account_change_password(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if request.method == 'POST':
        form = AccountPasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            request.user.set_password(form.cleaned_data['new_password'])
            request.user.save(update_fields=['password'])

            update_session_auth_hash(request, request.user)

            return redirect('parking:dashboard')

    else:
        form = AccountPasswordChangeForm(request.user)

    return render(request, 'parking/account_change_password.html', {
        'form': form,
        'customer': customer,
    })

def customer_settings(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    if request.method == 'POST':
        form = CustomerSettingsForm(
            request.POST,
            instance=customer,
        )

        if form.is_valid():
            form.save()
            return redirect('parking:customer_settings')

        customer = Customer.objects.get(pk=customer.pk)

    else:
        form = CustomerSettingsForm(
            instance=customer,
        )

    return render(request, 'parking/customer_settings.html', {
        'form': form,
        'customer': customer,
    })

@never_cache
def available_spots_api(request):
    def no_cache_json(payload):
        response = JsonResponse(payload)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    if not request.user.is_authenticated:
        return no_cache_json({'spots': []})

    customer = get_user_customer(request.user)

    if customer is None:
        return no_cache_json({'spots': []})

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)
    vehicle_type = request.GET.get('vehicle_type')
    query = (request.GET.get('q') or '').strip()
    selected_id = request.GET.get('selected_id')

    try:
        page = max(int(request.GET.get('page', 1)), 1)
    except (TypeError, ValueError):
        page = 1

    try:
        page_size = int(request.GET.get('page_size', 10))
    except (TypeError, ValueError):
        page_size = 10

    page_size = min(max(page_size, 1), 10)

    open_session_for_same_spot = ParkingSession.objects.filter(
        Q(spot_id=OuterRef('pk')) |
        Q(
            spot__parking_lot=OuterRef('parking_lot'),
            spot__code=OuterRef('code'),
        ),
        status=ParkingSession.SESSION_STATUS_OPEN,
    )

    spots = ParkingSpot.objects.filter(
        parking_lot__customer=customer,
        parking_lot__in=accessible_parking_lots,
        is_occupied=False,
        is_active=True,
    ).exclude(
        sessions__status=ParkingSession.SESSION_STATUS_OPEN,
    ).annotate(
        has_open_session=Exists(open_session_for_same_spot)
    ).filter(
        has_open_session=False
    ).select_related('parking_lot')

    if vehicle_type:
        spots = spots.filter(spot_type=vehicle_type)

    if query:
        spots = spots.filter(
            Q(parking_lot__name__icontains=query) |
            Q(code__icontains=query) |
            Q(level__icontains=query)
        )

    spots = sorted(spots, key=parking_spot_sort_key)

    total = len(spots)
    start = (page - 1) * page_size
    end = start + page_size
    page_spots = spots[start:end]

    def serialize_spot(spot):
        return {
            'id': spot.id,
            'text': f'{spot.parking_lot.name} - {spot.level} - {spot.code} - {spot.get_spot_type_display()}',
            'code': spot.code,
            'parking_lot': spot.parking_lot.name,
            'level': spot.level,
            'type': spot.get_spot_type_display(),
        }

    data = []

    for spot in page_spots:
        data.append(serialize_spot(spot))

    selected_spot = None

    if selected_id:
        try:
            selected_spot_id = int(selected_id)
        except (TypeError, ValueError):
            selected_spot_id = None

        if selected_spot_id and not any(spot['id'] == selected_spot_id for spot in data):
            selected = (
                ParkingSpot.objects
                .filter(
                    id=selected_spot_id,
                    parking_lot__customer=customer,
                    parking_lot__in=accessible_parking_lots,
                    is_occupied=False,
                    is_active=True,
                )
                .annotate(
                    has_open_session=Exists(open_session_for_same_spot)
                )
                .filter(has_open_session=False)
                .select_related('parking_lot')
                .first()
            )

            if selected and (not vehicle_type or selected.spot_type == vehicle_type):
                selected_spot = serialize_spot(selected)

    return no_cache_json({
        'spots': data,
        'selected_spot': selected_spot,
        'page': page,
        'page_size': page_size,
        'total': total,
        'has_next': end < total,
        'has_previous': page > 1,
    })

def parking_spot_auto_generate(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    accessible_parking_lots = get_accessible_parking_lots(request.user, customer, request)

    parking_lot = get_object_or_404(
        ParkingLot,
        pk=pk,
        customer=customer,
        pk__in=accessible_parking_lots.values('pk'),
    )

    existing_spots_count = ParkingSpot.objects.filter(
        parking_lot=parking_lot,
        is_active=True,
    ).count()

    open_sessions_count = ParkingSession.objects.filter(
        spot__parking_lot=parking_lot,
        status=ParkingSession.SESSION_STATUS_OPEN,
    ).count()

    closed_sessions_count = ParkingSession.objects.filter(
        spot__parking_lot=parking_lot,
        status=ParkingSession.SESSION_STATUS_CLOSED,
    ).count()
    form = ParkingSpotAutoGenerateForm(
        request.POST or None,
        parking_lot=parking_lot,
    )

    if request.method == 'POST':
        if open_sessions_count > 0:
            return render(request, 'parking/parking_spot_auto_generate.html', {
                'parking_lot': parking_lot,
                'existing_spots_count': existing_spots_count,
                'open_sessions_count': open_sessions_count,
                'closed_sessions_count': closed_sessions_count,
                'form': form,
                'error_message': 'برای این پارکینگ خودروی فعال وجود دارد؛ ابتدا خروج خودروهای فعال را ثبت کنید.',
            })

        if not form.is_valid():
            return render(request, 'parking/parking_spot_auto_generate.html', {
                'parking_lot': parking_lot,
                'existing_spots_count': existing_spots_count,
                'open_sessions_count': open_sessions_count,
                'closed_sessions_count': closed_sessions_count,
                'form': form,
            })

        prefix = make_parking_lot_code_prefix(parking_lot.name)
        floor_count = parking_lot.floor_count or 1
        car_counts_by_floor = form.cleaned_data['car_counts_by_floor']
        motorcycle_counts_by_floor = form.cleaned_data['motorcycle_counts_by_floor']

        with transaction.atomic():
            ParkingSpot.objects.filter(
                parking_lot=parking_lot,
                is_active=True,
            ).update(
                is_active=False,
                is_occupied=False,
            )

            new_spots = []

            for floor_number in range(1, floor_count + 1):
                level = f'طبقه {floor_number}'

                car_spots_count = car_counts_by_floor.get(floor_number, 0)
                motorcycle_spots_count = motorcycle_counts_by_floor.get(floor_number, 0)

                for index in range(1, car_spots_count + 1):
                    new_spots.append(
                        ParkingSpot(
                            parking_lot=parking_lot,
                            code=f'C{prefix}_F{floor_number}_{index}',
                            level=level,
                            spot_type=Vehicle.VEHICLE_TYPE_CAR,
                            is_occupied=False,
                            is_active=True,
                        )
                    )

                for index in range(1, motorcycle_spots_count + 1):
                    new_spots.append(
                        ParkingSpot(
                            parking_lot=parking_lot,
                            code=f'M{prefix}_F{floor_number}_{index}',
                            level=level,
                            spot_type=Vehicle.VEHICLE_TYPE_MOTORCYCLE,
                            is_occupied=False,
                            is_active=True,
                        )
                    )

            ParkingSpot.objects.bulk_create(new_spots)

        return redirect('parking:parking_spot_list')

    return render(request, 'parking/parking_spot_auto_generate.html', {
        'parking_lot': parking_lot,
        'existing_spots_count': existing_spots_count,
        'open_sessions_count': open_sessions_count,
        'closed_sessions_count': closed_sessions_count,
        'form': form,
    })
