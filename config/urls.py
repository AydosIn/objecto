from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from museum.admin_views import AnalyticsView
from museum.views import LandingView, SharedExhibitView, SharedPdfView, SharedPhotoView

urlpatterns = [
    path('', LandingView.as_view(), name='landing'),
    path('accounts/', include('accounts.urls')),
    path('museum/', include('museum.urls')),
    # A shared exhibit: public, for whoever has the link (the token is the secret).
    path('s/<str:token>/', SharedExhibitView.as_view(), name='shared'),
    path('s/<str:token>/photo.jpg', SharedPhotoView.as_view(), name='shared-photo'),
    path('s/<str:token>/story.pdf', SharedPdfView.as_view(), name='shared-pdf'),
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
