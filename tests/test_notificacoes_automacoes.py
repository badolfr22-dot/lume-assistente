from datetime import datetime

import pytest

from assistente import automacoes as a, configuracoes as cfg, notificacoes as n, repositorio as r
from assistente.validacao import ErroValidacao

AGORA = datetime(2026, 10, 22, 9, 0)
HOJE = AGORA.date()


# --- Notificações e lembretes ----------------------------------------------------

def test_lembrete_dispara_uma_vez():
    n.criar_lembrete("Tomar remédio", "2026-10-22", "08:30")
    n.criar_lembrete("Futuro", "2026-10-22", "20:00")
    assert n.gerar_avisos(AGORA) == 1
    assert n.gerar_avisos(AGORA) == 0  # sem duplicar
    assert [x["titulo"] for x in n.listar()] == ["Tomar remédio"]


def test_lembrete_validacao_e_duplicado():
    with pytest.raises(ErroValidacao):
        n.criar_lembrete("", "2026-10-22", "08:00")
    with pytest.raises(ErroValidacao):
        n.criar_lembrete("X", "2026-13-01", "08:00")
    n.criar_lembrete("X", "2026-10-22", "08:00")
    with pytest.raises(ErroValidacao, match="igual"):
        n.criar_lembrete("x", "22/10/2026", "08:00")


def test_aviso_de_prazo_sem_duplicar():
    r.criar_tarefa("Vence amanhã", prazo="2026-10-23")
    r.criar_tarefa("Vence semana que vem", prazo="2026-10-30")
    r.criar_tarefa("Atrasada", prazo="2026-10-01")
    assert n.gerar_avisos(AGORA) == 2
    assert n.gerar_avisos(AGORA) == 0
    titulos = {x["titulo"] for x in n.listar()}
    assert titulos == {"Vence amanhã", "Atrasada"}


def test_aviso_de_compromisso_proximo():
    r.criar_compromisso("Reunião", HOJE, "09:20", "10:00")
    r.criar_compromisso("Almoço", HOJE, "12:00", "13:00")
    assert n.gerar_avisos(AGORA) == 1
    assert n.listar()[0]["titulo"] == "Reunião"


def test_respeita_tipos_configurados():
    cfg.salvar({"notificacoes_tipos": ["lembretes"]})
    r.criar_tarefa("Vence hoje", prazo=HOJE)
    assert n.gerar_avisos(AGORA) == 0


def test_marcar_lida_e_listas():
    n.registrar("lembretes", "A", "", "ref:a")
    n.registrar("lembretes", "B", "", "ref:b")
    assert n.contar_nao_lidas() == 2
    primeiro = n.listar()[0]["id"]
    assert n.marcar_lida(primeiro)
    assert not n.marcar_lida(primeiro)
    assert n.contar_nao_lidas() == 1
    assert len(n.listar("lidas")) == 1
    assert n.marcar_todas_lidas() == 1
    assert n.contar_nao_lidas() == 0
    assert len(n.listar("todas")) == 2


def test_registrar_ignora_duplicata():
    assert n.registrar("prazos", "X", "", "mesma")
    assert not n.registrar("prazos", "X", "", "mesma")


# --- Automações ---------------------------------------------------------------------

def test_criar_validar_ativar_excluir_automacao():
    id_ = a.criar("Avisar atrasos", "tarefas_atrasadas", {"minimo": 2})
    assert a.obter(id_)["parametros"] == {"minimo": 2}
    with pytest.raises(ErroValidacao, match="Já existe"):
        a.criar("avisar atrasos", "resumo_diario")
    with pytest.raises(ErroValidacao):
        a.criar("Outra", "apagar_tudo")
    with pytest.raises(ErroValidacao, match="entre 1 e 50"):
        a.criar("Outra", "tarefas_atrasadas", {"minimo": 0})
    a.definir_ativa(id_, False)
    assert a.obter(id_)["ativa"] == 0
    assert a.excluir(id_)
    assert a.listar() == []


def test_automacao_atrasadas_e_historico():
    r.criar_tarefa("Velha", prazo="2026-10-01")
    id_ = a.criar("Atrasos", "tarefas_atrasadas")
    res = a.executar(id_, AGORA)
    assert res.situacao == "ok" and "Velha" in res.mensagem
    assert n.listar()[0]["tipo"] == "automacoes"
    hist = a.historico()
    assert hist[0]["situacao"] == "ok" and hist[0]["nome_automacao"] == "Atrasos"


def test_automacao_sem_acao():
    id_ = a.criar("Atrasos", "tarefas_atrasadas")
    assert a.executar(id_, AGORA).situacao == "sem_acao"
    assert n.listar() == []


def test_automacoes_nao_alteram_tarefas():
    t = r.criar_tarefa("Intocada", prazo="2026-10-01")
    antes = r.obter_tarefa(t)
    for tipo in a.TIPOS:
        a.executar(a.criar(f"Teste {tipo}", tipo), AGORA)
    assert r.obter_tarefa(t) == antes


def test_executar_pendentes_uma_vez_por_dia_e_ignora_inativas():
    a.criar("Resumo", "resumo_diario")
    inativa = a.criar("Inativa", "resumo_diario", ativa=False)
    assert len(a.executar_pendentes(AGORA)) == 1
    assert a.executar_pendentes(AGORA) == []
    assert a.obter(inativa)["ultima_execucao"] is None


def test_erro_na_automacao_vai_para_historico(monkeypatch):
    id_ = a.criar("Quebrada", "resumo_diario")

    def falhar(*_):
        raise RuntimeError("detalhe interno")

    monkeypatch.setitem(a.ACOES, "resumo_diario", falhar)
    res = a.executar(id_, AGORA)
    assert res.situacao == "erro"
    assert "detalhe interno" not in res.mensagem  # não expõe detalhes
    assert a.historico()[0]["situacao"] == "erro"


def test_sugerir_prioritarias():
    r.criar_tarefa("Baixa", prioridade="baixa", prazo="2026-10-25")
    r.criar_tarefa("Alta", prioridade="alta", prazo="2026-10-25")
    id_ = a.criar("Prioridades", "sugerir_prioritarias", {"quantidade": 1})
    assert a.executar(id_, AGORA).mensagem == "Sugeridas: Alta."


def test_aviso_de_automacao_respeita_configuracao():
    cfg.salvar({"notificacoes_tipos": ["lembretes"]})
    id_ = a.criar("Resumo", "resumo_diario")
    assert a.executar(id_, AGORA).situacao == "ok"
    assert n.listar() == []
