import random
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth.models import User
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth import update_session_auth_hash
from datetime import timedelta
from django.urls import reverse
from django.http import JsonResponse

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
    ParkingLotFilterForm,
    ParkingSpotFilterForm,
    TariffFilterForm,
    ParkingSessionFilterForm,
    PaymentFilterForm,
    ReceiptFilterForm,
    CustomerUserFilterForm,
    CustomerUserPasswordForm,
    AccountPasswordChangeForm,
    CustomerSettingsForm,
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


def paginate_queryset(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()

    if 'page' in query_params:
        query_params.pop('page')

    return page_obj, query_params.urlencode()

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


def home(request):
    if request.user.is_authenticated and get_user_customer(request.user):
        return redirect('parking:dashboard')

    request_id = request.session.get('customer_request_id')

    if request_id and Customer.objects.filter(id=request_id).exists():
        return redirect('parking:request_status')

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

    today = timezone.localdate()

    spots = ParkingSpot.objects.select_related(
        'parking_lot',
        'parking_lot__customer',
    ).filter(
        parking_lot__customer=customer,
        is_active=True,
    )

    sessions = ParkingSession.objects.select_related(
        'vehicle',
        'spot',
        'spot__parking_lot',
    ).filter(
        vehicle__customer=customer
    )

    payments = Payment.objects.select_related(
        'session',
        'session__vehicle',
        'session__spot',
        'session__spot__parking_lot',
    ).filter(
        session__vehicle__customer=customer
    )

    receipts = Receipt.objects.select_related(
        'session',
        'session__vehicle',
    ).filter(
        session__vehicle__customer=customer
    )

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

        'parking_lots_count': ParkingLot.objects.filter(customer=customer).count(),
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

    filter_form = ParkingLotFilterForm(request.GET or None)

    parking_lots = ParkingLot.objects.filter(
        customer=customer
    )

    if filter_form.is_valid():
        name = filter_form.cleaned_data.get('name')
        min_capacity = filter_form.cleaned_data.get('min_capacity')
        max_capacity = filter_form.cleaned_data.get('max_capacity')

        if name:
            parking_lots = parking_lots.filter(name__icontains=name)

        if min_capacity is not None:
            parking_lots = parking_lots.filter(total_capacity__gte=min_capacity)

        if max_capacity is not None:
            parking_lots = parking_lots.filter(total_capacity__lte=max_capacity)

    parking_lots = parking_lots.order_by('name')

    page_obj, query_string = paginate_queryset(request, parking_lots, per_page=10)

    return render(request, 'parking/parking_lot_list.html', {
        'parking_lots': page_obj,
        'customer': customer,
        'filter_form': filter_form,
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

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    filter_form = ParkingSpotFilterForm(request.GET or None, customer=customer)

    parking_spots = ParkingSpot.objects.select_related(
        'parking_lot',
        'parking_lot__customer',
    ).filter(
        parking_lot__customer=customer,
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
        customer=customer
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
        form = ParkingSpotForm(request.POST, customer=customer)

        if form.is_valid():
            form.save()
            return redirect('parking:parking_spot_list')

    else:
        form = ParkingSpotForm(customer=customer)

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

    parking_spot = get_object_or_404(
        ParkingSpot,
        pk=pk,
        parking_lot__customer=customer,
    )

    if request.method == 'POST':
        form = ParkingSpotForm(
            request.POST,
            instance=parking_spot,
            customer=customer,
        )

        if form.is_valid():
            form.save()
            return redirect('parking:parking_spot_list')

    else:
        form = ParkingSpotForm(
            instance=parking_spot,
            customer=customer,
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

    filter_form = TariffFilterForm(request.GET or None)

    tariffs = Tariff.objects.filter(
        customer=customer
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

    if request.method == 'POST':
        form = TariffForm(request.POST, customer=customer)

        if form.is_valid():
            tariff = form.save(commit=False)
            tariff.customer = customer
            tariff.save()

            return redirect('parking:tariff_list')

    else:
        form = TariffForm(customer=customer)

    return render(request, 'parking/tariff_form.html', {
        'form': form,
        'title': 'ثبت تعرفه جدید',
    })


def tariff_update(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    tariff = get_object_or_404(
        Tariff,
        pk=pk,
        customer=customer,
    )

    if request.method == 'POST':
        form = TariffForm(
            request.POST,
            instance=tariff,
            customer=customer,
        )

        if form.is_valid():
            form.save()
            return redirect('parking:tariff_list')

    else:
        form = TariffForm(
            instance=tariff,
            customer=customer,
        )

    return render(request, 'parking/tariff_form.html', {
        'form': form,
        'title': 'ویرایش تعرفه',
    })


def parking_session_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    filter_form = ParkingSessionFilterForm(request.GET or None, customer=customer)

    sessions = ParkingSession.objects.select_related(
        'vehicle',
        'spot',
        'spot__parking_lot',
    ).filter(
        vehicle__customer=customer
    )

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
            sessions = sessions.filter(vehicle__plate_number__icontains=plate_number)


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


def parking_session_create(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if request.method == 'POST':
        form = ParkingSessionEntryForm(request.POST, customer=customer)

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
        form = ParkingSessionEntryForm(customer=customer)

    return render(request, 'parking/parking_session_form.html', {
        'form': form,
        'title': 'ثبت ورود خودرو',
    })


def parking_session_close(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    session = get_object_or_404(
        ParkingSession,
        pk=pk,
        vehicle__customer=customer,
        status=ParkingSession.SESSION_STATUS_OPEN,
    )

    if request.method == 'POST':
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
    })

def parking_session_cancel(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    session = get_object_or_404(
        ParkingSession.objects.select_related(
            'vehicle',
            'spot',
            'spot__parking_lot',
        ),
        pk=pk,
        vehicle__customer=customer,
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

def parking_session_detail(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

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

def payment_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    filter_form = PaymentFilterForm(request.GET or None, customer=customer)

    payments = Payment.objects.select_related(
        'session',
        'session__vehicle',
        'session__spot',
        'session__spot__parking_lot',
    ).filter(
        session__vehicle__customer=customer
    )

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
            payments = payments.filter(session__vehicle__plate_number__icontains=plate_number)

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

    payment = get_object_or_404(
        Payment,
        pk=pk,
        session__vehicle__customer=customer,
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

def receipt_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    filter_form = ReceiptFilterForm(request.GET or None, customer=customer)

    receipts = Receipt.objects.select_related(
        'session',
        'session__vehicle',
        'session__spot',
        'session__spot__parking_lot',
        'payment',
    ).filter(
        session__vehicle__customer=customer
    )

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
            receipts = receipts.filter(session__vehicle__plate_number__icontains=plate_number)


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
    )

    auto_print = request.GET.get('auto') == '1'

    return render(request, 'parking/receipt_print.html', {
        'receipt': receipt,
        'customer': customer,
        'auto_print': auto_print,
    })

def report_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    today = timezone.localdate()

    form = ReportFilterForm(request.GET or None, customer=customer)

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

    payments = Payment.objects.select_related(
        'session',
        'session__vehicle',
        'session__spot',
        'session__spot__parking_lot',
    ).filter(
        session__vehicle__customer=customer
    )

    spots = ParkingSpot.objects.select_related(
        'parking_lot',
        'parking_lot__customer',
    ).filter(
        parking_lot__customer=customer,
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
        'closed_sessions': exits_in_range.order_by('-exit_time'),
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

    return render(request, 'parking/report_dashboard.html', context)


def customer_user_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if not is_owner(request.user):
        return redirect('parking:dashboard')

    filter_form = CustomerUserFilterForm(request.GET or None)

    users = CustomerUser.objects.select_related(
        'user',
        'customer',
    ).filter(
        customer=customer
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
        form = CustomerUserCreateForm(request.POST)

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
                is_active=form.cleaned_data.get('is_active'),
            )

            return redirect('parking:customer_user_list')

    else:
        form = CustomerUserCreateForm()

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

    customer_user = get_object_or_404(
        CustomerUser.objects.select_related('user', 'customer'),
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

    customer_user = get_object_or_404(
        CustomerUser.objects.select_related('user', 'customer'),
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
        form = CustomerSettingsForm(request.POST, instance=customer)

        if form.is_valid():
            form.save()
            return redirect('parking:customer_settings')

    else:
        form = CustomerSettingsForm(instance=customer)

    return render(request, 'parking/customer_settings.html', {
        'form': form,
        'customer': customer,
    })

def available_spots_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'spots': []})

    customer = get_user_customer(request.user)

    if customer is None:
        return JsonResponse({'spots': []})

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

    spots = ParkingSpot.objects.filter(
        parking_lot__customer=customer,
        is_occupied=False,
        is_active=True,
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
            'text': f'{spot.parking_lot.name} - {spot.code} - {spot.get_spot_type_display()}',
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
                    is_occupied=False,
                    is_active=True,
                )
                .select_related('parking_lot')
                .first()
            )

            if selected and (not vehicle_type or selected.spot_type == vehicle_type):
                selected_spot = serialize_spot(selected)

    return JsonResponse({
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

    parking_lot = get_object_or_404(
        ParkingLot,
        pk=pk,
        customer=customer,
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

    if request.method == 'POST':
        if open_sessions_count > 0:
            return render(request, 'parking/parking_spot_auto_generate.html', {
                'parking_lot': parking_lot,
                'existing_spots_count': existing_spots_count,
                'open_sessions_count': open_sessions_count,
                'closed_sessions_count': closed_sessions_count,
                'error_message': 'برای این پارکینگ سشن باز وجود دارد؛ تا قبل از ثبت خروج همه خودروها نمی‌توان جایگاه‌ها را دوباره ساخت.',
            })

        prefix = make_parking_lot_code_prefix(parking_lot.name)

        with transaction.atomic():
            ParkingSpot.objects.filter(
                parking_lot=parking_lot,
                is_active=True,
            ).update(
                is_active=False,
                is_occupied=False,
            )

            new_spots = []

            for index in range(1, parking_lot.car_capacity + 1):
                new_spots.append(
                    ParkingSpot(
                        parking_lot=parking_lot,
                        code=f'C{prefix}_{index}',
                        level='خودکار',
                        spot_type=Vehicle.VEHICLE_TYPE_CAR,
                        is_occupied=False,
                        is_active=True,
                    )
                )

            for index in range(1, parking_lot.motorcycle_capacity + 1):
                new_spots.append(
                    ParkingSpot(
                        parking_lot=parking_lot,
                        code=f'M{prefix}_{index}',
                        level='خودکار',
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
    })