from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from .forms import CustomerLoginForm

app_name = 'parking'

urlpatterns = [
    path('', views.home, name='home'),

    path('request/', views.customer_request_view, name='customer_request'),
    path('request/status/', views.request_status_view, name='request_status'),

    path('login/', auth_views.LoginView.as_view(
        template_name='parking/login.html',
        authentication_form=CustomerLoginForm,
    ), name='login'),

    path('logout/', auth_views.LogoutView.as_view(
        next_page='parking:home'
    ), name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),

    path('parking-lots/', views.parking_lot_list, name='parking_lot_list'),
    path('parking-lots/add/', views.parking_lot_create, name='parking_lot_create'),
    path('parking-lots/<int:pk>/edit/', views.parking_lot_update, name='parking_lot_update'),
    path('parking-spots/', views.parking_spot_list, name='parking_spot_list'),
    path('parking-spots/add/', views.parking_spot_create, name='parking_spot_create'),
    path('parking-spots/<int:pk>/edit/', views.parking_spot_update, name='parking_spot_update'),
    path('tariffs/', views.tariff_list, name='tariff_list'),
    path('tariffs/add/', views.tariff_create, name='tariff_create'),
    path('tariffs/<int:pk>/edit/', views.tariff_update, name='tariff_update'),
    path('sessions/', views.parking_session_list, name='parking_session_list'),
    path('sessions/add/', views.parking_session_create, name='parking_session_create'),
    path('sessions/<int:pk>/close/', views.parking_session_close, name='parking_session_close'),
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/<int:pk>/edit/', views.payment_update, name='payment_update'),
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('receipts/<int:pk>/', views.receipt_detail, name='receipt_detail'),
    path('reports/', views.report_dashboard, name='report_dashboard'),
]