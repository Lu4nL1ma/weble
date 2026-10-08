import io
import re
import unicodedata
from datetime import datetime
import pandas as pd

def remover_acentos(texto):
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).upper().strip()

def ler_e_auditar_planilha_ponto(file_source):
    """
    Parser avançado para auditoria de ponto da Leão Azul Webstore.
    Aplica validações de conformidade, constrói a Matriz Semanal de Escala (7 Dias)
    e consolida o Resumo Agregado Mensal por Unidade com cálculo do V.A.
    """
    if hasattr(file_source, 'read'):
        file_bytes = io.BytesIO(file_source.read())
        xls = pd.ExcelFile(file_bytes)
    else:
        xls = pd.ExcelFile(file_source)

    PADRAO_DATA = re.compile(r'^\d{2}/\d{2}/\d{2,4}')
    PADRAO_DATA_EXTRAIR = re.compile(r'(\d{2}/\d{2}/\d{2,4})')
    PADRAO_HORARIO_REAL = re.compile(r'^\d{2}:\d{2}$')

    colaboradores_brutos = []

    # -------------------------------------------------------------------------
    # ETAPA 1: LEITURA BRUTA E EXTRAÇÃO DAS MARCAÇÕES DIÁRIAS
    # -------------------------------------------------------------------------
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        if len(df) < 11:
            continue

        nome_colaborador = str(df.iloc[6, 1]).strip() if pd.notna(df.iloc[6, 1]) else 'Desconhecido'
        cpf = str(df.iloc[6, 5]).strip() if pd.notna(df.iloc[6, 5]) else ''
        cargo = str(df.iloc[7, 5]).strip() if pd.notna(df.iloc[7, 5]) else ''
        unidade = str(df.iloc[7, 1]).strip() if pd.notna(df.iloc[7, 1]) else 'Leão Azul'

        df_ponto = df.iloc[10:].copy()
        df_ponto.columns = [
            'dia', 'registros', 'previsto', 'realizado', 'horas_noturnas',
            'horas_noturnas_red', 'intervalo', 'hora_extra', 'hora_faltante',
            'banco_horas', 'saldo_banco', 'status', 'observacoes'
        ]

        dias_colaborador = []

        for _, row in df_ponto.iterrows():
            dia_raw = str(row['dia']).strip() if pd.notna(row['dia']) else ''
            if not PADRAO_DATA.match(dia_raw):
                continue

            registros_raw = str(row['registros']).strip() if pd.notna(row['registros']) else ''
            previsto = str(row['previsto']).strip() if pd.notna(row['previsto']) else '00:00'
            status_raw = str(row['status']).strip() if pd.notna(row['status']) else ''
            status_normalizado = remover_acentos(status_raw)
            intervalo = str(row['intervalo']).strip() if pd.notna(row['intervalo']) else '00:00'
            hora_faltante = str(row['hora_faltante']).strip() if pd.notna(row['hora_faltante']) else '00:00'
            observacoes = str(row['observacoes']).strip() if pd.notna(row['observacoes']) else ''

            tokens = [b.strip() for b in registros_raw.split('-') if b.strip()] if registros_raw else []
            batidas_reais = [t for t in tokens if PADRAO_HORARIO_REAL.match(t)]

            match_data = PADRAO_DATA_EXTRAIR.search(dia_raw)
            data_str = match_data.group(1) if match_data else dia_raw.split()[0]

            try:
                if len(data_str.split('/')[-1]) == 2:
                    dt_obj = datetime.strptime(data_str, '%d/%m/%y')
                else:
                    dt_obj = datetime.strptime(data_str, '%d/%m/%Y')
            except Exception:
                cleaned_data_str = re.sub(r'[^\d/]', '', data_str)
                try:
                    dt_obj = datetime.strptime(cleaned_data_str, '%d/%m/%y')
                except Exception:
                    dt_obj = datetime.now()

            semana_iso = dt_obj.isocalendar()[1]
            is_domingo = dt_obj.weekday() == 6
            teve_trabalho = len(batidas_reais) > 0
            
            status_is_folga = (
                any(f in status_normalizado for f in ['DESCANSO', 'FERIADO', 'FOLGA', 'DSR']) or 
                previsto == '00:00'
            )

            minutos_previstos = 0
            if previsto and previsto != '00:00':
                try:
                    hp, mp = map(int, previsto.split(':'))
                    minutos_previstos = hp * 60 + mp
                except ValueError:
                    pass

            dias_colaborador.append({
                'dia': dia_raw,
                'data_str': data_str,
                'dt_obj': dt_obj,
                'semana_iso': semana_iso,
                'is_domingo': is_domingo,
                'batidas_reais': batidas_reais,
                'previsto': previsto,
                'minutos_previstos': minutos_previstos,
                'status': status_raw,
                'intervalo': intervalo,
                'hora_faltante': hora_faltante,
                'observacoes': observacoes,
                'teve_trabalho': teve_trabalho,
                'status_is_folga': status_is_folga
            })

        colaboradores_brutos.append({
            'nome': nome_colaborador,
            'cpf': cpf,
            'cargo': cargo,
            'unidade': unidade,
            'dias': dias_colaborador
        })

    # -------------------------------------------------------------------------
    # ETAPA 2: MAPEAMENTO MATRICIAL SEMANAL E MENSAL (DOMINGOS) POR UNIDADE
    # -------------------------------------------------------------------------
    matriz_semanal = {}
    domingos_trabalhados_por_colab = {}

    for c in colaboradores_brutos:
        nome = c['nome']
        unidade = c['unidade']
        domingos_trabalhados_por_colab[nome] = []

        for d in c['dias']:
            semana = d['semana_iso']
            chave = (unidade, semana)

            if chave not in matriz_semanal:
                matriz_semanal[chave] = []

            eh_ausencia_sem_abono = (
                len(d['batidas_reais']) == 0 and 
                d['previsto'] != '00:00' and 
                not d['status_is_folga'] and 
                not d['observacoes']
            )

            if d['is_domingo'] and d['teve_trabalho']:
                domingos_trabalhados_por_colab[nome].append(d['data_str'])

            matriz_semanal[chave].append({
                'nome': nome,
                'dia': d['dia'],
                'data_str': d['data_str'],
                'dt_obj': d['dt_obj'],
                'is_domingo': d['is_domingo'],
                'teve_trabalho': d['teve_trabalho'],
                'ausencia': eh_ausencia_sem_abono
            })

    # -------------------------------------------------------------------------
    # ETAPA 3: AUDITORIA INDIVIDUAL E CONSTRUÇÃO DA MATRIZ SEMANAL DE ESCALA
    # -------------------------------------------------------------------------
    resultados_auditoria = []
    matriz_escala_semanal = {}

    for c in colaboradores_brutos:
        unidade = c['unidade']
        nome_colab = c['nome']
        inconsistencias_colaborador = []

        if unidade not in matriz_escala_semanal:
            matriz_escala_semanal[unidade] = {}

        for d in c['dias']:
            dia_raw = d['dia']
            batidas_reais = d['batidas_reais']
            previsto = d['previsto']
            minutos_previstos = d['minutos_previstos']
            intervalo = d['intervalo']
            hora_faltante = d['hora_faltante']
            observacoes = d['observacoes']
            semana_iso = d['semana_iso']
            is_domingo = d['is_domingo']
            status_is_folga = d['status_is_folga']
            data_str = d['data_str']

            num_batidas = len(batidas_reais)

            if semana_iso not in matriz_escala_semanal[unidade]:
                matriz_escala_semanal[unidade][semana_iso] = {
                    'semana_iso': semana_iso,
                    'dias_cabecalho': [],
                    'colaboradores_map': {},
                    'contingente_diario': {}
                }

            semana_ref = matriz_escala_semanal[unidade][semana_iso]

            if data_str not in [x['data_str'] for x in semana_ref['dias_cabecalho']]:
                semana_ref['dias_cabecalho'].append({
                    'data_str': data_str,
                    'dia_semana': d['dt_obj'].strftime('%a').capitalize(),
                    'is_domingo': is_domingo
                })

            if data_str not in semana_ref['contingente_diario']:
                semana_ref['contingente_diario'][data_str] = 0

            if nome_colab not in semana_ref['colaboradores_map']:
                semana_ref['colaboradores_map'][nome_colab] = {
                    'nome': nome_colab,
                    'cargo': c['cargo'],
                    'dias': {}
                }

            if d['teve_trabalho']:
                semana_ref['contingente_diario'][data_str] += 1
                horario_resumo = f"{batidas_reais[0]} - {batidas_reais[-1]}" if len(batidas_reais) >= 2 else batidas_reais[0]
                status_escala = {
                    'codigo': 'TRAB',
                    'badge': 'bg-success',
                    'texto': horario_resumo,
                    'eh_folga': False
                }
            else:
                status_escala = {
                    'codigo': 'FOLGA_CAD',
                    'badge': 'bg-secondary',
                    'texto': 'FOLGA',
                    'eh_folga': True
                }

            if num_batidas == 0 and previsto != '00:00' and not status_is_folga and not observacoes:
                
                if is_domingo:
                    domingos_trabalhados = domingos_trabalhados_por_colab.get(nome_colab, [])
                    if len(domingos_trabalhados) > 0:
                        datas_dom_str = ", ".join(domingos_trabalhados)
                        inconsistencias_colaborador.append({
                            'dia': dia_raw,
                            'tipo': 'Rodízio de Domingo Não Cadastrado (DSR)',
                            'detalhe': f'Provável folga de rodízio de domingo na unidade {unidade}. Trabalhou nos demais domingos ({datas_dom_str}).',
                            'nivel': 'ALERTA'
                        })
                        status_escala = {
                            'codigo': 'RODIZIO_DOM',
                            'badge': 'bg-warning text-dark',
                            'texto': 'DSR Domingo',
                            'eh_folga': True
                        }
                        semana_ref['colaboradores_map'][nome_colab]['dias'][data_str] = status_escala
                        continue

                registros_semana_loja = matriz_semanal.get((unidade, semana_iso), [])
                par_troca = None

                for reg in registros_semana_loja:
                    if reg['nome'] != nome_colab and reg['ausencia']:
                        colega_nome = reg['nome']
                        dia_ausencia_colega = reg['dia']

                        colab_trabalhou_no_dia_do_colega = any(
                            d_check['teve_trabalho'] 
                            for d_check in c['dias'] 
                            if d_check['data_str'] == reg['data_str']
                        )

                        colega_trabalhou_no_dia_atual = any(
                            r_check['teve_trabalho'] 
                            for r_check in registros_semana_loja 
                            if r_check['nome'] == colega_nome and r_check['data_str'] == d['data_str']
                        )

                        if colab_trabalhou_no_dia_do_colega and colega_trabalhou_no_dia_atual:
                            par_troca = {
                                'colega': colega_nome,
                                'dia_colega': dia_ausencia_colega
                            }
                            break

                if par_troca:
                    inconsistencias_colaborador.append({
                        'dia': dia_raw,
                        'tipo': 'Escala Alternada Não Cadastrada',
                        'detalhe': f'Provável troca de folga semanal na unidade {unidade} com {par_troca["colega"]} (ausente no dia {par_troca["dia_colega"]}).',
                        'nivel': 'ALERTA'
                    })
                    primeiro_nome_colega = par_troca['colega'].split()[0]
                    status_escala = {
                        'codigo': 'ESCALA_ALT',
                        'badge': 'bg-primary',
                        'texto': f'Troca ({primeiro_nome_colega})',
                        'eh_folga': True
                    }
                else:
                    inconsistencias_colaborador.append({
                        'dia': dia_raw,
                        'tipo': 'Falta Integral',
                        'detalhe': f'Previsão de {previsto}h sem registro de ponto no relógio.',
                        'nivel': 'ERRO'
                    })
                    status_escala = {
                        'codigo': 'FALTA',
                        'badge': 'bg-danger',
                        'texto': 'FALTA',
                        'eh_folga': True
                    }

                semana_ref['colaboradores_map'][nome_colab]['dias'][data_str] = status_escala
                continue

            if num_batidas > 0 and previsto != '00:00' and not status_is_folga:
                if num_batidas % 2 != 0:
                    inconsistencias_colaborador.append({
                        'dia': dia_raw,
                        'tipo': 'Marcação Ímpar / Falta de Batida',
                        'detalhe': f'Registrado {num_batidas} batida(s) ({", ".join(batidas_reais)}). Batida ausente.',
                        'nivel': 'ERRO'
                    })
                    status_escala['badge'] = 'bg-danger'
                    status_escala['texto'] = f'Ímpar ({num_batidas}b)'
                elif num_batidas == 2 and minutos_previstos > 360:
                    inconsistencias_colaborador.append({
                        'dia': dia_raw,
                        'tipo': 'Marcação Incompleta (Sem Batida de Almoço)',
                        'detalhe': f'Jornada de {previsto}h com apenas {num_batidas} batida(s) ({", ".join(batidas_reais)}). Faltam batidas do intervalo.',
                        'nivel': 'ERRO'
                    })
                    status_escala['badge'] = 'bg-danger'
                    status_escala['texto'] = 'Sem Almoço'

            if num_batidas > 0 and hora_faltante != '00:00' and not observacoes and previsto != '00:00':
                inconsistencias_colaborador.append({
                    'dia': dia_raw,
                    'tipo': 'Jornada Incompleta',
                    'detalhe': f'Carga faltante apurada: {hora_faltante}h (Batidas: {", ".join(batidas_reais)}).',
                    'nivel': 'ALERTA'
                })

            if intervalo and intervalo != '00:00':
                try:
                    h, m = map(int, intervalo.split(':'))
                    minutos = h * 60 + m
                    if 0 < minutos < 60 and not status_is_folga:
                        inconsistencias_colaborador.append({
                            'dia': dia_raw,
                            'tipo': 'Intervalo Sub-1h',
                            'detalhe': f'Intervalo de {intervalo} (abaixo de 01:00h).',
                            'nivel': 'ALERTA'
                        })
                except ValueError:
                    pass

            semana_ref['colaboradores_map'][nome_colab]['dias'][data_str] = status_escala

        resultados_auditoria.append({
            'nome': c['nome'],
            'cpf': c['cpf'],
            'cargo': c['cargo'],
            'unidade': unidade,
            'total_inconsistencias': len(inconsistencias_colaborador),
            'inconsistencias': inconsistencias_colaborador,
        })

    # Formatação da Matriz Semanal
    matriz_escala_formatada = {}
    for unid, semanas_dict in matriz_escala_semanal.items():
        matriz_escala_formatada[unid] = []
        for sem_iso, sem_dados in sorted(semanas_dict.items()):
            dias_cab = sem_dados['dias_cabecalho']
            primeira_data = dias_cab[0]['data_str'] if dias_cab else ''
            ultima_data = dias_cab[-1]['data_str'] if dias_cab else ''
            label_semana = f"Semana {sem_iso} ({primeira_data} a {ultima_data})"

            colaboradores_lista = []
            for colab_nome, colab_info in sem_dados['colaboradores_map'].items():
                lista_dias = [colab_info['dias'].get(d['data_str'], {'codigo': 'DESCONHECIDO', 'badge': 'bg-light text-muted', 'texto': '-', 'eh_folga': True}) for d in dias_cab]
                
                dias_trabalhados = sum(1 for d in lista_dias if not d.get('eh_folga'))

                colaboradores_lista.append({
                    'nome': colab_info['nome'],
                    'cargo': colab_info['cargo'],
                    'dias_trabalhados': dias_trabalhados,
                    'escala_dias': lista_dias
                })

            matriz_escala_formatada[unid].append({
                'semana_iso': sem_iso,
                'label_semana': label_semana,
                'dias_cabecalho': dias_cab,
                'colaboradores': colaboradores_lista,
                'contingente_diario': sem_dados['contingente_diario']
            })

    # -------------------------------------------------------------------------
    # ETAPA 4: CONSOLIDAÇÃO DO RESUMO AGREGADO + CÁLCULO DE V.A.
    # -------------------------------------------------------------------------
    resumo_agregado_unidades = {}

    for c in colaboradores_brutos:
        unidade = c['unidade']
        nome_colab = c['nome']
        cargo_colab = c['cargo']

        if unidade not in resumo_agregado_unidades:
            resumo_agregado_unidades[unidade] = []

        # Deduplicação por data_str
        dias_unicos_map = {}
        for d in c['dias']:
            data_k = d['data_str']
            if data_k not in dias_unicos_map or d['teve_trabalho']:
                dias_unicos_map[data_k] = d

        total_dias_registrados = len(dias_unicos_map)
        total_dias_trabalhados = sum(1 for d in dias_unicos_map.values() if d['teve_trabalho'])
        total_folgas = sum(1 for d in dias_unicos_map.values() if d['status_is_folga'] and not d['teve_trabalho'])

        # R$ 20/dia para Aeroporto e R$ 17/dia para as demais unidades
        valor_diaria_va = 20.00 if 'AEROPORTO' in unidade.upper() else 17.00
        valor_total_va = total_dias_trabalhados * valor_diaria_va

        inc_colab = next((r['inconsistencias'] for r in resultados_auditoria if r['nome'] == nome_colab), [])
        total_ocorrencias = len(inc_colab)

        resumo_agregado_unidades[unidade].append({
            'nome': nome_colab,
            'cargo': cargo_colab,
            'total_dias_trabalhados': total_dias_trabalhados,
            'total_folgas': total_folgas,
            'total_dias_periodo': total_dias_registrados,
            'valor_diaria_va': valor_diaria_va,
            'valor_total_va': valor_total_va,
            'total_ocorrencias': total_ocorrencias
        })

    for unid in resumo_agregado_unidades:
        resumo_agregado_unidades[unid] = sorted(resumo_agregado_unidades[unid], key=lambda x: x['nome'])

    return resultados_auditoria, matriz_escala_formatada, resumo_agregado_unidades