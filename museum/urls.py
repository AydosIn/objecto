from django.urls import path

from . import views

app_name = 'museum'

urlpatterns = [
    path('', views.MuseumView.as_view(), name='index'),
    path('new/', views.ExhibitCreateView.as_view(), name='new'),
    path('<int:pk>/', views.ExhibitDetailView.as_view(), name='detail'),
    path('<int:pk>/regenerate/', views.ExhibitRegenerateView.as_view(), name='regenerate'),
    path('<int:pk>/rename/', views.ExhibitRenameView.as_view(), name='rename'),
    path('<int:pk>/delete/', views.ExhibitDeleteView.as_view(), name='delete'),
    path('<int:pk>/share/', views.ExhibitShareView.as_view(), name='share'),
    path('<int:pk>/unshare/', views.ExhibitUnshareView.as_view(), name='unshare'),
    path('<int:pk>/pdf/', views.ExhibitPdfView.as_view(), name='pdf'),
]
