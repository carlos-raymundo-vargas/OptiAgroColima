# optimizer/urls.py

from django.urls import path
from . import views # Importa las vistas DESDE la app actual (.)

urlpatterns = [
    # Ruta para la vista de optimización
    path('optimize/', views.optimize_view, name='optimize_view'),
    # Ruta para la vista de compartir datos
    path('share_data/', views.share_data_view, name='share_data_view'),
    # Puedes añadir otras rutas específicas de esta app aquí
]