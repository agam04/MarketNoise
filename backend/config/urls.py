from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def root_view(request):
    return JsonResponse({
        'service': 'MarketNoise API',
        'endpoints': {
            'api': '/api/',
            'auth': '/api/auth/',
            'admin': '/admin/',
            'health': '/api/health/',
        }
    })


urlpatterns = [
    path('', root_view),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/auth/', include('users.urls')),
]
