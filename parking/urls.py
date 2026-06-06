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

    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/add/', views.vehicle_create, name='vehicle_create'),
    path('vehicles/<int:pk>/edit/', views.vehicle_update, name='vehicle_update'),
    path('parking-lots/', views.parking_lot_list, name='parking_lot_list'),
    path('parking-lots/add/', views.parking_lot_create, name='parking_lot_create'),
    path('parking-lots/<int:pk>/edit/', views.parking_lot_update, name='parking_lot_update'),
    path('parking-spots/', views.parking_spot_list, name='parking_spot_list'),
    path('parking-spots/add/', views.parking_spot_create, name='parking_spot_create'),
    path('parking-spots/<int:pk>/edit/', views.parking_spot_update, name='parking_spot_update'),
]