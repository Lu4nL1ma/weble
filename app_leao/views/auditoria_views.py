from django.shortcuts import render
from app_leao.services.ponto_parser import ler_e_auditar_planilha_ponto

def auditoria_espelho_ponto(request):
    """
    View de auditoria de ponto eletrônico com upload dinâmico,
    Matriz Semanal de Escala e Resumo Agregado Consolidado por Unidade.
    """
    relatorio_colaboradores = []
    matriz_escala = {}
    resumo_agregado = {}
    nome_arquivo = None
    unidades = set()

    tipos_divergencia = {
        'Falta Integral',
        'Escala Alternada Não Cadastrada',
        'Rodízio de Domingo Não Cadastrado (DSR)',
        'Marcação Ímpar / Falta de Batida',
        'Marcação Incompleta (Sem Batida de Almoço)',
        'Jornada Incompleta',
        'Intervalo Sub-1h',
    }

    if request.method == 'POST' and request.FILES.get('arquivo_ponto'):
        arquivo = request.FILES['arquivo_ponto']
        nome_arquivo = arquivo.name
        
        relatorio_colaboradores, matriz_escala, resumo_agregado = ler_e_auditar_planilha_ponto(arquivo)

        for colab in relatorio_colaboradores:
            if colab.get('unidade'):
                unidades.add(colab['unidade'])
            for inc in colab.get('inconsistencias', []):
                if inc.get('tipo'):
                    tipos_divergencia.add(inc['tipo'])

    context = {
        'titulo': 'Auditoria de Espelho de Ponto',
        'relatorio': relatorio_colaboradores,
        'matriz_escala': matriz_escala,
        'resumo_agregado': resumo_agregado,
        'nome_arquivo': nome_arquivo,
        'total_colaboradores': len(relatorio_colaboradores),
        'unidades': sorted(list(unidades)),
        'tipos_divergencia': sorted(list(tipos_divergencia)),
    }

    return render(request, 'auditoria_ponto.html', context)