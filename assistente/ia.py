"""Escolha do provedor do chat.

Hoje só existe o provedor local `regras`. A integração com um modelo de IA por
API é OPCIONAL e FUTURA: para adicioná-la, crie uma classe com o mesmo método
`responder(mensagem, estado, hoje)` de `ProvedorRegras`, leia a chave de uma
variável de ambiente (nunca do código) e registre-a em `PROVEDORES`.
Regra obrigatória para qualquer provedor: alterações de dados só por meio de
`AcaoPendente` + confirmação do usuário.
"""

from __future__ import annotations

import logging

from assistente.chat import Provedor, ProvedorRegras

log = logging.getLogger(__name__)

PROVEDORES: dict[str, type] = {"regras": ProvedorRegras}


def obter_provedor(nome: str = "regras") -> Provedor:
    classe = PROVEDORES.get(nome)
    if classe is None:
        log.warning("Provedor de chat '%s' não disponível; usando regras locais.", nome)
        classe = ProvedorRegras
    return classe()
