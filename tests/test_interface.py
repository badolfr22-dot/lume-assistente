"""Testes das telas com o AppTest oficial do Streamlit (sem abrir navegador)."""

from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from assistente import config, configuracoes, demo, notificacoes, preferencias, repositorio as r

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = ["painel", "tarefas", "metas", "agenda", "anotacoes", "pesquisa_pg", "planejador_pg", "chat_pg",
           "notificacoes_pg", "automacoes_pg", "preferencias_pg", "configuracoes_pg"]


def _script_pagina(nome: str) -> None:
    import importlib

    import streamlit as st

    from assistente.ui import componentes, estilos

    st.markdown(estilos.css(componentes.config()["tema"]), unsafe_allow_html=True)
    importlib.import_module(f"assistente.ui.paginas.{nome}").render()


def abrir(nome: str) -> AppTest:
    at = AppTest.from_function(_script_pagina, args=(nome,), default_timeout=60)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def textos(at: AppTest) -> str:
    partes = [m.value for m in at.markdown] + [c.value for c in at.caption]
    partes += [x.value for x in at.error] + [x.value for x in at.success] + [x.value for x in at.warning]
    partes += [x.value for x in at.info]
    return "\n".join(str(p) for p in partes)


def botao(at: AppTest, rotulo: str, indice: int = 0):
    candidatos = [b for b in at.button if b.label == rotulo]
    assert candidatos, f"Botão “{rotulo}” não encontrado"
    return candidatos[indice]


# --- Inicialização ---------------------------------------------------------------

def test_app_inicia_sem_erros():
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert "Progresso" in textos(at)


def test_app_pede_senha_quando_configurada(monkeypatch):
    monkeypatch.setenv("ASSISTENTE_SENHA_ACESSO", "senha-de-teste")
    config.recarregar()
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60)
    at.run()
    assert "Acesso protegido" in textos(at)
    assert "Progresso" not in textos(at)
    at.text_input[0].input("errada")
    at.button[0].click().run()
    assert "Senha incorreta" in textos(at)
    at.text_input[0].input("senha-de-teste")
    at.button[0].click().run()
    assert "Progresso" in textos(at)


@pytest.mark.parametrize("pagina", PAGINAS)
def test_todas_as_paginas_abrem_vazias(pagina):
    abrir(pagina)


@pytest.mark.parametrize("pagina", PAGINAS)
def test_todas_as_paginas_abrem_com_dados_e_tema_escuro(pagina):
    configuracoes.salvar({"tema": "escuro"})
    demo.carregar()
    r.criar_compromisso("Sobreposto", date.today(), "10:30", "11:30")
    notificacoes.registrar("lembretes", "Aviso", "texto", "ref:1")
    preferencias.salvar("outros", "cor", "azul")
    from assistente import automacoes
    automacoes.executar(automacoes.criar("Resumo", "resumo_diario"))
    abrir(pagina)


# --- Painel ------------------------------------------------------------------

def test_painel_mostra_dados_reais_e_estado_vazio():
    at = abrir("painel")
    texto = textos(at)
    assert "Nenhuma tarefa pendente" in texto
    assert "Sugestões inteligentes" in texto
    r.criar_tarefa("Tarefa real do usuário", prazo=date.today())
    at = abrir("painel")
    assert "Tarefa real do usuário" in textos(at)


def test_painel_concluir_atualiza_indicadores():
    id_ = r.criar_tarefa("Concluir pelo painel", prazo=date.today())
    at = abrir("painel")
    botao(at, "Concluir").click().run()
    assert r.obter_tarefa(id_)["status"] == "concluida"
    assert r.indicadores()["tarefas_concluidas_hoje"] == 1


def test_painel_anotacao_rapida():
    at = abrir("painel")
    at.text_input[0].input("Nota pelo painel")
    [b for b in at.get("form_submit_button") if b.label == "Salvar anotação"][0].click().run()
    assert r.listar_anotacoes()[0]["titulo"] == "Nota pelo painel"


