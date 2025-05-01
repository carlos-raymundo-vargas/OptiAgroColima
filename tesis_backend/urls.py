# EN EL ARCHIVO urls.py PRINCIPAL DEL PROYECTO (tesis_backend/urls.py):
from django.contrib import admin
from django.urls import path, include # Asegúrate de incluir 'include'

#
urlpatterns = [
    path('admin/', admin.site.urls),
    # Incluye las URLs de tu app 'optimizer' bajo el prefijo 'api/'
    # Asegúrate que 'optimizer.urls' sea el path correcto a tu app urls
    path('api/', include('optimizer.urls')),
    # Puedes añadir otras rutas a nivel de proyecto aquí si las tienes
]
