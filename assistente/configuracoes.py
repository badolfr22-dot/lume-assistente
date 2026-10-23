"""Configurações do aplicativo (aparência, formatos, notificações, sugestões).

Ficam na tabela `configuracoes`. Restaurar o padrão apaga só essa tabela:
tarefas, metas, compromissos, anotações e preferências não são tocados.
"""

from __future__ import annotations

import json
from typing import Any

from assistente import db
from assistente import validacao as v
from assistente.tempo import FORMATOS_DATA, FORMATOS_HORA, agora_iso

TIPOS_SUGESTAO = {
    "atrasadas": "Tarefas atrasadas",
    "hoje": "Tarefas que vencem hoje",
    "prioridade": "Tarefas de alta prioridade",
    "metas": "Metas com prazo próximo",
    "agenda": "Compromissos do dia",
}
TIPOS_NOTIFICACAO = {
    "lembretes": "Lembretes que você criou",
    "prazos": "Tarefas perto do prazo",
    "compromissos": "Compromissos que vão começar",
    "automacoes": "Avisos gerados por automações",
}
TEMAS = {"claro": "Claro", "escuro": "Escuro"}

PADROES: dict[str, Any] = {
    "nome_assistente": "Lume",
    "nome_usuario": "",
    "tema": "claro",
    "formato_data": "dd/mm/aaaa",
    "formato_hora": "24h",
    "notificacoes_tipos": list(TIPOS_NOTIFICACAO),
    "notificacoes_antecedencia_dias": 1,
    "notificacoes_compromisso_min": 30,
    "sugestoes_ativas": True,
    "sugestoes_tipos": list(TIPOS_SUGESTAO),
    "sugestoes_maximo": 5,
}


def _validar(chave: str, valor: Any) -> Any:
    if chave not in PADROES:
        raise v.ErroValidacao(f"Configuração desconhecida: {chave}.")
    if chave in ("nome_assistente",):
        return v.texto_obrigatorio(valor, "Nome do assistente", 40)
    if chave == "nome_usuario":
        return v.texto_opcional(valor, "Seu nome", 40)
    if chave == "tema":
        return v.opcao(valor, TEMAS, "Tema")
    if chave == "formato_data":
        return v.opcao(valor, {k: k for k in FORMATOS_DATA}, "Formato de data")
    if chave == "formato_hora":
        return v.opcao(valor, {k: k for k in FORMATOS_HORA}, "Formato de hora")
    if chave in ("notificacoes_tipos", "sugestoes_tipos"):
        validos = TIPOS_NOTIFICACAO if chave == "notificacoes_tipos" else TIPOS_SUGESTAO
        lista = list(valor or [])
        invalidos = [item for item in lista if item not in validos]
        if invalidos:
            raise v.ErroValidacao("Tipo inválido na lista selecionada.")
        return lista
    if chave == "notificacoes_antecedencia_dias":
        return v.inteiro(valor, "Antecedência (dias)", 0, 30)
    if chave == "notificacoes_compromisso_min":
        return v.inteiro(valor, "Aviso de compromisso (minutos)", 5, 240)
    if chave == "sugestoes_ativas":
        return bool(valor)
    if chave == "sugestoes_maximo":
        return v.inteiro(valor, "Máximo de sugestões", 1, 10)
    return valor  # pragma: no cover


def obter_todas() -> dict[str, Any]:
    valores = dict(PADROES)
    for linha in db.consultar("SELECT chave, valor FROM configuracoes WHERE usuario_id = ?", (db.usuario_atual(),)):
        if linha["chave"] in PADROES:
            try:
                valores[linha["chave"]] = json.loads(linha["valor"])
            except json.JSONDecodeError:
                pass  # valor corrompido: mantém o padrão
    return valores


def obter(chave: str) -> Any:
    return obter_todas().get(chave, PADROES.get(chave))


def salvar(alteracoes: dict[str, Any]) -> dict[str, Any]:
    limpos = {chave: _validar(chave, valor) for chave, valor in alteracoes.items()}
    momento = agora_iso()
    with db.conectar() as con:
        for chave, valor in limpos.items():
            con.execute(
                "INSERT INTO configuracoes (usuario_id, chave, valor, atualizado_em) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(usuario_id, chave) DO UPDATE SET valor = excluded.valor, "
                "atualizado_em = excluded.atualizado_em",
                (db.usuario_atual(), chave, json.dumps(valor, ensure_ascii=False), momento),
            )
    return obter_todas()


def restaurar_padroes() -> None:
    db.executar("DELETE FROM configuracoes WHERE usuario_id = ?", (db.usuario_atual(),))
