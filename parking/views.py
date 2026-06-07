from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone

from .models import (
    ParkingSpot,
    ParkingSession,
    Payment,
    Customer,
    CustomerUser,
    Vehicle,
    ParkingLot,
    Tariff,
)

from .forms import (
    CustomerRequestForm,
    VehicleForm,
    ParkingLotForm,
    ParkingSpotForm,
    TariffForm
)    


def get_user_customer(user):
    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return None

    try:
        profile = user.customer_profile
    except CustomerUser.DoesNotExist:
        return None

    if not profile.is_active:
        return None

    if not profile.customer.is_active:
        return None

    return profile.customer


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
    )

    sessions = ParkingSession.objects.select_related(
        'vehicle',
        'vehicle__customer',
        'spot',
        'spot__parking_lot',
        'spot__parking_lot__customer',
    )

    payments = Payment.objects.select_related(
        'session',
        'session__vehicle',
        'session__vehicle__customer',
    )

    if customer:
        spots = spots.filter(parking_lot__customer=customer)
        sessions = sessions.filter(vehicle__customer=customer)
        payments = payments.filter(session__vehicle__customer=customer)

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
        if request.user.is_superuser or get_user_customer(request.user):
            return redirect('parking:dashboard')

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


def vehicle_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    vehicles = Vehicle.objects.filter(
        customer=customer
    ).order_by('plate_number')

    return render(request, 'parking/vehicle_list.html', {
        'vehicles': vehicles,
        'customer': customer,
    })


def vehicle_create(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    if request.method == 'POST':
        form = VehicleForm(request.POST)

        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.customer = customer
            vehicle.save()

            return redirect('parking:vehicle_list')

    else:
        form = VehicleForm()

    return render(request, 'parking/vehicle_form.html', {
        'form': form,
        'title': 'ثبت وسیله نقلیه جدید',
    })


def vehicle_update(request, pk):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    vehicle = get_object_or_404(
        Vehicle,
        pk=pk,
        customer=customer,
    )

    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)

        if form.is_valid():
            form.save()
            return redirect('parking:vehicle_list')

    else:
        form = VehicleForm(instance=vehicle)

    return render(request, 'parking/vehicle_form.html', {
        'form': form,
        'title': 'ویرایش وسیله نقلیه',
    })

def parking_lot_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    parking_lots = ParkingLot.objects.filter(
        customer=customer
    ).order_by('name')

    return render(request, 'parking/parking_lot_list.html', {
        'parking_lots': parking_lots,
        'customer': customer,
    })


def parking_lot_create(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
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

    parking_spots = ParkingSpot.objects.select_related(
        'parking_lot',
        'parking_lot__customer',
    ).filter(
        parking_lot__customer=customer
    ).order_by('parking_lot__name', 'level', 'code')

    return render(request, 'parking/parking_spot_list.html', {
        'parking_spots': parking_spots,
        'customer': customer,
    })


def parking_spot_create(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
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

    tariffs = Tariff.objects.filter(
        customer=customer
    ).order_by('vehicle_type', 'name')

    return render(request, 'parking/tariff_list.html', {
        'tariffs': tariffs,
        'customer': customer,
    })


def tariff_create(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
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

def tariff_list(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
        return redirect('parking:dashboard')

    tariffs = Tariff.objects.filter(
        customer=customer
    ).order_by('vehicle_type', 'name')

    return render(request, 'parking/tariff_list.html', {
        'tariffs': tariffs,
        'customer': customer,
    })


def tariff_create(request):
    if not request.user.is_authenticated:
        return redirect('parking:login')

    customer = get_user_customer(request.user)

    if customer is None:
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