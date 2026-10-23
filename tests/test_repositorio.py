from datetime import date, timedelta

import pytest

from assistente import db, repositorio as r
from assistente.validacao import ErroValidacao

HOJE = date(2026, 10, 22)


# --- Tarefas ------------------------------------------------------------------

def test_criar_e_obter_tarefa():
    id_ = r.criar_tarefa("Estudar Python", prioridade="alta", prazo="2026-10-25", categoria="Estudos",
                         duracao_min=60)
    t = r.obter_tarefa(id_)
    assert t["titulo"] == "Estudar Python"
    assert t["prioridade"] == "alta"
    assert t["prazo"] == "2026-10-25"
    assert t["status"] == "pendente"
    assert t["duracao_min"] == 60


def test_tarefa_aceita_data_brasileira():
    id_ = r.criar_tarefa("Ir ao banco", prazo="25/10/2026")
    assert r.obter_tarefa(id_)["prazo"] == "2026-10-25"


@pytest.mark.parametrize("dados, trecho", [
    ({"titulo": ""}, "obrigatório"),
    ({"titulo": "   "}, "obrigatório"),
    ({"titulo": "x" * 200}, "no máximo"),
    ({"titulo": "Ok", "prioridade": "urgente"}, "Prioridade"),
    ({"titulo": "Ok", "prazo": "31/02/2026"}, "Data inválida"),
    ({"titulo": "Ok", "duracao_min": 0}, "entre 5 e 720"),
    ({"titulo": "Ok", "duracao_min": "abc"}, "número inteiro"),
])
def test_validacao_tarefa(dados, trecho):
    with pytest.raises(ErroValidacao, match=trecho):
        r.criar_tarefa(**dados)


def test_evita_tarefa_duplicada():
    r.criar_tarefa("Comprar pão", prazo="2026-10-23")
    with pytest.raises(ErroValidacao, match="Já existe"):
        r.criar_tarefa("comprar PÃO".replace("PÃO", "pão"), prazo="2026-10-23")
    # Mesmo título com outro prazo é permitido
    r.criar_tarefa("Comprar pão", prazo="2026-10-24")


def test_atualizar_concluir_reabrir_excluir_tarefa():
    id_ = r.criar_tarefa("Lavar o carro")
    assert r.atualizar_tarefa(id_, titulo="Lavar o carro hoje", prioridade="baixa", categoria="Casa")
    t = r.obter_tarefa(id_)
    assert (t["titulo"], t["prioridade"], t["categoria"]) == ("Lavar o carro hoje", "baixa", "Casa")
    r.concluir_tarefa(id_)
    t = r.obter_tarefa(id_)
    assert t["status"] == "concluida" and t["concluida_em"]
    r.reabrir_tarefa(id_)
    t = r.obter_tarefa(id_)
    assert t["status"] == "pendente" and t["concluida_em"] is None
    assert r.excluir_tarefa(id_)
    assert r.obter_tarefa(id_) is None
    assert not r.excluir_tarefa(id_)


def test_atualizar_tarefa_rejeita_campo_desconhecido():
    id_ = r.criar_tarefa("X")
    with pytest.raises(ErroValidacao):
        r.atualizar_tarefa(id_, id=99)
    with pytest.raises(ErroValidacao, match="não encontrada"):
        r.atualizar_tarefa(9999, titulo="Y")


def test_filtros_de_tarefas():
    atrasada = r.criar_tarefa("Atrasada", prazo=HOJE - timedelta(days=2))
    de_hoje = r.criar_tarefa("Hoje", prazo=HOJE)
    futura = r.criar_tarefa("Futura", prazo=HOJE + timedelta(days=5))
    feita = r.criar_tarefa("Feita", prazo=HOJE - timedelta(days=3))
    r.concluir_tarefa(feita)
    ids = lambda f: {t["id"] for t in r.listar_tarefas(f, hoje=HOJE)}  # noqa: E731
    assert ids("atrasadas") == {atrasada}
    assert ids("hoje") == {de_hoje}
    assert ids("pendentes") == {atrasada, de_hoje, futura}
    assert ids("concluidas") == {feita}
    assert ids("todas") == {atrasada, de_hoje, futura, feita}
    with pytest.raises(ErroValidacao):
        r.listar_tarefas("invalido")


def test_filtro_por_categoria_e_lista_de_categorias():
    r.criar_tarefa("A", categoria="Casa")
    r.criar_tarefa("B", categoria="Trabalho")
    assert [t["titulo"] for t in r.listar_tarefas(categoria="Casa")] == ["A"]
    assert r.categorias_tarefas() == ["Casa", "Trabalho"]


