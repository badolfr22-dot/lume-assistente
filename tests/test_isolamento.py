"""Garante que uma pessoa nunca vê, altera ou apaga dados de outra."""

import json
from datetime import date, datetime

import pytest

from assistente import (automacoes, configuracoes, db, demo, exportacao, notificacoes, pesquisa, planejador,
                        preferencias, repositorio as r, sugestoes, usuarios)

HOJE = date(2026, 10, 22)


@pytest.fixture
def dois_usuarios():
    ana = usuarios.criar_conta("ana@exemplo.com", "Ana", "senha1234", "senha1234", aceitou_privacidade=True)
    bia = usuarios.criar_conta("bia@exemplo.com", "Bia", "senha1234", "senha1234", aceitou_privacidade=True)
    db.definir_usuario(ana["id"])
    ids = {
        "tarefa": r.criar_tarefa("Segredo da Ana", prazo=HOJE, prioridade="alta"),
        "meta": r.criar_meta("Meta secreta da Ana", prazo="2026-10-30", progresso=10),
        "compromisso": r.criar_compromisso("Consulta da Ana", HOJE, "09:00", "10:00"),
        "anotacao": r.criar_anotacao("Diário da Ana", "texto privado"),
        "preferencia": preferencias.salvar("outros", "cor", "azul da Ana"),
        "lembrete": notificacoes.criar_lembrete("Lembrete da Ana", HOJE, "08:00"),
        "automacao": automacoes.criar("Resumo da Ana", "resumo_diario"),
    }
    configuracoes.salvar({"tema": "escuro", "nome_assistente": "Assistente da Ana"})
    notificacoes.gerar_avisos(datetime(2026, 10, 22, 9, 0))
    automacoes.executar(ids["automacao"], datetime(2026, 10, 22, 9, 0))
    planejador.salvar_ordem(HOJE, [ids["tarefa"]])
    db.definir_usuario(bia["id"])
    return ana, bia, ids


def test_outra_pessoa_nao_ve_nada(dois_usuarios):
    assert r.listar_tarefas() == [] and r.listar_metas() == []
    assert r.listar_compromissos() == [] and r.listar_anotacoes() == []
    assert preferencias.listar() == [] and notificacoes.listar("todas") == []
    assert notificacoes.listar_lembretes() == [] and automacoes.listar() == [] and automacoes.historico() == []
    assert r.categorias_tarefas() == []
    assert configuracoes.obter("tema") == "claro"  # configurações também são por pessoa
    assert planejador.ordem_manual(HOJE) == {}
    assert pesquisa.total(pesquisa.pesquisar("Ana")) == 0
    assert r.indicadores(HOJE)["tarefas_total"] == 0
    assert planejador.progresso_do_dia(HOJE) == (0, 0)
    assert [s.tipo for s in sugestoes.gerar(HOJE)] == ["vazio"]
    assert notificacoes.contar_nao_lidas() == 0
    assert demo.contar() == 0


def test_outra_pessoa_nao_abre_itens_pelo_numero(dois_usuarios):
    _, _, ids = dois_usuarios
    assert r.obter_tarefa(ids["tarefa"]) is None
    assert r.obter_meta(ids["meta"]) is None
    assert r.obter_compromisso(ids["compromisso"]) is None
    assert r.obter_anotacao(ids["anotacao"]) is None
    assert preferencias.obter(ids["preferencia"]) is None
    assert automacoes.obter(ids["automacao"]) is None


def test_outra_pessoa_nao_altera_nem_apaga(dois_usuarios):
    ana, _, ids = dois_usuarios
    with pytest.raises(Exception):
        r.atualizar_tarefa(ids["tarefa"], titulo="invadido")
    with pytest.raises(Exception):
        r.concluir_tarefa(ids["tarefa"])
    with pytest.raises(Exception):
        r.atualizar_meta(ids["meta"], progresso=100)
    with pytest.raises(Exception):
        preferencias.editar(ids["preferencia"], "invadido")
    assert not r.excluir_tarefa(ids["tarefa"])
    assert not r.excluir_meta(ids["meta"])
    assert not r.excluir_compromisso(ids["compromisso"])
    assert not r.excluir_anotacao(ids["anotacao"])
    assert not preferencias.excluir(ids["preferencia"])
    assert not notificacoes.excluir_lembrete(ids["lembrete"])
    assert not automacoes.definir_ativa(ids["automacao"], False)
    assert not automacoes.excluir(ids["automacao"])
    assert notificacoes.marcar_todas_lidas() == 0
    preferencias.limpar_tudo()
    automacoes.limpar_historico()
    configuracoes.restaurar_padroes()
    demo.remover()
    planejador.limpar_ordem(HOJE)
    planejador.salvar_ordem(HOJE, [ids["tarefa"]])  # tarefa da Ana não entra no plano da Bia
    assert planejador.ordem_manual(HOJE) == {}

    # Tudo da Ana continua intacto
    db.definir_usuario(ana["id"])
    assert r.obter_tarefa(ids["tarefa"])["titulo"] == "Segredo da Ana"
    assert r.obter_tarefa(ids["tarefa"])["status"] == "pendente"
    assert r.obter_meta(ids["meta"])["progresso"] == 10
    assert len(r.listar_compromissos()) == len(r.listar_anotacoes()) == 1
    assert preferencias.obter(ids["preferencia"])["valor"] == "azul da Ana"
    assert automacoes.obter(ids["automacao"])["ativa"] == 1
    assert len(automacoes.historico()) == 1
    assert configuracoes.obter("tema") == "escuro"
    assert planejador.ordem_manual(HOJE) == {ids["tarefa"]: 0}
    assert notificacoes.contar_nao_lidas() >= 1


def test_mesmo_titulo_pode_existir_para_pessoas_diferentes(dois_usuarios):
    r.criar_meta("Meta secreta da Ana")  # não conflita com a meta da Ana
    preferencias.salvar("outros", "cor", "verde da Bia")
    automacoes.criar("Resumo da Ana", "resumo_diario")
    assert len(r.listar_metas()) == 1


def test_exportacao_so_tem_dados_da_pessoa(dois_usuarios):
    pacote = json.loads(exportacao.para_json())
    assert pacote["conta"]["email"] == "bia@exemplo.com"
    assert all(linhas == [] for linhas in pacote["dados"].values())
    assert "Ana" not in exportacao.para_zip_csv().decode("latin-1")