# --- Tarefas ---------------------------------------------------------------

def test_criar_tarefa_pela_tela_e_validacao():
    at = abrir("tarefas")
    salvar = [b for b in at.get("form_submit_button") if b.label == "Adicionar tarefa"][0]
    salvar.click().run()
    assert "obrigatório" in textos(at)
    assert r.listar_tarefas() == []
    at.text_input[0].input("Nova pela tela")
    [b for b in at.get("form_submit_button") if b.label == "Adicionar tarefa"][0].click().run()
    assert [t["titulo"] for t in r.listar_tarefas()] == ["Nova pela tela"]
    assert "Tarefa adicionada" in textos(at)


def test_excluir_tarefa_pede_confirmacao():
    id_ = r.criar_tarefa("Excluir pela tela")
    at = abrir("tarefas")
    botao(at, "Excluir").click().run()
    assert r.obter_tarefa(id_) is not None
    assert "não pode ser desfeita" in textos(at)
    botao(at, "Sim, excluir").click().run()
    assert r.obter_tarefa(id_) is None


def test_filtro_atrasadas():
    r.criar_tarefa("Velha", prazo=date.today() - timedelta(days=3))
    r.criar_tarefa("Nova", prazo=date.today() + timedelta(days=3))
    at = abrir("tarefas")
    at.get("button_group")[0].set_value("atrasadas").run()
    texto = textos(at)
    assert "Velha" in texto and "Nova" not in texto


# --- Pesquisa e "abrir item" -----------------------------------------------------

def test_pesquisa_pela_tela():
    r.criar_anotacao("Receita de bolo", "farinha")
    at = abrir("pesquisa_pg")
    at.text_input[0].input("bolo")
    [b for b in at.get("form_submit_button") if b.label == "Pesquisar"][0].click().run()
    texto = textos(at)
    assert "1 resultado(s)" in texto and "Receita de bolo" in texto


def test_pesquisa_vazia_mostra_erro_claro():
    at = abrir("pesquisa_pg")
    [b for b in at.get("form_submit_button") if b.label == "Pesquisar"][0].click().run()
    assert "pelo menos 2 caracteres" in textos(at)


def test_item_aberto_aparece_destacado():
    id_ = r.criar_meta("Meta aberta")
    at = AppTest.from_function(_script_pagina, args=("metas",), default_timeout=60)
    at.session_state["_foco"] = ("metas", id_)
    at.run()
    assert not at.exception
    assert "Item aberto pela pesquisa" in textos(at)


# --- Chat ----------------------------------------------------------------------

def test_chat_cria_tarefa_com_confirmacao():
    at = abrir("chat_pg")
    at.chat_input[0].set_value("criar tarefa Comprar leite amanhã").run()
    assert "Confirma criar a tarefa" in textos(at)
    assert r.listar_tarefas() == []
    botao(at, "Sim, confirmar").click().run()
    assert [t["titulo"] for t in r.listar_tarefas()] == ["Comprar leite"]


# --- Preferências e configurações -----------------------------------------------------

def test_preferencia_sensivel_recusada_na_tela():
    at = abrir("preferencias_pg")
    at.text_input[0].input("minha senha")
    at.text_input[1].input("abc123")
    [b for b in at.get("form_submit_button") if b.label == "Salvar na memória"][0].click().run()
    assert "Por segurança" in textos(at)
    assert preferencias.listar() == []


def test_configuracoes_salvar_tema_e_restaurar():
    r.criar_tarefa("Não pode sumir")
    at = abrir("configuracoes_pg")
    at.radio[0].set_value("escuro")
    [b for b in at.get("form_submit_button") if b.label == "Salvar configurações"][0].click().run()
    assert configuracoes.obter("tema") == "escuro"
    botao(at, "Restaurar configurações padrão").click().run()
    botao(at, "Sim, restaurar").click().run()
    assert configuracoes.obter("tema") == "claro"
    assert len(r.listar_tarefas()) == 1


