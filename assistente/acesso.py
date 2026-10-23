"""Senha de acesso opcional para quando o app for publicado.

Uso local: deixe ASSISTENTE_SENHA_ACESSO vazio e não haverá tela de acesso.
Publicação: defina a variável no servidor (nunca no código nem no Git).
Isto é uma proteção básica para um único usuário; não substitui HTTPS.
"""

from __future__ import annotations

import hmac
import time

TENTATIVAS_MAXIMAS = 5
BLOQUEIO_SEGUNDOS = 60


def senha_confere(digitada: str, esperada: str) -> bool:
    if not esperada:
        return True
    return hmac.compare_digest(digitada.encode("utf-8"), esperada.encode("utf-8"))


class ControleTentativas:
    """Limita tentativas erradas por sessão para dificultar tentativa e erro."""

    def __init__(self) -> None:
        self.erros = 0
        self.bloqueado_ate = 0.0

    def bloqueado(self, agora: float | None = None) -> bool:
        return (agora or time.monotonic()) < self.bloqueado_ate

    def registrar_erro(self, agora: float | None = None) -> None:
        self.erros += 1
        if self.erros >= TENTATIVAS_MAXIMAS:
            self.bloqueado_ate = (agora or time.monotonic()) + BLOQUEIO_SEGUNDOS
            self.erros = 0
