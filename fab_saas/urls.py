from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from simulator import views_landing

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views_landing.landing, name='landing'),
    path('auth/', include('simulator.urls_auth')),
    path('dashboard/', include('simulator.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
