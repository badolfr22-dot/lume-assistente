"""Sugestões inteligentes geradas por regras locais a partir dos dados reais.

Cada sugestão traz o motivo, para o usuário entender de onde ela veio.
Nenhuma sugestão altera dados.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from assistente import configuracoes, repositorio
from assistente.tempo import formatar_data, hoje as _hoje


@dataclass(frozen=True)
class Sugestao:
    tipo: str
    icone: str
    titulo: str
    motivo: str
    pagina: str  # página do app onde o usuário pode agir


def gerar(hoje: date | None = None, config: dict | None = None) -> list[Sugestao]:
    hoje = hoje or _hoje()
    config = config or configuracoes.obter_todas()
    if not config.get("sugestoes_ativas", True):
        return []
    tipos = set(config.get("sugestoes_tipos", configuracoes.TIPOS_SUGESTAO))
    fmt = config.get("formato_data", "dd/mm/aaaa")
    sugestoes: list[Sugestao] = []

    pendentes = repositorio.listar_tarefas("pendentes", hoje=hoje)
    atrasadas = [t for t in pendentes if repositorio.esta_atrasada(t, hoje)]
    para_hoje = [t for t in pendentes if t["prazo"] == hoje.isoformat()]

    if "atrasadas" in tipos and atrasadas:
        mais_antiga = min(atrasadas, key=lambda t: t["prazo"])
        sugestoes.append(Sugestao(
            "atrasadas", "⏰",
            f"Você tem {len(atrasadas)} tarefa(s) atrasada(s). Comece por “{mais_antiga['titulo']}”.",
            f"É a tarefa com prazo mais antigo ({formatar_data(mais_antiga['prazo'], fmt)}).",
            "tarefas",
        ))
    if "hoje" in tipos and para_hoje:
        sugestoes.append(Sugestao(
            "hoje", "📌",
            f"{len(para_hoje)} tarefa(s) vencem hoje. Reserve um tempo no planejador.",
            "Essas tarefas têm prazo igual à data de hoje.",
            "planejador",
        ))
    if "prioridade" in tipos:
        ids_atrasadas = {t["id"] for t in atrasadas}  # conjunto: busca O(1) em vez de percorrer a lista
        altas = [t for t in pendentes if t["prioridade"] == "alta" and t["id"] not in ids_atrasadas]
        if altas:
            primeira = altas[0]
            sugestoes.append(Sugestao(
                "prioridade", "🔥",
                f"Priorize “{primeira['titulo']}” (prioridade alta).",
                f"Há {len(altas)} tarefa(s) de alta prioridade em aberto; esta tem o prazo mais próximo.",
                "tarefas",
            ))
    if "metas" in tipos:
        limite = (hoje + timedelta(days=14)).isoformat()
        for meta in repositorio.listar_metas("ativas"):
            if meta["prazo"] and hoje.isoformat() <= meta["prazo"] <= limite and meta["progresso"] < 50:
                sugestoes.append(Sugestao(
                    "metas", "🎯",
                    f"A meta “{meta['titulo']}” está em {meta['progresso']}% e vence em "
                    f"{formatar_data(meta['prazo'], fmt)}.",
                    "Meta com menos de 50% de progresso e prazo nos próximos 14 dias.",
                    "metas",
                ))
                break
    if "agenda" in tipos:
        compromissos = repositorio.compromissos_do_dia(hoje)
        if compromissos:
            primeiro = compromissos[0]
            sugestoes.append(Sugestao(
                "agenda", "📅",
                f"Hoje você tem {len(compromissos)} compromisso(s). O primeiro é “{primeiro['titulo']}” "
                f"às {primeiro['hora_inicio']}.",
                "Compromissos cadastrados na agenda para hoje.",
                "agenda",
            ))

    if not sugestoes and not pendentes:
        sugestoes.append(Sugestao(
            "vazio", "✨",
            "Nenhuma tarefa em aberto. Que tal cadastrar o que precisa fazer esta semana?",
            "Não há tarefas pendentes no banco de dados.",
            "tarefas",
        ))
    return sugestoes[: int(config.get("sugestoes_maximo", 5))]
