import io
import json
import zipfile
from datetime import date

import pytest

from assistente import configuracoes as cfg, demo, exportacao, pesquisa, repositorio as r, sugestoes
from assistente.validacao import ErroValidacao

HOJE = date(2026, 10, 22)


# --- Pesquisa global -------------------------------------------------------------

def test_pesquisa_separa_por_categoria():
    r.criar_tarefa("Comprar café", prazo="2026-10-23")
    r.criar_meta("Tomar menos café")
    r.criar_compromisso("Café com Ana", "2026-10-24", "08:00", "09:00")
    r.criar_anotacao("Receitas", "bolo de café")
    r.criar_tarefa("Outra coisa")
    res = pesquisa.pesquisar("café")
    assert {k: len(v) for k, v in res.items()} == {"tarefas": 1, "metas": 1, "compromissos": 1, "anotacoes": 1}
    assert pesquisa.total(res) == 4


def test_pesquisa_filtra_por_tipo_e_data():
    r.criar_tarefa("Relatório A", prazo="2026-10-10")
    r.criar_tarefa("Relatório B", prazo="2026-11-10")
    r.criar_anotacao("Relatório anual")
    res = pesquisa.pesquisar("relatório", tipos=["tarefas"], data_inicio="2026-11-01", data_fim="2026-11-30")
    assert list(res) == ["tarefas"]
    assert [t["titulo"] for t in res["tarefas"]] == ["Relatório B"]


def test_pesquisa_vazia_curta_e_invalida():
    with pytest.raises(ErroValidacao, match="pelo menos 2"):
        pesquisa.pesquisar("")
    with pytest.raises(ErroValidacao, match="pelo menos 2"):
        pesquisa.pesquisar(" a ")
    with pytest.raises(ErroValidacao):
        pesquisa.pesquisar("abc", tipos=["usuarios"])
    with pytest.raises(ErroValidacao, match="anterior"):
        pesquisa.pesquisar("abc", data_inicio="2026-12-01", data_fim="2026-01-01")


def test_pesquisa_sem_resultado_e_curingas_literais():
    r.criar_tarefa("Desconto de 10%")
    assert pesquisa.total(pesquisa.pesquisar("xyz")) == 0
    assert pesquisa.total(pesquisa.pesquisar("10%")) == 1
    assert pesquisa.total(pesquisa.pesquisar("__")) == 0
    assert pesquisa.total(pesquisa.pesquisar("' OR 1=1 --")) == 0


# --- Sugestões --------------------------------------------------------------------

def test_sugestao_banco_vazio():
    lista = sugestoes.gerar(HOJE)
    assert [s.tipo for s in lista] == ["vazio"]


def test_sugestoes_correspondem_aos_dados():
    r.criar_tarefa("Atrasadinha", prazo="2026-10-20")
    r.criar_tarefa("Para hoje", prazo=HOJE)
    r.criar_tarefa("Importante", prioridade="alta", prazo="2026-10-28")
    r.criar_meta("Meta lenta", prazo="2026-10-30", progresso=10)
    r.criar_compromisso("Dentista", HOJE, "15:00", "16:00")
    lista = sugestoes.gerar(HOJE)
    tipos = [s.tipo for s in lista]
    assert tipos == ["atrasadas", "hoje", "prioridade", "metas", "agenda"]
    textos = " ".join(s.titulo for s in lista)
    for esperado in ("Atrasadinha", "Importante", "Meta lenta", "Dentista"):
        assert esperado in textos
    assert all(s.motivo for s in lista)


def test_sugestoes_respeitam_configuracoes():
    r.criar_tarefa("Atrasada", prazo="2026-10-20")
    r.criar_tarefa("Hoje", prazo=HOJE)
    cfg.salvar({"sugestoes_tipos": ["hoje"]})
    assert [s.tipo for s in sugestoes.gerar(HOJE)] == ["hoje"]
    cfg.salvar({"sugestoes_tipos": ["atrasadas", "hoje"], "sugestoes_maximo": 1})
    assert len(sugestoes.gerar(HOJE)) == 1
    cfg.salvar({"sugestoes_ativas": False})
    assert sugestoes.gerar(HOJE) == []


# --- Dados de exemplo ------------------------------------------------------------------

def test_exemplos_marcados_e_removiveis():
    real = r.criar_tarefa("Minha tarefa real")
    assert demo.carregar(HOJE) == 7
    assert demo.carregar(HOJE) == 0  # não duplica
    exemplos = [t for t in r.listar_tarefas() if t["exemplo"]]
    assert exemplos and all(t["titulo"].startswith("[Exemplo]") for t in exemplos)
    assert demo.remover() == 7
    assert demo.contar() == 0
    assert [t["id"] for t in r.listar_tarefas()] == [real]


def test_remover_exemplos_apaga_avisos_deles_e_mantem_os_reais():
    from datetime import datetime

    from assistente import notificacoes
    r.criar_tarefa("Real com prazo", prazo=HOJE)
    demo.carregar(HOJE)
    notificacoes.gerar_avisos(datetime(2026, 10, 22, 9, 0))
    assert any("[Exemplo]" in n["titulo"] for n in notificacoes.listar())
    demo.remover()
    titulos = [n["titulo"] for n in notificacoes.listar()]
    assert titulos == ["Real com prazo"]


# --- Exportação ----------------------------------------------------------------------

def test_exportar_json_e_zip():
    r.criar_tarefa("Exportar", descricao="=SOMA(A1)")
    pacote = json.loads(exportacao.para_json())
    assert pacote["dados"]["tarefas"][0]["titulo"] == "Exportar"
    with zipfile.ZipFile(io.BytesIO(exportacao.para_zip_csv())) as z:
        assert "tarefas.csv" in z.namelist()
        conteudo = z.read("tarefas.csv").decode("utf-8-sig")
    assert "Exportar" in conteudo
    assert "'=SOMA(A1)" in conteudo  # fórmula neutralizada
