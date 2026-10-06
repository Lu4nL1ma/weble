import pandas as pd
import io
import re
from datetime import datetime

def ler_e_auditar_planilha_ponto(file_source):
    """
    Parser para auditoria de ponto da Leão Azul Webstore.
    
    Aplica validações de conformidade:
    - Identifica faltas de batida intrajornada (almoço) mesmo quando há um número PAR de batidas (ex: 2 batidas em turno longo).
    - Mapeia rodízio mensal de domingos e trocas de folga na semana.
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
            status = str(row['status']).strip() if pd.notna(row['status']) else ''
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
            status_is_folga = status in ['Descanso semanal', 'Feriado', 'Folga'] or previsto == '00:00'

            # Converte 'previsto' para minutos para saber se a jornada exige almoço (> 6h)
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
                'status': status,
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
    # ETAPA 3: AUDITORIA INDIVIDUAL E DIAGNÓSTICO
    # -------------------------------------------------------------------------
    resultados_auditoria = []

    for c in colaboradores_brutos:
        unidade = c['unidade']
        nome_colab = c['nome']
        inconsistencias_colaborador = []

        for d in c['dias']:
            dia_raw = d['dia']
            batidas_reais = d['batidas_reais']
            previsto = d['previsto']
            minutos_previstos = d['minutos_previstos']
            status = d['status']
            intervalo = d['intervalo']
            hora_faltante = d['hora_faltante']
            observacoes = d['observacoes']
            semana_iso = d['semana_iso']
            is_domingo = d['is_domingo']
            status_is_folga = d['status_is_folga']

            num_batidas = len(batidas_reais)

            # -----------------------------------------------------------------
            # 1. ANÁLISE DE FALTA INTEGRAL / RODÍZIO DE DOMINGO / TROCA
            # -----------------------------------------------------------------
            if num_batidas == 0 and previsto != '00:00' and not status_is_folga and not observacoes:
                
                # Rodízio de Domingo
                if is_domingo:
                    domingos_trabalhados = domingos_trabalhados_por_colab.get(nome_colab, [])
                    if len(domingos_trabalhados) > 0:
                        datas_dom_str = ", ".join(domingos_trabalhados)
                        inconsistencias_colaborador.append({
                            'dia': dia_raw,
                            'tipo': 'Rodízio de Domingo Não Cadastrado (DSR)',
                            'detalhe': f'Provável folga de rodízio de domingo na unidade {unidade}. O colaborador trabalhou nos demais domingos do mês ({datas_dom_str}).',
                            'nivel': 'ALERTA'
                        })
                        continue

                # Troca de Folga Semanal
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
                else:
                    inconsistencias_colaborador.append({
                        'dia': dia_raw,
                        'tipo': 'Falta Integral',
                        'detalhe': f'Previsão de {previsto}h sem registro de ponto no relógio.',
                        'nivel': 'ERRO'
                    })
                continue

            # -----------------------------------------------------------------
            # 2. MARCAÇÃO INCOMPLETA / FALTA DE BATIDA (ÍMPAR OU APENAS 2 BATIDAS)
            # -----------------------------------------------------------------
            if num_batidas > 0 and previsto != '00:00' and not status_is_folga:
                # Caso A: Número Ímpar de batidas (ex: 1 ou 3 batidas)
                if num_batidas % 2 != 0:
                    inconsistencias_colaborador.append({
                        'dia': dia_raw,
                        'tipo': 'Marcação Ímpar / Falta de Batida',
                        'detalhe': f'Registrado {num_batidas} batida(s) ({", ".join(batidas_reais)}). Batida de entrada ou saída ausente.',
                        'nivel': 'ERRO'
                    })
                # Caso B: Turno longo (> 6h) com apenas 2 batidas (Omite intervalo de almoço)
                elif num_batidas == 2 and minutos_previstos > 360:
                    inconsistencias_colaborador.append({
                        'dia': dia_raw,
                        'tipo': 'Marcação Incompleta (Sem Batida de Almoço)',
                        'detalhe': f'Jornada prevista de {previsto}h com apenas {num_batidas} batida(s) ({", ".join(batidas_reais)}). Faltam as batidas do intervalo intrajornada.',
                        'nivel': 'ERRO'
                    })

            # -----------------------------------------------------------------
            # 3. JORNADA INCOMPLETA (Atraso / Saída antecipada com 4 batidas)
            # -----------------------------------------------------------------
            if num_batidas > 0 and hora_faltante != '00:00' and not observacoes and previsto != '00:00':
                inconsistencias_colaborador.append({
                    'dia': dia_raw,
                    'tipo': 'Jornada Incompleta',
                    'detalhe': f'Carga faltante apurada: {hora_faltante}h (Batidas: {", ".join(batidas_reais)}).',
                    'nivel': 'ALERTA'
                })

            # -----------------------------------------------------------------
            # 4. INTERVALO SUB-1H
            # -----------------------------------------------------------------
            if intervalo and intervalo != '00:00':
                try:
                    h, m = map(int, intervalo.split(':'))
                    minutos = h * 60 + m
                    if 0 < minutos < 60 and not status_is_folga:
                        inconsistencias_colaborador.append({
                            'dia': dia_raw,
                            'tipo': 'Intervalo Sub-1h',
                            'detalhe': f'Intervalo intrajornada de {intervalo} (abaixo de 01:00h).',
                            'nivel': 'ALERTA'
                        })
                except ValueError:
                    pass

        resultados_auditoria.append({
            'nome': c['nome'],
            'cpf': c['cpf'],
            'cargo': c['cargo'],
            'unidade': unidade,
            'total_inconsistencias': len(inconsistencias_colaborador),
            'inconsistencias': inconsistencias_colaborador,
        })

    return resultados_auditoria