# --- Metas --------------------------------------------------------------------

def test_crud_meta():
    id_ = r.criar_meta("Correr 5 km", descricao="Treinar 3x por semana", prazo="2026-12-01", progresso=10)
    assert r.obter_meta(id_)["progresso"] == 10
    r.atualizar_meta(id_, progresso=100)
    assert [m["id"] for m in r.listar_metas("concluidas")] == [id_]
    assert r.listar_metas("ativas") == []
    with pytest.raises(ErroValidacao, match="entre 0 e 100"):
        r.atualizar_meta(id_, progresso=150)
    with pytest.raises(ErroValidacao, match="Já existe"):
        r.criar_meta("correr 5 km")
    assert r.excluir_meta(id_)


# --- Compromissos ---------------------------------------------------------------

def test_crud_compromisso():
    id_ = r.criar_compromisso("Dentista", "2026-10-23", "14:00", "15:00", local="Centro")
    c = r.obter_compromisso(id_)
    assert (c["data"], c["hora_inicio"], c["hora_fim"]) == ("2026-10-23", "14:00", "15:00")
    r.atualizar_compromisso(id_, hora_fim="15:30")
    assert r.obter_compromisso(id_)["hora_fim"] == "15:30"
    assert [x["id"] for x in r.compromissos_do_dia(date(2026, 10, 23))] == [id_]
    assert r.excluir_compromisso(id_)


def test_compromisso_valida_horarios_e_duplicidade():
    with pytest.raises(ErroValidacao, match="depois do horário de início"):
        r.criar_compromisso("Reunião", "2026-10-23", "10:00", "09:00")
    with pytest.raises(ErroValidacao, match="Horário inválido"):
        r.criar_compromisso("Reunião", "2026-10-23", "25:00", "26:00")
    with pytest.raises(ErroValidacao, match="obrigatório"):
        r.criar_compromisso("Reunião", "", "10:00", "11:00")
    r.criar_compromisso("Reunião", "2026-10-23", "10:00", "11:00")
    with pytest.raises(ErroValidacao, match="já está cadastrado"):
        r.criar_compromisso("reunião", "23/10/2026", "10:00", "11:00")


# --- Anotações ------------------------------------------------------------------

def test_crud_e_pesquisa_anotacao():
    id_ = r.criar_anotacao("Lista de compras", "arroz, feijão, 100% café", tags="casa,  mercado ,")
    assert r.obter_anotacao(id_)["tags"] == "casa, mercado"
    assert [a["id"] for a in r.listar_anotacoes("feijão")] == [id_]
    assert [a["id"] for a in r.listar_anotacoes("mercado")] == [id_]
    # O % é tratado como texto literal, não como curinga
    assert [a["id"] for a in r.listar_anotacoes("100%")] == [id_]
    assert r.listar_anotacoes("50%") == []
    r.atualizar_anotacao(id_, conteudo="só café")
    assert r.listar_anotacoes("feijão") == []
    assert r.excluir_anotacao(id_)


# --- Persistência e indicadores -------------------------------------------------

@pytest.mark.somente_sqlite
def test_dados_persistem_apos_reabrir_o_banco():
    r.criar_tarefa("Persistente")
    db.fechar_conexao()  # simula reinício do app
    db._inicializados.clear()
    assert [t["titulo"] for t in r.listar_tarefas()] == ["Persistente"]


def test_inicializar_nao_apaga_dados():
    r.criar_meta("Manter")
    db._inicializados.clear()
    db.inicializar()
    assert len(r.listar_metas()) == 1


def test_indicadores():
    r.criar_tarefa("A", prazo=HOJE - timedelta(days=1))
    r.criar_tarefa("B", prazo=HOJE)
    feita = r.criar_tarefa("C")
    r.concluir_tarefa(feita)
    r.criar_meta("M1", progresso=50)
    r.criar_meta("M2", progresso=100)
    r.criar_compromisso("Reunião", HOJE, "09:00", "10:00")
    ind = r.indicadores(HOJE)
    assert ind["tarefas_total"] == 3
    assert ind["tarefas_pendentes"] == 2
    assert ind["tarefas_atrasadas"] == 1
    assert ind["tarefas_hoje"] == 1
    assert ind["percentual_tarefas"] == 33
    assert ind["metas_media"] == 75
    assert ind["metas_concluidas"] == 1
    assert ind["compromissos_hoje"] == 1


def test_indicadores_banco_vazio():
    ind = r.indicadores(HOJE)
    assert ind["tarefas_total"] == 0 and ind["percentual_tarefas"] == 0 and ind["metas_media"] == 0
