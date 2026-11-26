"""Validação de CPF e CNPJ (dígitos verificadores) e normalização de campos numéricos."""
import re

from django.core.exceptions import ValidationError


def somente_digitos(valor):
    return re.sub(r'\D', '', valor or '')


def _digito(base, pesos):
    resto = sum(int(d) * p for d, p in zip(base, pesos)) % 11
    return '0' if resto < 2 else str(11 - resto)


def cpf_valido(numero):
    if len(numero) != 11 or len(set(numero)) == 1:
        return False
    d1 = _digito(numero[:9], range(10, 1, -1))
    d2 = _digito(numero[:9] + d1, range(11, 1, -1))
    return numero[9:] == d1 + d2


def cnpj_valido(numero):
    if len(numero) != 14 or len(set(numero)) == 1:
        return False
    d1 = _digito(numero[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = _digito(numero[:12] + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return numero[12:] == d1 + d2


def validar_cpf(valor):
    """Devolve o CPF só com dígitos ou levanta ValidationError."""
    numero = somente_digitos(valor)
    if not cpf_valido(numero):
        raise ValidationError('Informe um CPF válido.')
    return numero


def validar_cnpj(valor):
    """Devolve o CNPJ só com dígitos ou levanta ValidationError."""
    numero = somente_digitos(valor)
    if not cnpj_valido(numero):
        raise ValidationError('Informe um CNPJ válido.')
    return numero


def validar_cep(valor):
    numero = somente_digitos(valor)
    if len(numero) != 8:
        raise ValidationError('Informe um CEP com 8 dígitos.')
    return numero
