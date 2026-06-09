from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView


urlpatterns = [
    path('admin/', RedirectView.as_view(url='/', permanent=False)),
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('parking.urls')),
]

handler400 = 'parking.views.custom_bad_request'
handler403 = 'parking.views.custom_permission_denied'
handler404 = 'parking.views.custom_page_not_found'
handler500 = 'parking.views.custom_server_error'


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
