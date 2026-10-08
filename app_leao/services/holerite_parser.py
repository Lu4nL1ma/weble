import io
import re
import unicodedata
from pypdf import PdfReader, PdfWriter
from app_leao.models import Colaborador, Unidade

def remover_acentos(texto):
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()

def formatar_primeiro_ultimo_nome(nome_completo):
    """Retorna o Primeiro + Último Nome em caixa alta sem caracteres especiais."""
    partes = remover_acentos(nome_completo).split()
    if not partes:
        return "COLABORADOR"
    if len(partes) == 1:
        return partes[0]
    return f"{partes[0]} {partes[-1]}"

def extrair_competencia(texto_pagina):
    """
    Busca padrões de data no PDF como:
    01/09/2026 a 30/09/2026 -> extrai '09/2026'
    ou 'Competência: 09/2026' ou '09/2026'
    """
    # Procura por intervalo de datas (ex: 01/09/2026 a 30/09/2026)
    match_intervalo = re.search(r'\d{2}/(\d{2}/\d{4})\s+a\s+\d{2}/\d{2}/\d{4}', texto_pagina)
    if match_intervalo:
        return match_intervalo.group(1) # Retorna MM/YYYY

    # Procura formato padrão MM/YYYY isolado
    match_padrao = re.search(r'\b(0[1-9]|1[0-2])/(20\d{2})\b', texto_pagina)
    if match_padrao:
        return match_padrao.group(0)

    return "09/2026"  # Fallback padrão caso não encontre no texto

def processar_e_agrupar_anexos_por_unidade(file_source):
    if hasattr(file_source, 'read'):
        pdf_bytes = io.BytesIO(file_source.read())
        reader = PdfReader(pdf_bytes)
    else:
        reader = PdfReader(file_source)

    colaboradores_banco = list(Colaborador.objects.filter(status='ATIVO'))
    unidades_banco = list(Unidade.objects.all())
    unidades_email_map = {u.nome.upper(): u.email_gerente for u in unidades_banco}

    holerites_por_unidade = {}
    nao_identificados = []
    competencia_detectada = None

    for index, page in enumerate(reader.pages):
        numero_pagina = index + 1
        texto_pagina = page.extract_text() or ""
        texto_limpo = remover_acentos(" ".join(texto_pagina.split()))

        # Tenta capturar a competência na primeira página
        if not competencia_detectada:
            competencia_detectada = extrair_competencia(texto_pagina)

        colaborador_encontrado = None
        for colab in colaboradores_banco:
            nome_limpo = remover_acentos(colab.nome)
            if nome_limpo in texto_limpo:
                colaborador_encontrado = colab
                break

        writer = PdfWriter()
        writer.add_page(page)
        pdf_individual_io = io.BytesIO()
        writer.write(pdf_individual_io)
        pdf_bytes_individual = pdf_individual_io.getvalue()

        if colaborador_encontrado:
            unid_nome = colaborador_encontrado.unidade
            if unid_nome not in holerites_por_unidade:
                holerites_por_unidade[unid_nome] = []

            # Formata NOME com Primeiro + Último Nome
            nome_resumido = formatar_primeiro_ultimo_nome(colaborador_encontrado.nome)
            comp_slug = competencia_detectada.replace('/', '-')
            
            # Exemplo de Nome: HOLERITE_LUAN_LIMA_COMP_09-2026.pdf
            nome_arquivo_pdf = f"HOLERITE - {nome_resumido} - COMP_{comp_slug}.pdf"

            holerites_por_unidade[unid_nome].append({
                'colaborador': colaborador_encontrado.nome,
                'nome_arquivo': nome_arquivo_pdf,
                'pdf_bytes': pdf_bytes_individual
            })
        else:
            nao_identificados.append({
                'pagina': numero_pagina,
                'nome_arquivo': f"HOLERITE_NAO_IDENTIFICADO_PAG_{numero_pagina}.pdf",
                'pdf_bytes': pdf_bytes_individual
            })

    pacotes_unidades = []
    for unid_nome, lista_holerites in holerites_por_unidade.items():
        email_gerente = None
        for key_unid, email_g in unidades_email_map.items():
            if key_unid in unid_nome.upper() or unid_nome.upper() in key_unid:
                email_gerente = email_g
                break

        pacotes_unidades.append({
            'unidade': unid_nome,
            'email_gerente': email_gerente or '',
            'competencia': competencia_detectada or "09/2026",
            'total_holerites': len(lista_holerites),
            'colaboradores': [h['colaborador'] for h in lista_holerites],
            'anexos_pdf': lista_holerites
        })

    return pacotes_unidades, nao_identificados