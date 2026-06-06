from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'parking'

urlpatterns = [
    path('', views.home, name='home'),

    path('request/', views.customer_request_view, name='customer_request'),
    path('request/status/', views.request_status_view, name='request_status'),

    path('login/', auth_views.LoginView.as_view(
        template_name='parking/login.html'
    ), name='login'),

    path('logout/', auth_views.LogoutView.as_view(
        next_page='parking:home'
    ), name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/add/', views.vehicle_create, name='vehicle_create'),
    path('vehicles/<int:pk>/edit/', views.vehicle_update, name='vehicle_update'),
]
