import re

from django.core.exceptions import ValidationError


def somente_digitos(valor):
    """Remove tudo que nao for digito (mascara de CNPJ, CEP, telefone)."""
    return re.sub(r'\D', '', valor or '')


def validar_cnpj(valor):
    """Confere tamanho e digitos verificadores do CNPJ (so numeros)."""
    cnpj = somente_digitos(valor)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        raise ValidationError('Informe um CNPJ válido com 14 dígitos.')

    def digito(base, pesos):
        soma = sum(int(n) * p for n, p in zip(base, pesos))
        resto = soma % 11
        return '0' if resto < 2 else str(11 - resto)

    primeiro = digito(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    segundo = digito(cnpj[:12] + primeiro, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    if cnpj[12:] != primeiro + segundo:
        raise ValidationError('Informe um CNPJ válido com 14 dígitos.')


def validar_cep(valor):
    if len(somente_digitos(valor)) != 8:
        raise ValidationError('Informe um CEP com 8 dígitos.')


def validar_telefone(valor):
    if len(somente_digitos(valor)) not in (10, 11):
        raise ValidationError('Informe o telefone com DDD (10 ou 11 dígitos).')
