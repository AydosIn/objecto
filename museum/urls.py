from django.urls import path

from . import views

app_name = 'museum'

urlpatterns = [
    path('new/', views.ExhibitCreateView.as_view(), name='new'),
    path('<int:pk>/', views.ExhibitDetailView.as_view(), name='detail'),
]
