from django.urls import path

from . import views

app_name = 'museum'

urlpatterns = [
    path('new/', views.ExhibitCreateView.as_view(), name='new'),
    path('<int:pk>/', views.ExhibitDetailView.as_view(), name='detail'),
    path('<int:pk>/regenerate/', views.ExhibitRegenerateView.as_view(), name='regenerate'),
    path('<int:pk>/rename/', views.ExhibitRenameView.as_view(), name='rename'),
    path('<int:pk>/delete/', views.ExhibitDeleteView.as_view(), name='delete'),
]
