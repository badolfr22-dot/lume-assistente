"""CRUD de tarefas, metas, compromissos e anotações.

Cada função valida os dados antes de gravar. Nomes de colunas usados em SQL
vêm sempre de listas fixas deste arquivo, nunca do usuário. Toda consulta
filtra por `usuario_id`: uma pessoa nunca vê nem altera dados de outra.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from assistente import db
from assistente import validacao as v
from assistente.tempo import agora_iso, hoje as _hoje

uid = db.usuario_atual

# ---------------------------------------------------------------------------
# Utilitário interno
# ---------------------------------------------------------------------------


def _checar_campos(campos: dict[str, Any], permitidos: tuple[str, ...]) -> None:
    desconhecidas = set(campos) - set(permitidos)
    if desconhecidas:
        raise v.ErroValidacao(f"Campos não reconhecidos: {', '.join(sorted(desconhecidas))}.")


def _atualizar(tabela: str, colunas_permitidas: tuple[str, ...], id_: int, campos: dict[str, Any]) -> bool:
    _checar_campos(campos, colunas_permitidas)
    if not campos:
        return False
    campos = {**campos, "atualizado_em": agora_iso()}
    trecho = ", ".join(f"{coluna} = ?" for coluna in campos)  # colunas da lista fixa
    afetadas = db.executar(f"UPDATE {tabela} SET {trecho} WHERE id = ? AND usuario_id = ?",
                           (*campos.values(), int(id_), uid()))
    return afetadas > 0


def _obter(tabela: str, id_: int) -> dict[str, Any] | None:
    return db.consultar_um(f"SELECT * FROM {tabela} WHERE id = ? AND usuario_id = ?", (int(id_), uid()))


def _excluir(tabela: str, id_: int) -> bool:
    return db.executar(f"DELETE FROM {tabela} WHERE id = ? AND usuario_id = ?", (int(id_), uid())) > 0


# ---------------------------------------------------------------------------
# Tarefas
# ---------------------------------------------------------------------------

FILTROS_TAREFA = {
    "todas": "Todas",
    "pendentes": "Pendentes",
    "atrasadas": "Atrasadas",
    "hoje": "Para hoje",
    "concluidas": "Concluídas",
}
CAMPOS_TAREFA = ("titulo", "descricao", "prioridade", "prazo", "categoria", "status", "duracao_min")


def _validar_tarefa(dados: dict[str, Any], parcial: bool = False) -> dict[str, Any]:
    limpos: dict[str, Any] = {}
    if not parcial or "titulo" in dados:
        limpos["titulo"] = v.texto_obrigatorio(dados.get("titulo"), "Título")
    if "descricao" in dados:
        limpos["descricao"] = v.texto_opcional(dados.get("descricao"), "Descrição")
    if not parcial or "prioridade" in dados:
        limpos["prioridade"] = v.opcao(dados.get("prioridade", "media"), v.PRIORIDADES, "Prioridade")
    if "prazo" in dados:
        limpos["prazo"] = v.data_iso(dados.get("prazo"), "Prazo")
    if "categoria" in dados:
        limpos["categoria"] = v.texto_opcional(dados.get("categoria"), "Categoria", v.LIMITE_CURTO)
    if "status" in dados:
        limpos["status"] = v.opcao(dados.get("status"), v.STATUS_TAREFA, "Status")
    if "duracao_min" in dados:
        limpos["duracao_min"] = v.inteiro(dados.get("duracao_min"), "Duração estimada (min)", 5, 720)
    return limpos


def _existe_tarefa_igual(titulo: str, prazo: str | None, ignorar_id: int | None = None) -> bool:
    linha = db.consultar_um(
        "SELECT id FROM tarefas WHERE usuario_id = ? AND lower(titulo) = lower(?) AND prazo IS NOT DISTINCT FROM ? "
        "AND status != 'concluida' AND id != ?",
        (uid(), titulo, prazo, ignorar_id or -1),
    )
    return linha is not None


def criar_tarefa(titulo: str, descricao: str = "", prioridade: str = "media", prazo: Any = None,
                 categoria: str = "", duracao_min: int = 30, exemplo: bool = False) -> int:
    dados = _validar_tarefa({"titulo": titulo, "descricao": descricao, "prioridade": prioridade,
                             "prazo": prazo, "categoria": categoria, "duracao_min": duracao_min})
    if _existe_tarefa_igual(dados["titulo"], dados["prazo"]):
        raise v.ErroValidacao("Já existe uma tarefa em aberto com esse título e prazo.")
    momento = agora_iso()
    return db.inserir(
        "INSERT INTO tarefas (usuario_id, titulo, descricao, prioridade, prazo, categoria, duracao_min, exemplo, "
        "criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (uid(), dados["titulo"], dados["descricao"], dados["prioridade"], dados["prazo"], dados["categoria"],
         dados["duracao_min"], int(exemplo), momento, momento),
    )


def obter_tarefa(id_: int) -> dict[str, Any] | None:
    return _obter("tarefas", id_)


def listar_tarefas(filtro: str = "todas", categoria: str | None = None,
                   hoje: date | None = None) -> list[dict[str, Any]]:
    hoje_iso = (hoje or _hoje()).isoformat()
    condicoes: list[str] = ["usuario_id = ?"]
    parametros: list[Any] = [uid()]
    if filtro == "pendentes":
        condicoes.append("status != 'concluida'")
    elif filtro == "concluidas":
        condicoes.append("status = 'concluida'")
    elif filtro == "atrasadas":
        condicoes.append("status != 'concluida' AND prazo IS NOT NULL AND prazo < ?")
        parametros.append(hoje_iso)
    elif filtro == "hoje":
        condicoes.append("status != 'concluida' AND prazo = ?")
        parametros.append(hoje_iso)
    elif filtro != "todas":
        raise v.ErroValidacao("Filtro de tarefas inválido.")
    if categoria:
        condicoes.append("categoria = ?")
        parametros.append(categoria)
    return db.consultar(
        f"SELECT * FROM tarefas WHERE {' AND '.join(condicoes)} "
        "ORDER BY CASE WHEN status = 'concluida' THEN 1 ELSE 0 END, CASE WHEN prazo IS NULL THEN 1 ELSE 0 END, "
        "prazo, CASE prioridade WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END, id",
        tuple(parametros),
    )


def atualizar_tarefa(id_: int, **campos: Any) -> bool:
    atual = obter_tarefa(id_)
    if atual is None:
        raise v.ErroValidacao("Tarefa não encontrada.")
    _checar_campos(campos, CAMPOS_TAREFA)
    limpos = _validar_tarefa(campos, parcial=True)
    titulo = limpos.get("titulo", atual["titulo"])
    prazo = limpos["prazo"] if "prazo" in limpos else atual["prazo"]
    status = limpos.get("status", atual["status"])
    if status != "concluida" and _existe_tarefa_igual(titulo, prazo, ignorar_id=int(id_)):
        raise v.ErroValidacao("Já existe uma tarefa em aberto com esse título e prazo.")
    if "status" in limpos:
        limpos["concluida_em"] = agora_iso() if status == "concluida" else None
    return _atualizar("tarefas", (*CAMPOS_TAREFA, "concluida_em"), id_, limpos)


def concluir_tarefa(id_: int) -> bool:
    return atualizar_tarefa(id_, status="concluida")


def reabrir_tarefa(id_: int) -> bool:
    return atualizar_tarefa(id_, status="pendente")


def excluir_tarefa(id_: int) -> bool:
    return _excluir("tarefas", id_)


def categorias_tarefas() -> list[str]:
    linhas = db.consultar("SELECT DISTINCT categoria FROM tarefas WHERE usuario_id = ? AND categoria != '' "
                          "ORDER BY categoria", (uid(),))
    return [linha["categoria"] for linha in linhas]


def esta_atrasada(tarefa: dict[str, Any], hoje: date | None = None) -> bool:
    prazo = tarefa.get("prazo")
    return bool(prazo) and tarefa.get("status") != "concluida" and prazo < (hoje or _hoje()).isoformat()


# ---------------------------------------------------------------------------
# Metas
# ---------------------------------------------------------------------------

CAMPOS_META = ("titulo", "descricao", "prazo", "progresso", "recorrencia")


def _validar_meta(dados: dict[str, Any], parcial: bool = False) -> dict[str, Any]:
    limpos: dict[str, Any] = {}
    if not parcial or "titulo" in dados:
        limpos["titulo"] = v.texto_obrigatorio(dados.get("titulo"), "Título")
    if "descricao" in dados:
        limpos["descricao"] = v.texto_opcional(dados.get("descricao"), "Descrição")
    if "prazo" in dados:
        limpos["prazo"] = v.data_iso(dados.get("prazo"), "Prazo")
    if not parcial or "progresso" in dados:
        limpos["progresso"] = v.inteiro(dados.get("progresso", 0), "Progresso (%)", 0, 100)
    if not parcial or "recorrencia" in dados:
        limpos["recorrencia"] = v.opcao(dados.get("recorrencia", "nenhuma"), v.RECORRENCIAS, "Recorrência")
    return limpos


def criar_meta(titulo: str, descricao: str = "", prazo: Any = None, progresso: int = 0,
               recorrencia: str = "nenhuma", exemplo: bool = False) -> int:
    dados = _validar_meta({"titulo": titulo, "descricao": descricao, "prazo": prazo,
                           "progresso": progresso, "recorrencia": recorrencia})
    if db.consultar_um("SELECT id FROM metas WHERE usuario_id = ? AND lower(titulo) = lower(?)",
                       (uid(), dados["titulo"])):
        raise v.ErroValidacao("Já existe uma meta com esse título.")
    momento = agora_iso()
    return db.inserir(
        "INSERT INTO metas (usuario_id, titulo, descricao, prazo, progresso, recorrencia, exemplo, criado_em, "
        "atualizado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (uid(), dados["titulo"], dados["descricao"], dados["prazo"], dados["progresso"], dados["recorrencia"],
         int(exemplo), momento, momento),
    )


def obter_meta(id_: int) -> dict[str, Any] | None:
    return _obter("metas", id_)


def listar_metas(filtro: str = "todas") -> list[dict[str, Any]]:
    extra = {"todas": "", "ativas": " AND progresso < 100", "concluidas": " AND progresso = 100"}
    if filtro not in extra:
        raise v.ErroValidacao("Filtro de metas inválido.")
    return db.consultar(
        f"SELECT * FROM metas WHERE usuario_id = ?{extra[filtro]} ORDER BY CASE WHEN progresso = 100 THEN 1 ELSE 0 END, "
        "CASE WHEN prazo IS NULL THEN 1 ELSE 0 END, prazo, id",
        (uid(),),
    )


def atualizar_meta(id_: int, **campos: Any) -> bool:
    if obter_meta(id_) is None:
        raise v.ErroValidacao("Meta não encontrada.")
    _checar_campos(campos, CAMPOS_META)
    limpos = _validar_meta(campos, parcial=True)
    if "titulo" in limpos and db.consultar_um(
        "SELECT id FROM metas WHERE usuario_id = ? AND lower(titulo) = lower(?) AND id != ?",
        (uid(), limpos["titulo"], int(id_)),
    ):
        raise v.ErroValidacao("Já existe uma meta com esse título.")
    return _atualizar("metas", CAMPOS_META, id_, limpos)


def excluir_meta(id_: int) -> bool:
    return _excluir("metas", id_)


# ---------------------------------------------------------------------------
# Compromissos (agenda)
# ---------------------------------------------------------------------------

CAMPOS_COMPROMISSO = ("titulo", "descricao", "data", "hora_inicio", "hora_fim", "local")


def _validar_compromisso(dados: dict[str, Any]) -> dict[str, Any]:
    limpos = {
        "titulo": v.texto_obrigatorio(dados.get("titulo"), "Título"),
        "descricao": v.texto_opcional(dados.get("descricao"), "Descrição"),
        "data": v.data_iso(dados.get("data"), "Data", obrigatoria=True),
        "hora_inicio": v.hora_iso(dados.get("hora_inicio"), "Início"),
        "hora_fim": v.hora_iso(dados.get("hora_fim"), "Fim"),
        "local": v.texto_opcional(dados.get("local"), "Local", v.LIMITE_TITULO),
    }
    if limpos["hora_fim"] <= limpos["hora_inicio"]:
        raise v.ErroValidacao("O horário de fim deve ser depois do horário de início.")
    return limpos


def criar_compromisso(titulo: str, data: Any, hora_inicio: Any, hora_fim: Any, descricao: str = "",
                      local: str = "", exemplo: bool = False) -> int:
    d = _validar_compromisso({"titulo": titulo, "data": data, "hora_inicio": hora_inicio,
                              "hora_fim": hora_fim, "descricao": descricao, "local": local})
    if db.consultar_um(
        "SELECT id FROM compromissos WHERE usuario_id = ? AND lower(titulo) = lower(?) AND data = ? "
        "AND hora_inicio = ?",
        (uid(), d["titulo"], d["data"], d["hora_inicio"]),
    ):
        raise v.ErroValidacao("Esse compromisso já está cadastrado nesse dia e horário.")
    momento = agora_iso()
    return db.inserir(
        "INSERT INTO compromissos (usuario_id, titulo, descricao, data, hora_inicio, hora_fim, local, exemplo, "
        "criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (uid(), d["titulo"], d["descricao"], d["data"], d["hora_inicio"], d["hora_fim"], d["local"],
         int(exemplo), momento, momento),
    )


def obter_compromisso(id_: int) -> dict[str, Any] | None:
    return _obter("compromissos", id_)


def listar_compromissos(inicio: Any = None, fim: Any = None) -> list[dict[str, Any]]:
    condicoes, parametros = ["usuario_id = ?"], [uid()]
    if inicio:
        condicoes.append("data >= ?")
        parametros.append(v.data_iso(inicio, "Início"))
    if fim:
        condicoes.append("data <= ?")
        parametros.append(v.data_iso(fim, "Fim"))
    return db.consultar(f"SELECT * FROM compromissos WHERE {' AND '.join(condicoes)} ORDER BY data, hora_inicio, id",
                        tuple(parametros))


def compromissos_do_dia(dia: date | None = None) -> list[dict[str, Any]]:
    dia = dia or _hoje()
    return listar_compromissos(dia, dia)


def proximos_compromissos(dias: int = 7, hoje: date | None = None) -> list[dict[str, Any]]:
    hoje = hoje or _hoje()
    return listar_compromissos(hoje, hoje + timedelta(days=dias))


def atualizar_compromisso(id_: int, **campos: Any) -> bool:
    atual = obter_compromisso(id_)
    if atual is None:
        raise v.ErroValidacao("Compromisso não encontrado.")
    _checar_campos(campos, CAMPOS_COMPROMISSO)
    limpos = _validar_compromisso({**{k: atual[k] for k in CAMPOS_COMPROMISSO}, **campos})
    return _atualizar("compromissos", CAMPOS_COMPROMISSO, id_, limpos)


def excluir_compromisso(id_: int) -> bool:
    return _excluir("compromissos", id_)


# ---------------------------------------------------------------------------
# Anotações
# ---------------------------------------------------------------------------


def _validar_anotacao(dados: dict[str, Any], parcial: bool = False) -> dict[str, Any]:
    limpos: dict[str, Any] = {}
    if not parcial or "titulo" in dados:
        limpos["titulo"] = v.texto_obrigatorio(dados.get("titulo"), "Título")
    if not parcial or "conteudo" in dados:
        limpos["conteudo"] = v.texto_opcional(dados.get("conteudo"), "Conteúdo")
    if not parcial or "tags" in dados:
        tags = v.texto_opcional(dados.get("tags"), "Etiquetas", v.LIMITE_TITULO)
        limpos["tags"] = ", ".join(t.strip() for t in tags.split(",") if t.strip())
    return limpos


def criar_anotacao(titulo: str, conteudo: str = "", tags: str = "", exemplo: bool = False) -> int:
    d = _validar_anotacao({"titulo": titulo, "conteudo": conteudo, "tags": tags})
    if db.consultar_um("SELECT id FROM anotacoes WHERE usuario_id = ? AND lower(titulo) = lower(?) AND conteudo = ?",
                       (uid(), d["titulo"], d["conteudo"])):
        raise v.ErroValidacao("Já existe uma anotação idêntica.")
    momento = agora_iso()
    return db.inserir(
        "INSERT INTO anotacoes (usuario_id, titulo, conteudo, tags, exemplo, criado_em, atualizado_em) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uid(), d["titulo"], d["conteudo"], d["tags"], int(exemplo), momento, momento),
    )


def obter_anotacao(id_: int) -> dict[str, Any] | None:
    return _obter("anotacoes", id_)


def listar_anotacoes(busca: str = "") -> list[dict[str, Any]]:
    busca = v.texto_opcional(busca, "Pesquisa", v.LIMITE_TITULO)
    if not busca:
        return db.consultar("SELECT * FROM anotacoes WHERE usuario_id = ? ORDER BY atualizado_em DESC, id DESC",
                            (uid(),))
    termo = f"%{db.escapar_like(busca)}%"
    return db.consultar(
        f"SELECT * FROM anotacoes WHERE usuario_id = ? AND ({db.contem('titulo')} OR {db.contem('conteudo')} "
        f"OR {db.contem('tags')}) ORDER BY atualizado_em DESC, id DESC",
        (uid(), termo, termo, termo),
    )


def atualizar_anotacao(id_: int, **campos: Any) -> bool:
    if obter_anotacao(id_) is None:
        raise v.ErroValidacao("Anotação não encontrada.")
    _checar_campos(campos, ("titulo", "conteudo", "tags"))
    return _atualizar("anotacoes", ("titulo", "conteudo", "tags"), id_, _validar_anotacao(campos, parcial=True))


def excluir_anotacao(id_: int) -> bool:
    return _excluir("anotacoes", id_)


# ---------------------------------------------------------------------------
# Indicadores do painel
# ---------------------------------------------------------------------------

def _soma(condicao: str) -> str:
    return f"COALESCE(SUM(CASE WHEN {condicao} THEN 1 ELSE 0 END), 0)"


def indicadores(hoje: date | None = None) -> dict[str, Any]:
    hoje_iso = (hoje or _hoje()).isoformat()
    feita = "status = 'concluida'"
    aberta = "status != 'concluida'"
    colunas = ", ".join([
        "COUNT(*) AS total",
        f"{_soma(feita)} AS concluidas",
        f"{_soma(aberta)} AS pendentes",
        f"{_soma(aberta + ' AND prazo IS NOT NULL AND prazo < ?')} AS atrasadas",
        f"{_soma(aberta + ' AND prazo = ?')} AS para_hoje",
        f"{_soma(feita + ' AND substr(concluida_em, 1, 10) = ?')} AS concluidas_hoje",
    ])
    t = db.consultar_um(
        f"SELECT {colunas} FROM tarefas WHERE usuario_id = ?",
        (hoje_iso, hoje_iso, hoje_iso, uid()),
    ) or {}
    m = db.consultar_um(
        f"SELECT COUNT(*) AS total, COALESCE(AVG(progresso), 0) AS media, {_soma('progresso = 100')} AS concluidas "
        "FROM metas WHERE usuario_id = ?", (uid(),)
    ) or {}
    c = db.consultar_um("SELECT COUNT(*) AS hoje FROM compromissos WHERE usuario_id = ? AND data = ?",
                        (uid(), hoje_iso)) or {}
    n = db.consultar_um("SELECT COUNT(*) AS total FROM anotacoes WHERE usuario_id = ?", (uid(),)) or {}
    total = int(t.get("total") or 0)
    concluidas = int(t.get("concluidas") or 0)
    return {
        "tarefas_total": total,
        "tarefas_concluidas": concluidas,
        "tarefas_pendentes": int(t.get("pendentes") or 0),
        "tarefas_atrasadas": int(t.get("atrasadas") or 0),
        "tarefas_hoje": int(t.get("para_hoje") or 0),
        "tarefas_concluidas_hoje": int(t.get("concluidas_hoje") or 0),
        "percentual_tarefas": round(100 * concluidas / total) if total else 0,
        "metas_total": int(m.get("total") or 0),
        "metas_media": round(float(m.get("media") or 0)),
        "metas_concluidas": int(m.get("concluidas") or 0),
        "compromissos_hoje": int(c.get("hoje") or 0),
        "anotacoes_total": int(n.get("total") or 0),
    }
