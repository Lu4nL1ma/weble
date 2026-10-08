from django.contrib import admin
from app_leao.models import Unidade, Colaborador


@admin.register(Unidade)
class UnidadeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'email_gerente')
    search_fields = ('nome', 'cnpj', 'email_gerente')
    list_filter = ('nome',)
    ordering = ('nome',)


@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'unidade', 'vinculo', 'pix', 'email', 'status')
    list_filter = ('status', 'unidade', 'vinculo')
    search_fields = ('nome', 'cpf', 'email', 'pix', 'unidade')
    list_editable = ('status', 'unidade', 'vinculo', 'pix')
    ordering = ('nome',)