def test_exemplos_pela_tela():
    at = abrir("configuracoes_pg")
    botao(at, "Carregar exemplos").click().run()
    assert demo.contar() == 7
    botao(at, "Remover exemplos (7)").click().run()
    assert demo.contar() == 0


def test_texto_do_usuario_e_escapado_no_html():
    r.criar_tarefa("<script>alert(1)</script>", prazo=date.today())
    at = abrir("painel")
    html_bruto = "\n".join(m.value for m in at.markdown)
    assert "<script>alert(1)</script>" not in html_bruto
    assert "&lt;script&gt;" in html_bruto


# --- Modo com contas (publicação) ----------------------------------------------------------

def _app_com_contas(monkeypatch) -> AppTest:
    monkeypatch.setenv("ASSISTENTE_CONTAS", "sim")
    config.recarregar()
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _enviar(at: AppTest, rotulo: str) -> None:
    [b for b in at.get("form_submit_button") if b.label == rotulo][0].click().run()


def test_com_contas_pede_login_antes_de_mostrar_dados(monkeypatch):
    at = _app_com_contas(monkeypatch)
    texto = textos(at)
    assert "Seu assistente pessoal" in texto
    assert "Progresso" not in texto  # painel não aparece sem login


def test_criar_conta_entrar_e_sair_pela_tela(monkeypatch):
    at = _app_com_contas(monkeypatch)
    campos = {t.label: t for t in at.text_input}
    campos["Seu nome *"].input("Carla")
    campos["E-mail *"].input("carla@exemplo.com")
    campos["Senha *"].input("senha1234")
    campos["Confirme a senha *"].input("senha1234")
    _enviar(at, "Criar conta")
    assert "concordar com o aviso" in textos(at)  # sem aceitar a privacidade, não cria
    at.checkbox[0].check()
    _enviar(at, "Criar conta")
    assert not at.exception
    assert "Progresso" in textos(at) and "Carla" in textos(at)
    [b for b in at.button if b.label == "Sair"][0].click().run()
    assert "Progresso" not in textos(at)
    # Entrar de novo com a conta criada
    campos = {t.label: t for t in at.text_input}
    campos["E-mail"].input("carla@exemplo.com")
    campos["Senha"].input("errada999")
    _enviar(at, "Entrar")
    assert "E-mail ou senha incorretos" in textos(at)
    campos = {t.label: t for t in at.text_input}
    campos["E-mail"].input("carla@exemplo.com")
    campos["Senha"].input("senha1234")
    _enviar(at, "Entrar")
    assert "Progresso" in textos(at)


def test_duas_sessoes_nao_misturam_dados(monkeypatch):
    from assistente import db, usuarios
    ana = usuarios.criar_conta("ana@exemplo.com", "Ana", "senha1234", "senha1234", aceitou_privacidade=True)
    usuarios.criar_conta("bia@exemplo.com", "Bia", "senha1234", "senha1234", aceitou_privacidade=True)
    db.definir_usuario(ana["id"])
    r.criar_tarefa("Tarefa secreta da Ana", prazo=date.today())
    db.definir_usuario(None)
    at = _app_com_contas(monkeypatch)
    campos = {t.label: t for t in at.text_input}
    campos["E-mail"].input("bia@exemplo.com")
    campos["Senha"].input("senha1234")
    _enviar(at, "Entrar")
    assert "Progresso" in textos(at)
    assert "Tarefa secreta da Ana" not in textos(at)


def test_producao_sem_banco_online_para_com_aviso(monkeypatch):
    monkeypatch.setenv("ASSISTENTE_AMBIENTE", "producao")
    monkeypatch.setenv("ASSISTENTE_DATABASE_URL", "COLE-AQUI-A-CONNECTION-STRING")
    config.recarregar()
    from assistente import db
    db.definir_caminho_banco(None)
    db.definir_url_banco(None)
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60)
    at.run()
    assert "banco de dados online não está configurado" in textos(at)
    assert "Criar conta" not in textos(at)
