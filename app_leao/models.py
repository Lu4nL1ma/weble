from django.db import models

class Unidade(models.Model):
    cnpj = models.CharField(max_length=18, unique=True, verbose_name="CNPJ da Filial")
    nome = models.CharField(max_length=150, unique=True, verbose_name="Nome da Unidade / Loja")
    email_gerente = models.EmailField(verbose_name="E-mail do Gerente / Supervisão")

    class Meta:
        verbose_name = "Unidade"
        verbose_name_plural = "Unidades"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} - {self.cnpj} ({self.email_gerente})"


class Colaborador(models.Model):
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
    ]

    VINCULO_CHOICES = [
        ('CELETISTA', 'Celetista'),
        ('ESTAGIARIO', 'Estagiário'),
        ('PJ', 'Pessoa Jurídica'),
        ('OUTRO', 'Outro'),
    ]

    nome = models.CharField(max_length=255, verbose_name="Nome Completo", unique=True)
    unidade = models.CharField(max_length=150, verbose_name="Unidade / Loja", default="Leão Azul")
    email = models.EmailField(verbose_name="E-mail", blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ATIVO', verbose_name="Status")
    cpf = models.CharField(max_length=14, verbose_name="CPF", blank=True, null=True)
    cargo = models.CharField(max_length=150, verbose_name="Cargo", blank=True, null=True)
    
    # NOVOS CAMPOS ADICIONADOS DA PLANILHA:
    pix = models.CharField(max_length=100, verbose_name="Chave Pix", blank=True, null=True)
    vinculo = models.CharField(max_length=50, choices=VINCULO_CHOICES, default='CELETISTA', verbose_name="Vínculo Empregatício", blank=True, null=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Colaborador"
        verbose_name_plural = "Colaboradores"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.unidade})"