"""Menu de navegação e inicialização comum a todas as páginas."""

from __future__ import annotations

import logging
import time

import streamlit as st

from assistente import acesso, automacoes, config, db, notificacoes, usuarios
from assistente.ui import componentes as ui, estilos
from assistente.ui.paginas import (agenda, anotacoes, automacoes_pg, chat_pg, configuracoes_pg, entrada, metas,
                                   notificacoes_pg, painel, pesquisa_pg, planejador_pg, preferencias_pg, tarefas)

log = logging.getLogger(__name__)

# (chave, função, título, ícone Material, url)
_DEFINICOES = {
    "Principal": [
        ("painel", painel.render, "Painel", ":material/space_dashboard:", "painel"),
        ("planejador", planejador_pg.render, "Planejador do dia", ":material/event_note:", "planejador"),
        ("chat", chat_pg.render, "Conversa", ":material/chat:", "conversa"),
    ],
    "Organização": [
        ("tarefas", tarefas.render, "Tarefas", ":material/task_alt:", "tarefas"),
        ("metas", metas.render, "Metas", ":material/flag:", "metas"),
        ("compromissos", agenda.render, "Agenda", ":material/calendar_month:", "agenda"),
        ("anotacoes", anotacoes.render, "Anotações", ":material/sticky_note_2:", "anotacoes"),
    ],
    "Ferramentas": [
        ("pesquisa", pesquisa_pg.render, "Pesquisa", ":material/search:", "pesquisa"),
        ("notificacoes", notificacoes_pg.render, "Notificações", ":material/notifications:", "notificacoes"),
        ("automacoes", automacoes_pg.render, "Automações", ":material/bolt:", "automacoes"),
    ],
    "Ajustes": [
        ("preferencias", preferencias_pg.render, "Preferências e memória", ":material/psychology:", "preferencias"),
        ("configuracoes", configuracoes_pg.render, "Configurações", ":material/settings:", "configuracoes"),
    ],
}
# Apelidos usados por outras partes do app.
_APELIDOS = {"agenda": "compromissos"}

_PAGINAS: dict[str, st.Page] = {}

INTERVALO_VERIFICACAO_S = 60


def pagina(nome: str) -> st.Page:
    return _PAGINAS[_APELIDOS.get(nome, nome)]


def _construir_paginas(nao_lidas: int) -> dict[str, list[st.Page]]:
    secoes: dict[str, list[st.Page]] = {}
    for secao, itens in _DEFINICOES.items():
        lista = []
        for chave, funcao, titulo, icone, url in itens:
            if chave == "notificacoes" and nao_lidas:
                titulo = f"{titulo} ({nao_lidas})"
            pg = st.Page(funcao, title=titulo, icon=icone, url_path=url, default=(chave == "painel"))
            _PAGINAS[chave] = pg
            lista.append(pg)
        secoes[secao] = lista
    return secoes


def _tela_de_acesso(senha: str) -> bool:
    """Mostra a tela de senha se ASSISTENTE_SENHA_ACESSO estiver definida."""
    if not senha or st.session_state.get("_acesso_ok"):
        return True
    controle = st.session_state.setdefault("_tentativas", acesso.ControleTentativas())
    st.markdown("## 🔒 Acesso protegido")
    st.write("Este assistente está protegido por senha.")
    if controle.bloqueado():
        st.error("Muitas tentativas erradas. Aguarde um minuto e tente novamente.")
        return False
    with st.form("acesso"):
        digitada = st.text_input("Senha de acesso", type="password")
        if st.form_submit_button("Entrar", type="primary"):
            if acesso.senha_confere(digitada, senha):
                st.session_state["_acesso_ok"] = True
                st.rerun()
            controle.registrar_erro()
            st.error("Senha incorreta.")
    return False


def _verificacoes_periodicas() -> None:
    """Gera avisos e roda automações no máximo uma vez por minuto por sessão."""
    agora = time.monotonic()
    if agora - st.session_state.get("_ultima_verificacao", -INTERVALO_VERIFICACAO_S) < INTERVALO_VERIFICACAO_S:
        return
    st.session_state["_ultima_verificacao"] = agora
    try:
        notificacoes.gerar_avisos(config=ui.config())
        automacoes.executar_pendentes()
    except db.ErroBanco as erro:
        log.warning("Verificação periódica falhou: %s", erro)


def _identificar_usuario(multiusuario: bool) -> dict | None:
    """Define o dono dos dados desta execução. Devolve a conta logada (modo com contas)."""
    if not multiusuario:
        db.definir_usuario(None)  # uso pessoal: sempre o usuário local
        return None
    conta = st.session_state.get("_usuario")
    if conta and usuarios.obter(conta["id"]) is None:  # conta excluída em outra sessão
        st.session_state.clear()
        conta = None
    db.definir_usuario(conta["id"] if conta else None)
    return conta


def executar() -> None:
    # Relê a configuração a cada acesso: os Secrets da hospedagem podem mudar sem reiniciar o processo.
    configuracao = config.recarregar()
    logging.basicConfig(level=configuracao.nivel_log, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if configuracao.producao and not db.usando_postgres():
        # Na hospedagem, o disco não é permanente: sem banco online os dados se perderiam.
        motivo = config.diagnosticar_url_banco(configuracao.url_banco)
        st.error("O banco de dados online não está configurado. Quem administra o app precisa colocar uma "
                 "ASSISTENTE_DATABASE_URL válida (começando com postgresql://) nos Secrets da hospedagem. "
                 f"Motivo provável: {motivo}.")
        st.stop()

    try:
        db.inicializar()
    except Exception:  # noqa: BLE001 - mensagem amigável, detalhe só no log
        log.exception("Falha ao preparar o banco")
        st.error("Não foi possível abrir o banco de dados. Tente novamente em alguns instantes.")
        st.stop()

    conta = _identificar_usuario(configuracao.multiusuario)
    if configuracao.multiusuario and conta is None:
        st.markdown(estilos.css("claro"), unsafe_allow_html=True)
        entrada.render()
        st.stop()

    cfg = ui.config()
    st.markdown(estilos.css(cfg["tema"]), unsafe_allow_html=True)

    if not configuracao.multiusuario and not _tela_de_acesso(configuracao.senha_acesso):
        st.stop()

    _verificacoes_periodicas()
    nao_lidas = notificacoes.contar_nao_lidas()
    navegacao = st.navigation(_construir_paginas(nao_lidas), position="sidebar")

    with st.sidebar:
        nome = cfg["nome_assistente"]
        st.markdown(f"### ✨ {ui.e(nome)}")
        st.caption("Seu assistente pessoal de produtividade")
        if nao_lidas:
            if st.button(f"🔔 {nao_lidas} aviso(s) não lido(s)", key="_sb_avisos", width="stretch"):
                st.switch_page(pagina("notificacoes"))
        if conta:
            st.caption(f"Conectado como **{ui.e(conta['nome'])}**")
            if st.button("Sair", key="_sb_sair", icon=":material/logout:", width="stretch"):
                st.session_state.clear()
                st.rerun()
        elif not configuracao.producao:
            st.caption("Ambiente: desenvolvimento · dados salvos só neste computador")

    navegacao.run()
