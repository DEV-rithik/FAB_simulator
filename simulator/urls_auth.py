"""URL patterns for authentication."""

from django.urls import path
from .views_auth import login_view, logout_view, register_view

app_name = 'auth'

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/',    login_view,    name='login'),
    path('logout/',   logout_view,   name='logout'),
]
