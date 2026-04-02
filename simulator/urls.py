"""URL patterns for the simulator app."""

from django.urls import path
from . import views

app_name = 'simulator'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('simulate/', views.simulate_config, name='simulate'),
    path('results/<int:pk>/', views.results, name='results'),
    path('history/', views.history, name='history'),
    path('export/<int:pk>/csv/', views.export_csv, name='export_csv'),
    path('export/<int:pk>/pdf/', views.export_pdf, name='export_pdf'),
]
