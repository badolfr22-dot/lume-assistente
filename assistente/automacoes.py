"""Automações configuráveis com histórico de execuções.

Todas as ações são internas e seguras: só criam avisos dentro do app ou
resumos. Nenhuma automação exclui dados, conclui tarefas, altera compromissos
ou envia informações para fora do computador.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable

from assistente import configuracoes, db, notificacoes, repositorio
from assistente import validacao as v
from assistente.tempo import agora as _agora, agora_iso

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TipoAutomacao:
    nome: str
    descricao: str
    parametros: dict[str, tuple[str, int, int, int]]  # nome -> (rótulo, padrão, mínimo, máximo)


TIPOS: dict[str, TipoAutomacao] = {
    "tarefas_atrasadas": TipoAutomacao(
        "Avisar tarefas atrasadas",
        "Quando houver tarefas atrasadas, cria um aviso com a quantidade e os títulos.",
        {"minimo": ("Avisar a partir de quantas tarefas atrasadas", 1, 1, 50)},
    ),
    "prazo_proximo": TipoAutomacao(
        "Avisar prazos próximos",
        "Cria um aviso com as tarefas que vencem nos próximos dias.",
        {"dias": ("Quantos dias à frente", 2, 0, 30)},
    ),
    "resumo_diario": TipoAutomacao(
        "Resumo diário",
        "Gera um resumo do dia: tarefas pendentes, concluídas hoje, compromissos e metas.",
        {},
    ),
    "sugerir_prioritarias": TipoAutomacao(
        "Sugerir tarefas prioritárias",
        "Escolhe até N tarefas pendentes mais importantes e cria um aviso com elas.",
        {"quantidade": ("Quantas tarefas sugerir", 3, 1, 10)},
    ),
}


@dataclass
class Resultado:
    situacao: str  # ok, sem_acao, erro
    mensagem: str


def _validar_parametros(tipo: str, parametros: dict[str, Any] | None) -> dict[str, int]:
    definicao = TIPOS[tipo].parametros
    parametros = parametros or {}
    limpos = {}
    for chave, (rotulo, padrao, minimo, maximo) in definicao.items():
        limpos[chave] = v.inteiro(parametros.get(chave, padrao), rotulo, minimo, maximo)
    return limpos


def criar(nome: str, tipo: str, parametros: dict[str, Any] | None = None, ativa: bool = True) -> int:
    nome = v.texto_obrigatorio(nome, "Nome da automação", v.LIMITE_CURTO)
    tipo = v.opcao(tipo, {k: t.nome for k, t in TIPOS.items()}, "Tipo")
    limpos = _validar_parametros(tipo, parametros)
    if db.consultar_um("SELECT id FROM automacoes WHERE usuario_id = ? AND lower(nome) = lower(?)",
                       (db.usuario_atual(), nome)):
        raise v.ErroValidacao("Já existe uma automação com esse nome.")
    return db.inserir(
        "INSERT INTO automacoes (usuario_id, nome, tipo, parametros, ativa, criado_em) VALUES (?, ?, ?, ?, ?, ?)",
        (db.usuario_atual(), nome, tipo, json.dumps(limpos), int(ativa), agora_iso()),
    )


def listar() -> list[dict[str, Any]]:
    linhas = db.consultar("SELECT * FROM automacoes WHERE usuario_id = ? ORDER BY id", (db.usuario_atual(),))
    for linha in linhas:
        linha["parametros"] = json.loads(linha["parametros"] or "{}")
    return linhas


def obter(id_: int) -> dict[str, Any] | None:
    linha = db.consultar_um("SELECT * FROM automacoes WHERE id = ? AND usuario_id = ?",
                            (int(id_), db.usuario_atual()))
    if linha:
        linha["parametros"] = json.loads(linha["parametros"] or "{}")
    return linha


def definir_ativa(id_: int, ativa: bool) -> bool:
    return db.executar("UPDATE automacoes SET ativa = ? WHERE id = ? AND usuario_id = ?",
                       (int(ativa), int(id_), db.usuario_atual())) > 0


def excluir(id_: int) -> bool:
    """Exclui só a regra de automação (o histórico é mantido)."""
    return db.executar("DELETE FROM automacoes WHERE id = ? AND usuario_id = ?", (int(id_), db.usuario_atual())) > 0


# --- Ações ---------------------------------------------------------------------

def _avisar(auto: dict, titulo: str, mensagem: str, hoje: date) -> None:
    """Cria o aviso no app, a menos que o usuário tenha desligado avisos de automações."""
    if "automacoes" in configuracoes.obter("notificacoes_tipos"):
        notificacoes.registrar("automacoes", titulo, mensagem, f"auto:{auto['id']}:{hoje.isoformat()}")


def _acao_atrasadas(auto: dict, hoje: date) -> Resultado:
    atrasadas = repositorio.listar_tarefas("atrasadas", hoje=hoje)
    if len(atrasadas) < auto["parametros"].get("minimo", 1):
        return Resultado("sem_acao", "Nenhuma tarefa atrasada acima do limite.")
    titulos = ", ".join(t["titulo"] for t in atrasadas[:5])
    _avisar(auto, f"{len(atrasadas)} tarefa(s) atrasada(s)", titulos, hoje)
    return Resultado("ok", f"{len(atrasadas)} tarefa(s) atrasada(s): {titulos}.")


def _acao_prazo(auto: dict, hoje: date) -> Resultado:
    limite = (hoje + timedelta(days=auto["parametros"].get("dias", 2))).isoformat()
    proximas = [t for t in repositorio.listar_tarefas("pendentes", hoje=hoje)
                if t["prazo"] and hoje.isoformat() <= t["prazo"] <= limite]
    if not proximas:
        return Resultado("sem_acao", "Nenhuma tarefa com prazo próximo.")
    _avisar(auto, f"{len(proximas)} tarefa(s) com prazo próximo", ", ".join(t["titulo"] for t in proximas[:5]), hoje)
    return Resultado("ok", f"{len(proximas)} tarefa(s) vencendo até {limite}.")


def resumo_do_dia(hoje: date) -> str:
    ind = repositorio.indicadores(hoje)
    return (f"Pendentes: {ind['tarefas_pendentes']} (atrasadas: {ind['tarefas_atrasadas']}, "
            f"para hoje: {ind['tarefas_hoje']}). Concluídas hoje: {ind['tarefas_concluidas_hoje']}. "
            f"Compromissos hoje: {ind['compromissos_hoje']}. Progresso médio das metas: {ind['metas_media']}%.")


def _acao_resumo(auto: dict, hoje: date) -> Resultado:
    texto = resumo_do_dia(hoje)
    _avisar(auto, f"Resumo do dia {hoje.strftime('%d/%m')}", texto, hoje)
    return Resultado("ok", texto)


def _acao_prioritarias(auto: dict, hoje: date) -> Resultado:
    from assistente import planejador  # import local evita ciclo

    pendentes = repositorio.listar_tarefas("pendentes", hoje=hoje)
    if not pendentes:
        return Resultado("sem_acao", "Não há tarefas pendentes.")
    escolhidas = planejador.ordenar_tarefas(pendentes, hoje)[: auto["parametros"].get("quantidade", 3)]
    titulos = ", ".join(t["titulo"] for t in escolhidas)
    _avisar(auto, "Tarefas prioritárias sugeridas", titulos, hoje)
    return Resultado("ok", f"Sugeridas: {titulos}.")


ACOES: dict[str, Callable[[dict, date], Resultado]] = {
    "tarefas_atrasadas": _acao_atrasadas,
    "prazo_proximo": _acao_prazo,
    "resumo_diario": _acao_resumo,
    "sugerir_prioritarias": _acao_prioritarias,
}


def _registrar_historico(auto: dict, resultado: Resultado, momento: str) -> None:
    db.executar(
        "INSERT INTO automacoes_historico (usuario_id, automacao_id, nome_automacao, executado_em, situacao, "
        "mensagem) VALUES (?, ?, ?, ?, ?, ?)",
        (db.usuario_atual(), auto["id"], auto["nome"], momento, resultado.situacao, resultado.mensagem[:500]),
    )
    db.executar("UPDATE automacoes SET ultima_execucao = ? WHERE id = ? AND usuario_id = ?",
                (momento, auto["id"], db.usuario_atual()))


def executar(id_: int, agora: datetime | None = None) -> Resultado:
    auto = obter(id_)
    if auto is None:
        raise v.ErroValidacao("Automação não encontrada.")
    agora = agora or _agora()
    try:
        resultado = ACOES[auto["tipo"]](auto, agora.date())
    except Exception as exc:  # o erro vai para o histórico, sem derrubar o app
        log.exception("Falha na automação %s", auto["id"])
        resultado = Resultado("erro", f"Falha ao executar ({type(exc).__name__}).")
    _registrar_historico(auto, resultado, agora.isoformat(sep=" "))
    return resultado


def executar_pendentes(agora: datetime | None = None) -> list[tuple[str, Resultado]]:
    """Executa as automações ativas que ainda não rodaram hoje (uma vez por dia)."""
    agora = agora or _agora()
    hoje_iso = agora.date().isoformat()
    executadas = []
    for auto in listar():
        if auto["ativa"] and not (auto["ultima_execucao"] or "").startswith(hoje_iso):
            executadas.append((auto["nome"], executar(auto["id"], agora)))
    return executadas


def historico(limite: int = 100) -> list[dict[str, Any]]:
    return db.consultar("SELECT * FROM automacoes_historico WHERE usuario_id = ? "
                        "ORDER BY executado_em DESC, id DESC LIMIT ?", (db.usuario_atual(), int(limite)))


def limpar_historico() -> int:
    return db.executar("DELETE FROM automacoes_historico WHERE usuario_id = ?", (db.usuario_atual(),))

