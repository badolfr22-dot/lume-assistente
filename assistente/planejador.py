"""Planejador diário com regras locais.

Regras de ordenação (nesta ordem):
1. Posição definida manualmente pelo usuário, se houver.
2. Tarefas atrasadas primeiro.
3. Prazo mais próximo (sem prazo vai por último).
4. Prioridade (alta > média > baixa).
5. Menor duração estimada (ajuda a ganhar ritmo).

O planejador só sugere: nunca conclui tarefas nem altera compromissos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from assistente import db, preferencias, repositorio
from assistente import validacao as v
from assistente.tempo import hora_de_minutos, minutos

PESO_PRIORIDADE = {"alta": 0, "media": 1, "baixa": 2}
NOME_PRIORIDADE = {"alta": "alta", "media": "média", "baixa": "baixa"}
JANELA_DIAS = 3  # tarefas que vencem nos próximos dias também entram como candidatas
INICIO_PADRAO = "08:00"
FIM_PADRAO = "18:00"


@dataclass
class ItemPlano:
    tipo: str  # "tarefa" ou "compromisso"
    id: int
    titulo: str
    inicio: str
    fim: str
    explicacao: str
    atrasada: bool = False


@dataclass
class Plano:
    dia: date
    itens: list[ItemPlano] = field(default_factory=list)
    nao_couberam: list[dict[str, Any]] = field(default_factory=list)
    conflitos: list[tuple[dict[str, Any], dict[str, Any]]] = field(default_factory=list)
    atrasadas: list[dict[str, Any]] = field(default_factory=list)
    ordem_tarefas: list[int] = field(default_factory=list)


def _chave(tarefa: dict[str, Any], dia: date, ordem_manual: dict[int, int]) -> tuple:
    manual = ordem_manual.get(tarefa["id"])
    atrasada = repositorio.esta_atrasada(tarefa, dia)
    return (
        0 if manual is not None else 1,
        manual if manual is not None else 0,
        0 if atrasada else 1,
        tarefa["prazo"] is None,
        tarefa["prazo"] or "",
        PESO_PRIORIDADE.get(tarefa["prioridade"], 1),
        tarefa.get("duracao_min") or 30,
        tarefa["id"],
    )


def ordenar_tarefas(tarefas: list[dict[str, Any]], dia: date,
                    ordem_manual: dict[int, int] | None = None) -> list[dict[str, Any]]:
    ordem_manual = ordem_manual or {}
    return sorted(tarefas, key=lambda t: _chave(t, dia, ordem_manual))


def explicar(tarefa: dict[str, Any], dia: date, manual: bool) -> str:
    motivos: list[str] = []
    if manual:
        motivos.append("posição definida por você")
    if repositorio.esta_atrasada(tarefa, dia):
        atraso = (dia - date.fromisoformat(tarefa["prazo"])).days
        motivos.append(f"está atrasada há {atraso} dia(s)")
    elif tarefa["prazo"] == dia.isoformat():
        motivos.append("vence hoje")
    elif tarefa["prazo"]:
        dias = (date.fromisoformat(tarefa["prazo"]) - dia).days
        motivos.append(f"vence em {dias} dia(s)")
    else:
        motivos.append("não tem prazo definido")
    motivos.append(f"prioridade {NOME_PRIORIDADE.get(tarefa['prioridade'], tarefa['prioridade'])}")
    duracao = tarefa.get("duracao_min") or 30
    if duracao <= 20:
        motivos.append(f"é curta ({duracao} min)")
    else:
        motivos.append(f"duração estimada de {duracao} min")
    return "Sugerida aqui porque " + ", ".join(motivos) + "."


def encontrar_conflitos(compromissos: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Pares de compromissos do mesmo dia cujos horários se sobrepõem."""
    ordenados = sorted(compromissos, key=lambda c: (c["data"], c["hora_inicio"]))
    conflitos = []
    for i, a in enumerate(ordenados):
        for b in ordenados[i + 1:]:
            if b["data"] != a["data"]:
                continue
            if minutos(b["hora_inicio"]) < minutos(a["hora_fim"]) and minutos(a["hora_inicio"]) < minutos(b["hora_fim"]):
                conflitos.append((a, b))
    return conflitos


