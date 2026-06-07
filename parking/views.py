from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth.models import User
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from django.core.paginator import Paginator

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


def home(request):
    if request.user.is_authenticated and get_user_customer(request.user):
        return redirect('parking:dashboard')

    request_id = request.session.get('customer_request_id')

    if request_id and Customer.objects.filter(id=request_id).exists():
        return redirect('parking:request_status')

    return render(request, 'parking/home.html')


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
        parking_lot__customer=customer
    )

    sessions = ParkingSession.objects.select_related(
        'vehicle',
        'vehicle__customer',
        'spot',
        'spot__parking_lot',
        'spot__parking_lot__customer',
    ).filter(
        vehicle__customer=customer
    )

    payments = Payment.objects.select_related(
        'session',
        'session__vehicle',
        'session__vehicle__customer',
    ).filter(
        session__vehicle__customer=customer
    )

    total_spots = spots.count()
    occupied_spots = spots.filter(is_occupied=True).count()
    available_spots = spots.filter(is_occupied=False).count()

    open_sessions = sessions.filter(
        status=ParkingSession.SESSION_STATUS_OPEN
    ).count()

    closed_sessions = sessions.filter(
        status=ParkingSession.SESSION_STATUS_CLOSED
    ).count()

    today_income = payments.filter(
        payment_status=Payment.PAYMENT_STATUS_CLOSED,
        payment_time__date=today
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    active_sessions = sessions.filter(
        status=ParkingSession.SESSION_STATUS_OPEN
    ).order_by('-entry_time')[:10]

    context = {
        'customer': customer,
        'user_profile': get_user_profile(request.user),
        'is_owner_user': is_owner(request.user),
        'total_spots': total_spots,
        'occupied_spots': occupied_spots,
        'available_spots': available_spots,
        'open_sessions': open_sessions,
        'closed_sessions': closed_sessions,
        'today_income': today_income,
        'active_sessions': active_sessions,
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
        form = ParkingLotForm(request.POST)

        if form.is_valid():
            parking_lot = form.save(commit=False)
            parking_lot.customer = customer
            parking_lot.save()

            return redirect('parking:parking_lot_list')

    else:
        form = ParkingLotForm()

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
        form = ParkingLotForm(request.POST, instance=parking_lot)

        if form.is_valid():
            form.save()
            return redirect('parking:parking_lot_list')

    else:
        form = ParkingLotForm(instance=parking_lot)

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
        parking_lot__customer=customer
    )

    if filter_form.is_valid():
        parking_lot = filter_form.cleaned_data.get('parking_lot')
        code = filter_form.cleaned_data.get('code')
        level = filter_form.cleaned_data.get('level')
        status = filter_form.cleaned_data.get('status')

        if parking_lot:
            parking_spots = parking_spots.filter(parking_lot=parking_lot)

        if code:
            parking_spots = parking_spots.filter(code__icontains=code)

        if level:
            parking_spots = parking_spots.filter(level__icontains=level)

        if status == 'free':
            parking_spots = parking_spots.filter(is_occupied=False)

        if status == 'occupied':
            parking_spots = parking_spots.filter(is_occupied=True)

    parking_spots = parking_spots.order_by(
        'parking_lot__name',
        'level',
        'code'
    )

    page_obj, query_string = paginate_queryset(request, parking_spots, per_page=10)

    return render(request, 'parking/parking_spot_list.html', {
        'parking_spots': page_obj,
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
        owner_name = filter_form.cleaned_data.get('owner_name')
        vehicle_type = filter_form.cleaned_data.get('vehicle_type')
        parking_lot = filter_form.cleaned_data.get('parking_lot')
        status = filter_form.cleaned_data.get('status')
        entry_from = filter_form.cleaned_data.get('entry_from')
        entry_to = filter_form.cleaned_data.get('entry_to')
        exit_from = filter_form.cleaned_data.get('exit_from')
        exit_to = filter_form.cleaned_data.get('exit_to')

        if plate_number:
            sessions = sessions.filter(vehicle__plate_number__icontains=plate_number)

        if owner_name:
            sessions = sessions.filter(vehicle__owner_name__icontains=owner_name)

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
            owner_name = form.cleaned_data.get('owner_name')
            vehicle_type = form.cleaned_data['vehicle_type']
            color = form.cleaned_data.get('color')
            spot = form.cleaned_data['spot']

            vehicle, created = Vehicle.objects.get_or_create(
                customer=customer,
                plate_number=plate_number,
                defaults={
                    'owner_name': owner_name,
                    'type': vehicle_type,
                    'color': color,
                }
            )

            if not created:
                vehicle.owner_name = owner_name
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

        return redirect('parking:parking_session_list')

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
        owner_name = filter_form.cleaned_data.get('owner_name')
        parking_lot = filter_form.cleaned_data.get('parking_lot')
        payment_method = filter_form.cleaned_data.get('payment_method')
        payment_status = filter_form.cleaned_data.get('payment_status')
        payment_from = filter_form.cleaned_data.get('payment_from')
        payment_to = filter_form.cleaned_data.get('payment_to')
        min_amount = filter_form.cleaned_data.get('min_amount')
        max_amount = filter_form.cleaned_data.get('max_amount')

        if plate_number:
            payments = payments.filter(session__vehicle__plate_number__icontains=plate_number)

        if owner_name:
            payments = payments.filter(session__vehicle__owner_name__icontains=owner_name)

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
            form.save()
            return redirect('parking:payment_list')

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
        owner_name = filter_form.cleaned_data.get('owner_name')
        parking_lot = filter_form.cleaned_data.get('parking_lot')
        payment_method = filter_form.cleaned_data.get('payment_method')
        issue_from = filter_form.cleaned_data.get('issue_from')
        issue_to = filter_form.cleaned_data.get('issue_to')

        if receipt_number:
            receipts = receipts.filter(receipt_number__icontains=receipt_number)

        if plate_number:
            receipts = receipts.filter(session__vehicle__plate_number__icontains=plate_number)

        if owner_name:
            receipts = receipts.filter(session__vehicle__owner_name__icontains=owner_name)

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

    return render(request, 'parking/receipt_print.html', {
        'receipt': receipt,
        'customer': customer,
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
        parking_lot__customer=customer
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

    average_duration = exits_in_range.aggregate(
        average=Avg('total_duration_minutes')
    )['average'] or 0

    total_spots = spots.count()
    occupied_spots = spots.filter(is_occupied=True).count()
    free_spots = spots.filter(is_occupied=False).count()

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
