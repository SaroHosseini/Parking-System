from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from .forms import CustomerLoginForm

app_name = 'parking'

urlpatterns = [
    path('', views.home, name='home'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap_xml'),

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
    path('help/', views.help_faq, name='help_faq'),
    path('help/<slug:slug>/', views.help_section, name='help_section'),
    path('bug-reports/create/', views.bug_report_create, name='bug_report_create'),
    path('announcements/<int:pk>/seen/', views.announcement_seen, name='announcement_seen'),
    path('parking-lot/select/', views.current_parking_lot_select, name='current_parking_lot_select'),

    path('parking-lots/', views.parking_lot_list, name='parking_lot_list'),
    path('parking-lots/add/', views.parking_lot_create, name='parking_lot_create'),
    path('parking-lots/<int:pk>/edit/', views.parking_lot_update, name='parking_lot_update'),
    path('parking-spots/', views.parking_spot_list, name='parking_spot_list'),
    path('parking-spots/add/', views.parking_spot_create, name='parking_spot_create'),
    path('parking-spots/<int:pk>/edit/', views.parking_spot_update, name='parking_spot_update'),
    path('tariffs/', views.tariff_list, name='tariff_list'),
    path('tariffs/add/', views.tariff_create, name='tariff_create'),
    path('tariffs/<int:pk>/edit/', views.tariff_update, name='tariff_update'),
    path('tariffs/<int:pk>/delete/', views.tariff_delete, name='tariff_delete'),
    path('sessions/', views.parking_session_list, name='parking_session_list'),
    path('sessions/add/', views.parking_session_create, name='parking_session_create'),
    path('sessions/<int:pk>/close/', views.parking_session_close, name='parking_session_close'),
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/<int:pk>/edit/', views.payment_update, name='payment_update'),
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('receipts/<int:pk>/', views.receipt_detail, name='receipt_detail'),
    path('reports/', views.report_dashboard, name='report_dashboard'),
    path('users/', views.customer_user_list, name='customer_user_list'),
    path('users/add/', views.customer_user_create, name='customer_user_create'),
    path('users/<int:pk>/edit/', views.customer_user_update, name='customer_user_update'),
    path('sessions/<int:pk>/', views.parking_session_detail, name='parking_session_detail'),
    path('receipts/<int:pk>/print/', views.receipt_print, name='receipt_print'),
    path('sessions/<int:pk>/cancel/', views.parking_session_cancel, name='parking_session_cancel'),
    path('users/<int:pk>/change-password/',views.customer_user_change_password,name='customer_user_change_password'),
    path('account/change-password/',views.account_change_password,name='account_change_password'),
    path('settings/', views.customer_settings, name='customer_settings'),
    path('ajax/available-spots/', views.available_spots_api, name='available_spots_api'),
    path('parking-lots/<int:pk>/auto-generate-spots/',views.parking_spot_auto_generate,name='parking_spot_auto_generate'),
]
