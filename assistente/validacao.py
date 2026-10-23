"""Validação e normalização dos dados recebidos do usuário."""

from __future__ import annotations

import re
from datetime import date, datetime, time


class ErroValidacao(ValueError):
    """Erro com mensagem clara, pronta para exibir na interface."""


PRIORIDADES = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}
STATUS_TAREFA = {"pendente": "Pendente", "em_andamento": "Em andamento", "concluida": "Concluída"}
RECORRENCIAS = {"nenhuma": "Nenhuma", "semanal": "Semanal", "mensal": "Mensal"}

LIMITE_TITULO = 120
LIMITE_TEXTO = 5000
LIMITE_CURTO = 60


def texto_obrigatorio(valor: object, campo: str, limite: int = LIMITE_TITULO) -> str:
    texto = texto_opcional(valor, campo, limite)
    if not texto:
        raise ErroValidacao(f"O campo “{campo}” é obrigatório.")
    return texto


def texto_opcional(valor: object, campo: str, limite: int = LIMITE_TEXTO) -> str:
    if valor is None:
        return ""
    if not isinstance(valor, str):
        valor = str(valor)
    # Remove caracteres de controle (exceto quebra de linha e tab).
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", valor).strip()
    if len(texto) > limite:
        raise ErroValidacao(f"O campo “{campo}” aceita no máximo {limite} caracteres.")
    return texto


def opcao(valor: object, opcoes: dict[str, str], campo: str) -> str:
    chave = str(valor or "").strip().lower()
    if chave not in opcoes:
        raise ErroValidacao(f"Valor inválido para “{campo}”. Use: {', '.join(opcoes.values())}.")
    return chave


def data_iso(valor: object, campo: str, obrigatoria: bool = False) -> str | None:
    """Aceita date, 'AAAA-MM-DD' ou 'DD/MM/AAAA' e devolve 'AAAA-MM-DD'."""
    if valor in (None, ""):
        if obrigatoria:
            raise ErroValidacao(f"O campo “{campo}” é obrigatório.")
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    raise ErroValidacao(f"Data inválida em “{campo}”. Use o formato DD/MM/AAAA.")


def hora_iso(valor: object, campo: str) -> str:
    """Aceita time ou 'HH:MM' e devolve 'HH:MM'."""
    if isinstance(valor, time):
        return valor.strftime("%H:%M")
    texto = str(valor or "").strip()
    try:
        return datetime.strptime(texto, "%H:%M").strftime("%H:%M")
    except ValueError:
        raise ErroValidacao(f"Horário inválido em “{campo}”. Use o formato HH:MM.") from None


def inteiro(valor: object, campo: str, minimo: int, maximo: int) -> int:
    try:
        numero = int(valor)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ErroValidacao(f"O campo “{campo}” deve ser um número inteiro.") from None
    if not minimo <= numero <= maximo:
        raise ErroValidacao(f"O campo “{campo}” deve estar entre {minimo} e {maximo}.")
    return numero


# --- Proteção da memória controlada contra dados sensíveis -----------------

_PALAVRAS_SENSIVEIS = re.compile(
    r"senha|password|passwd|token|api[\s_-]?key|chave\s+de\s+api|secret|segredo|"
    r"\bcpf\b|\brg\b|cart[aã]o\s+de\s+cr[eé]dito|\bcvv\b|\bpin\b",
    re.IGNORECASE,
)
_PADROES_SENSIVEIS = [
    re.compile(r"\b(?:\d[ .-]?){13,19}\b"),  # parece número de cartão
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),  # parece CPF
    re.compile(r"\b(sk|pk|ghp|gho|xox[bap])[-_][A-Za-z0-9_-]{10,}"),  # prefixos comuns de tokens
    re.compile(r"\b[A-Za-z0-9+/_-]{32,}={0,2}\b"),  # sequência longa parecida com chave
]


def parece_sensivel(*textos: str) -> bool:
    for texto in textos:
        if _PALAVRAS_SENSIVEIS.search(texto):
            return True
        if any(padrao.search(texto) for padrao in _PADROES_SENSIVEIS):
            return True
    return False