def montar_plano(tarefas: list[dict[str, Any]], compromissos: list[dict[str, Any]], dia: date,
                 inicio: str = INICIO_PADRAO, fim: str = FIM_PADRAO,
                 ordem_manual: dict[int, int] | None = None, agora: datetime | None = None) -> Plano:
    """Função pura: recebe os dados e devolve o plano (fácil de testar)."""
    ordem_manual = ordem_manual or {}
    plano = Plano(dia=dia)
    plano.conflitos = encontrar_conflitos(compromissos)
    candidatas = [t for t in tarefas if t["status"] != "concluida"]
    plano.atrasadas = [t for t in candidatas if repositorio.esta_atrasada(t, dia)]
    ordenadas = ordenar_tarefas(candidatas, dia, ordem_manual)
    plano.ordem_tarefas = [t["id"] for t in ordenadas]

    blocos = sorted(((minutos(c["hora_inicio"]), minutos(c["hora_fim"]), c) for c in compromissos),
                    key=lambda b: b[0])
    for ini, fim_c, c in blocos:
        plano.itens.append(ItemPlano("compromisso", c["id"], c["titulo"], c["hora_inicio"], c["hora_fim"],
                                     "Compromisso fixo da agenda (não é alterado pelo planejador)."))

    cursor = minutos(inicio)
    limite = minutos(fim)
    if agora is not None and agora.date() == dia:
        atual = agora.hour * 60 + agora.minute
        cursor = max(cursor, -(-atual // 5) * 5)  # arredonda para cima, múltiplo de 5 min

    for tarefa in ordenadas:
        duracao = int(tarefa.get("duracao_min") or 30)
        inicio_t = cursor
        mudou = True
        while mudou:  # pula os compromissos que se sobrepõem ao intervalo
            mudou = False
            for ini, fim_c, _ in blocos:
                if inicio_t < fim_c and ini < inicio_t + duracao:
                    inicio_t = fim_c
                    mudou = True
        if inicio_t + duracao > limite:
            plano.nao_couberam.append(tarefa)
            continue
        plano.itens.append(ItemPlano(
            "tarefa", tarefa["id"], tarefa["titulo"], hora_de_minutos(inicio_t),
            hora_de_minutos(inicio_t + duracao), explicar(tarefa, dia, tarefa["id"] in ordem_manual),
            atrasada=repositorio.esta_atrasada(tarefa, dia),
        ))
        cursor = inicio_t + duracao

    plano.itens.sort(key=lambda item: (item.inicio, item.tipo != "compromisso"))
    return plano


# ---------------------------------------------------------------------------
# Integração com o banco
# ---------------------------------------------------------------------------


def tarefas_candidatas(dia: date) -> list[dict[str, Any]]:
    limite = (dia + timedelta(days=JANELA_DIAS)).isoformat()
    return [t for t in repositorio.listar_tarefas("pendentes", hoje=dia)
            if t["prazo"] is None or t["prazo"] <= limite]


def ordem_manual(dia: date) -> dict[int, int]:
    linhas = db.consultar("SELECT tarefa_id, posicao FROM plano_dia WHERE usuario_id = ? AND data = ?",
                          (db.usuario_atual(), dia.isoformat()))
    return {linha["tarefa_id"]: linha["posicao"] for linha in linhas}


def salvar_ordem(dia: date, ids_em_ordem: list[int]) -> None:
    uid = db.usuario_atual()
    with db.conectar() as con:
        con.execute("DELETE FROM plano_dia WHERE usuario_id = ? AND data = ?", (uid, dia.isoformat()))
        # O SELECT garante que só entram tarefas do próprio usuário.
        con.executemany(
            "INSERT INTO plano_dia (usuario_id, data, tarefa_id, posicao) "
            "SELECT ?, ?, id, ? FROM tarefas WHERE id = ? AND usuario_id = ?",
            [(uid, dia.isoformat(), pos, int(id_), uid) for pos, id_ in enumerate(ids_em_ordem)],
        )


def mover(dia: date, ordem_atual: list[int], tarefa_id: int, deslocamento: int) -> list[int]:
    if tarefa_id not in ordem_atual:
        raise v.ErroValidacao("Tarefa não está no plano.")
    nova = list(ordem_atual)
    i = nova.index(tarefa_id)
    j = max(0, min(len(nova) - 1, i + deslocamento))
    nova.insert(j, nova.pop(i))
    salvar_ordem(dia, nova)
    return nova


def limpar_ordem(dia: date) -> None:
    db.executar("DELETE FROM plano_dia WHERE usuario_id = ? AND data = ?", (db.usuario_atual(), dia.isoformat()))


def horario_trabalho() -> tuple[str, str]:
    inicio = preferencias.valor(*preferencias.CHAVE_INICIO_DIA, INICIO_PADRAO) or INICIO_PADRAO
    fim = preferencias.valor(*preferencias.CHAVE_FIM_DIA, FIM_PADRAO) or FIM_PADRAO
    if minutos(fim) <= minutos(inicio):
        return INICIO_PADRAO, FIM_PADRAO
    return inicio, fim


def plano_do_dia(dia: date, agora: datetime | None = None) -> Plano:
    inicio, fim = horario_trabalho()
    return montar_plano(tarefas_candidatas(dia), repositorio.compromissos_do_dia(dia), dia,
                        inicio, fim, ordem_manual(dia), agora)


def progresso_do_dia(dia: date) -> tuple[int, int]:
    """(concluídas no dia, total = concluídas no dia + pendentes que vencem até o dia)."""
    uid = db.usuario_atual()
    feitas = int(db.consultar_um(
        "SELECT COUNT(*) AS n FROM tarefas WHERE usuario_id = ? AND status = 'concluida' "
        "AND substr(concluida_em, 1, 10) = ?",
        (uid, dia.isoformat()),
    )["n"])
    abertas = int(db.consultar_um(
        "SELECT COUNT(*) AS n FROM tarefas WHERE usuario_id = ? AND status != 'concluida' "
        "AND prazo IS NOT NULL AND prazo <= ?",
        (uid, dia.isoformat()),
    )["n"])
    return feitas, feitas + abertas
