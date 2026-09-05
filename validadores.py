"""
validadores.py
Funções de validação de dados de entrada do usuário.
"""

import re


def validar_nome(nome: str) -> str:
    """
    Valida o nome do visitante.
    Retorna o nome limpo (sem espaços extras) se válido,
    ou lança ValueError com mensagem explicativa.
    """
    nome = nome.strip()
    if not nome:
        raise ValueError("Informe o nome do visitante.")
    if len(nome) < 2:
        raise ValueError("O nome deve ter pelo menos 2 caracteres.")
    if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ' \-]+$", nome):
        raise ValueError("O nome deve conter apenas letras e espaços.")
    return nome


def validar_telefone(telefone: str) -> str:
    """
    Valida e normaliza o telefone do visitante.
    Aceita formatos como (11) 91234-5678, 11912345678, 11 91234-5678 etc.
    Retorna apenas os dígitos se válido, ou lança ValueError.
    """
    apenas_digitos = re.sub(r"\D", "", telefone)
    if not apenas_digitos:
        raise ValueError("Informe o telefone do visitante.")
    if len(apenas_digitos) < 10 or len(apenas_digitos) > 11:
        raise ValueError(
            "Telefone inválido. Use DDD + número (10 ou 11 dígitos)."
        )
    return apenas_digitos


def formatar_telefone(apenas_digitos: str) -> str:
    """Formata uma string de dígitos como (DD) DDDDD-DDDD ou (DD) DDDD-DDDD."""
    d = re.sub(r"\D", "", apenas_digitos)
    if len(d) == 11:
        return f"({d[0:2]}) {d[2:7]}-{d[7:11]}"
    if len(d) == 10:
        return f"({d[0:2]}) {d[2:6]}-{d[6:10]}"
    return apenas_digitos
