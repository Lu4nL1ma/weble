import io
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import EmailMessage
from app_leao.models import Unidade, Colaborador
from app_leao.services.holerite_parser import processar_e_agrupar_anexos_por_unidade

def processar_holerites(request):
    """
    View sincronizada com o template processar_holerites.html
    """

    # 1. BOTÃO DE LIMPAR SESSÃO / NOVO PROCESSAMENTO
    if request.GET.get('limpar') == '1':
        if 'pacotes_holerites' in request.session:
            del request.session['pacotes_holerites']
        messages.info(request, "Painel limpo! Pode enviar um novo ficheiro PDF.")
        return redirect('processar_holerites')

    # 2. DISPARO DE E-MAILS DA UNIDADE (Trata POST 'enviar_unidade')
    if request.method == 'POST' and request.POST.get('enviar_unidade'):
        unidade_alvo = request.POST.get('enviar_unidade')
        email_destino = request.POST.get('email_gerente')
        
        pacotes_sessao = request.session.get('pacotes_holerites', [])
        pacote_encontrado = next((p for p in pacotes_sessao if p['unidade'] == unidade_alvo), None)

        if pacote_encontrado and email_destino:
            competencia = pacote_encontrado.get('competencia', '09/2026')
            try:
                    subject = f"Contra Cheques - Comp. {competencia} — Unidade {unidade_alvo}"
                    
                    body = (
                        f"Olá,<br><br>"
                        f"Segue em anexo o lote de contra-cheques referentes à competência {competencia} da unidade {unidade_alvo}.<br><br>"
                        f"Total de contra-cheques anexados: {pacote_encontrado['total_holerites']}<br><br>"
                        f"<b>Atenção: preciso que todos os arquivos sejam assinados e enviados aqui!</b><br><br>"
                        f"Atenciosamente,<br>"
                        f"Luan Lima."
                    )

                    email = EmailMessage(
                        subject=subject,
                        body=body,
                        to=[email_destino]
                    )
                    
                    # OBRIGATÓRIO: Define que o corpo será interpretado como HTML no Gmail/Outlook
                    email.content_subtype = "html"

                    for item in pacote_encontrado['anexos_pdf']:
                        pdf_bytes = bytes.fromhex(item['pdf_hex']) if 'pdf_hex' in item else item.get('pdf_bytes')
                        email.attach(
                            item['nome_arquivo'],
                            pdf_bytes,
                            'application/pdf'
                        )

                    email.send(fail_silently=False)
                    messages.success(request, f"E-mail com {pacote_encontrado['total_holerites']} contra-cheque(s) enviado com sucesso para {email_destino}!")
            except Exception as e:
                messages.error(request, f"Erro ao enviar e-mail para a unidade {unidade_alvo}: {str(e)}")
        else:
            messages.warning(request, "Dados da unidade ou e-mail de destino inválidos.")

        return redirect('processar_holerites')

    # 3. UPLOAD DE UM NOVO PDF (Trata request.FILES['arquivo_holerite'])
    nao_identificados = []

    if request.method == 'POST' and request.FILES.get('arquivo_holerite'):
        # Limpa o lote anterior da memória da sessão
        if 'pacotes_holerites' in request.session:
            del request.session['pacotes_holerites']

        pdf_file = request.FILES['arquivo_holerite']
        pacotes_unidades, nao_identificados = processar_e_agrupar_anexos_por_unidade(pdf_file)

        # Converte bytes para HEX para permitir salvamento na sessão do Django
        pacotes_serializaveis = []
        for p in pacotes_unidades:
            anexos_hex = []
            for item in p['anexos_pdf']:
                anexos_hex.append({
                    'colaborador': item['colaborador'],
                    'nome_arquivo': item['nome_arquivo'],
                    'pdf_hex': item['pdf_bytes'].hex() if isinstance(item['pdf_bytes'], bytes) else item['pdf_bytes']
                })
            pacotes_serializaveis.append({
                'unidade': p['unidade'],
                'email_gerente': p['email_gerente'],
                'competencia': p.get('competencia', '09/2026'),
                'total_holerites': p['total_holerites'],
                'colaboradores': p['colaboradores'],
                'anexos_pdf': anexos_hex
            })

        request.session['pacotes_holerites'] = pacotes_serializaveis
        
        # Guarda temporariamente as folhas não identificadas para exibição
        request.session['nao_identificados'] = [
            {'pagina': item['pagina'], 'nome_arquivo': item['nome_arquivo']} 
            for item in nao_identificados
        ]

        messages.success(request, f"PDF fatiado com sucesso! {len(pacotes_unidades)} unidade(s) identificada(s).")
        return redirect('processar_holerites')

    # 4. RENDERIZAÇÃO DA PÁGINA (GET)
    context = {
        'titulo': 'Processamento de Contra-Cheques',
        'pacotes_unidades': request.session.get('pacotes_holerites', []),
        'nao_identificados': request.session.get('nao_identificados', []),
        'unidades_banco': Unidade.objects.all(),
    }

    return render(request, 'processar_holerites.html', context)