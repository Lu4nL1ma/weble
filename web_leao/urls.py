from django.contrib import admin
from django.urls import path
from app_leao.views import (
    core,
    recursos_humanos,
    auditoria_views
)

urlpatterns = [
    path('', core.home, name='home'),
    path('menu_rh', recursos_humanos.home_rh, name='menu_rh'),
    path('auditoria_ponto/', auditoria_views.auditoria_espelho_ponto, name='auditoria_ponto'),
    path('admin/', admin.site.urls),
]
