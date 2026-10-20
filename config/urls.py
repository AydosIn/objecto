from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from museum.admin_views import AnalyticsView
from museum.views import LandingView

urlpatterns = [
    path('', LandingView.as_view(), name='landing'),
    path('accounts/', include('accounts.urls')),
    path('museum/', include('museum.urls')),
    # Before admin.site.urls, which would otherwise swallow this path.
    path(
        f'{settings.ADMIN_URL}analytics/',
        admin.site.admin_view(AnalyticsView.as_view()),
        name='admin-analytics',
    ),
    path(settings.ADMIN_URL, admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
