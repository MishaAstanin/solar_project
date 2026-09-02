from django.urls import path, include


urlpatterns = [
    path('', include('pages.urls')),
    path('export/', include('export.urls')),
    path('health/', include('healthcheck.urls')),
]
