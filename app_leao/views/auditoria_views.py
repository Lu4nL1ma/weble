from django.shortcuts import render
from app_leao.services.ponto_parser import ler_e_auditar_planilha_ponto

def auditoria_espelho_ponto(request):
    """
    View de auditoria de ponto eletrônico com upload dinâmico.
    """
    relatorio_colaboradores = []
    nome_arquivo = None
    unidades = set()
    tipos_divergencia = set()

    if request.method == 'POST' and request.FILES.get('arquivo_ponto'):
        arquivo = request.FILES['arquivo_ponto']  # <-- Pega especificamente o ARQUIVO
        nome_arquivo = arquivo.name
        
        # Passa o arquivo para o parser
        relatorio_colaboradores = ler_e_auditar_planilha_ponto(arquivo)

        # Extrai unidades e tipos de divergência únicos para popular os filtros
        for colab in relatorio_colaboradores:
            if colab.get('unidade'):
                unidades.add(colab['unidade'])
            for inc in colab.get('inconsistencias', []):
                if inc.get('tipo'):
                    tipos_divergencia.add(inc['tipo'])

    total_colaboradores = len(relatorio_colaboradores)
    total_com_inconsistencia = sum(1 for c in relatorio_colaboradores if c['total_inconsistencias'] > 0)
    total_alertas_gerais = sum(c['total_inconsistencias'] for c in relatorio_colaboradores)

    context = {
        'titulo': 'Auditoria de Espelho de Ponto',
        'relatorio': relatorio_colaboradores,
        'nome_arquivo': nome_arquivo,
        'total_colaboradores': total_colaboradores,
        'total_com_inconsistencia': total_com_inconsistencia,
        'total_alertas_gerais': total_alertas_gerais,
        'unidades': sorted(list(unidades)),
        'tipos_divergencia': sorted(list(tipos_divergencia)),
    }

    return render(request, 'auditoria_ponto.html', context)