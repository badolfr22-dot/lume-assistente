"""Pesquisa global em tarefas, metas, compromissos e anotações."""

from __future__ import annotations

from typing import Any

from assistente import db
from assistente import validacao as v

TIPOS = {
    "tarefas": "Tarefas",
    "metas": "Metas",
    "compromissos": "Compromissos",
    "anotacoes": "Anotações",
}

# Para cada tipo: colunas pesquisáveis e coluna de data (para o filtro de período).
_CAMPOS = {
    "tarefas": (("titulo", "descricao", "categoria"), "prazo"),
    "metas": (("titulo", "descricao"), "prazo"),
    "compromissos": (("titulo", "descricao", "local"), "data"),
    "anotacoes": (("titulo", "conteudo", "tags"), "substr(atualizado_em, 1, 10)"),
}

LIMITE_POR_TIPO = 50


def pesquisar(termo: str, tipos: list[str] | None = None, data_inicio: Any = None,
              data_fim: Any = None) -> dict[str, list[dict[str, Any]]]:
    """Devolve {tipo: [itens]}. Termo vazio gera erro de validação claro."""
    termo = v.texto_opcional(termo, "Pesquisa", v.LIMITE_TITULO)
    if len(termo) < 2:
        raise v.ErroValidacao("Digite pelo menos 2 caracteres para pesquisar.")
    tipos = tipos or list(TIPOS)
    if any(t not in TIPOS for t in tipos):
        raise v.ErroValidacao("Tipo de pesquisa inválido.")
    inicio = v.data_iso(data_inicio, "Data inicial")
    fim = v.data_iso(data_fim, "Data final")
    if inicio and fim and inicio > fim:
        raise v.ErroValidacao("A data inicial deve ser anterior à data final.")

    padrao = f"%{db.escapar_like(termo)}%"
    resultados: dict[str, list[dict[str, Any]]] = {}
    for tipo in tipos:
        colunas, coluna_data = _CAMPOS[tipo]  # nomes fixos, nunca vindos do usuário
        condicoes = ["usuario_id = ?", "(" + " OR ".join(db.contem(c) for c in colunas) + ")"]
        parametros: list[Any] = [db.usuario_atual(), *[padrao] * len(colunas)]
        if inicio:
            condicoes.append(f"{coluna_data} >= ?")
            parametros.append(inicio)
        if fim:
            condicoes.append(f"{coluna_data} <= ?")
            parametros.append(fim)
        parametros.append(LIMITE_POR_TIPO)
        resultados[tipo] = db.consultar(
            f"SELECT * FROM {tipo} WHERE {' AND '.join(condicoes)} ORDER BY id DESC LIMIT ?",
            tuple(parametros),
        )
    return resultados


def total(resultados: dict[str, list[dict[str, Any]]]) -> int:
    return sum(len(itens) for itens in resultados.values())
