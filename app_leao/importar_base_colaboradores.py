from django.core.management.base import BaseCommand
from app_leao.models import Colaborador

BASE_DADOS = [
    {"nome": "ABRAAO CAMPOS DA COSTA", "unidade": "AEROPORTO", "email": None, "status": "ATIVO"},
    {"nome": "ERCILIA MARIANA SANTANA LEAL", "unidade": "AEROPORTO", "email": None, "status": "ATIVO"},
    {"nome": "JHENNIFER DE SOUZA LOBATO", "unidade": "AEROPORTO", "email": None, "status": "ATIVO"},
    {"nome": "TAINA DA SILVA RODRIGUES", "unidade": "AEROPORTO", "email": None, "status": "ATIVO"},
    {"nome": "DAFINE ELANE DE ALMEIDA FIEL", "unidade": "CASTANHEIRA", "email": None, "status": "ATIVO"},
    {"nome": "LUANNY CRISTINA LIMA BOMFIM", "unidade": "CASTANHEIRA", "email": "cristina.lu0987@gmail.com", "status": "ATIVO"},
    {"nome": "PEDRO HENRIQUE FERREIRA DE OLIVEIRA", "unidade": "CASTANHEIRA", "email": "pedrohfoliveira123@gmail.com", "status": "ATIVO"},
    {"nome": "THAYLIZE NADINE LÚCIO MACHADO", "unidade": "CASTANHEIRA", "email": "thaylucio9@gmail.com", "status": "ATIVO"},
    {"nome": "BEATRIZ ALMEIDA GUIMARAES", "unidade": "CASTANHEIRA", "email": None, "status": "ATIVO"},
    {"nome": "LEONARDO SOARES DA SILVA", "unidade": "CASTANHEIRA", "email": "leosilvaraiol2017@gmail.com", "status": "ATIVO"},
    {"nome": "DAVI COSTA RICARTE DE OLIVEIRA", "unidade": "BAENÃO", "email": None, "status": "ATIVO"},
    {"nome": "JORGE WALLACE DINIZ VALADARES", "unidade": "BAENÃO", "email": None, "status": "INATIVO"},
    {"nome": "RAFAELA NUNES NOVAES", "unidade": "BAENÃO", "email": None, "status": "INATIVO"},
    {"nome": "RAINARY LOPES REZENDE", "unidade": "BAENÃO", "email": None, "status": "ATIVO"},
    {"nome": "THAMYRIS DE OLIVEIRA EVANGELISTA", "unidade": "BAENÃO", "email": None, "status": "ATIVO"},
    {"nome": "VITORYA CAROLYNE LIMA DO NASCIMENTO", "unidade": "BAENÃO", "email": "vitoryalima8432@gmail.com", "status": "ATIVO"},
    {"nome": "JHULLIANY AMARAL DIAS", "unidade": "BAENÃO", "email": None, "status": "ATIVO"},
    {"nome": "HERCULES AUGUSTO BRABO PINA DE CARVALHO", "unidade": "BAENÃO", "email": None, "status": "ATIVO"},
    {"nome": "ASHLEY MONTEIRO GUEDES DA SILVA", "unidade": "PÁTIO", "email": None, "status": "ATIVO"},
    {"nome": "CYNTYA THALIA POMPEU VIANA", "unidade": "PÁTIO", "email": None, "status": "ATIVO"},
    {"nome": "RUBENS VINICIUS SANTANA DE NAZARE", "unidade": "PÁTIO", "email": None, "status": "ATIVO"},
    {"nome": "SILVIA HIRIANE SOUZA DE SOUZA", "unidade": "PÁTIO", "email": "hirianesouza@icloud.com", "status": "ATIVO"},
    {"nome": "PABLO LUIS ALVES VALENTE", "unidade": "PÁTIO", "email": None, "status": "ATIVO"},
]

class Command(BaseCommand):
    help = 'Popula o banco de dados com a lista inicial de colaboradores'

    def handle(self, *args, **kwargs):
        cadastrados = 0
        atualizados = 0

        for item in BASE_DADOS:
            colab, created = Colaborador.objects.update_or_create(
                nome=item["nome"],
                defaults={
                    "unidade": item["unidade"],
                    "email": item["email"],
                    "status": item["status"],
                }
            )
            if created:
                cadastrados += 1
            else:
                atualizados += 1

        self.stdout.write(self.style.SUCCESS(f'Sucesso! {cadastrados} novos colaboradores cadastrados e {atualizados} atualizados.'))