from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', RedirectView.as_view(url='/', permanent=False)),
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('parking.urls')),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
