from django.contrib import admin
from django.urls import path
from app_leao.views import (
    core,
    recursos_humanos,
    auditoria_views,
    holerite_views
)

urlpatterns = [
    path('', core.home, name='home'),
    path('menu_rh/', recursos_humanos.home_rh, name='menu_rh'),  # Adicionada a barra /
    path('auditoria_ponto/', auditoria_views.auditoria_espelho_ponto, name='auditoria_ponto'),
    path('menu_rh/contra-cheques/', holerite_views.processar_holerites, name='processar_holerites'),
    path('admin/', admin.site.urls),
]