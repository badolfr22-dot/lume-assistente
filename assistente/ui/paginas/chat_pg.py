"""Conversa com o assistente (regras locais)."""

from __future__ import annotations

import streamlit as st

from assistente.chat import EstadoChat
from assistente.config import configuracao
from assistente.ia import obter_provedor
from assistente.ui import componentes as ui

ATALHOS = ["ajuda", "tarefas pendentes", "agenda hoje", "sugestões", "resumo do dia", "planejar meu dia"]
LIMITE_HISTORICO = 60


def _enviar(estado: EstadoChat, mensagem: str) -> None:
    provedor = obter_provedor(configuracao().provedor_ia)
    resposta = provedor.responder(mensagem, estado)
    estado.historico.append(("user", mensagem))
    estado.historico.append(("assistant", resposta.texto))
    del estado.historico[:-LIMITE_HISTORICO]


def render() -> None:
    nome = ui.config()["nome_assistente"]
    ui.cabecalho("Conversa", f"Fale com {nome} usando comandos simples em português.", "💬")
    estado: EstadoChat = st.session_state.setdefault("chat_estado", EstadoChat())

    st.caption("Este chat funciona com regras locais (não é uma inteligência artificial) e só usa os dados "
               "cadastrados aqui. Alterações sempre pedem sua confirmação.")

    def _usar_atalho() -> None:
        escolha = st.session_state.get("chat_atalho")
        if escolha:
            _enviar(estado, escolha)
        st.session_state["chat_atalho"] = None  # permitido dentro do callback

    st.pills("Atalhos", ATALHOS, key="chat_atalho", on_change=_usar_atalho)

    if not estado.historico:
        with st.chat_message("assistant"):
            st.markdown(f"Olá! Eu sou {ui.e(nome)}. Escreva **ajuda** para ver o que sei fazer.")
    for autor, texto in estado.historico:
        with st.chat_message(autor):
            st.markdown(texto.replace("\n", "  \n"))  # quebra de linha visível no Markdown

    if estado.pendente is not None:
        c1, c2 = st.columns(2)
        if c1.button("Sim, confirmar", type="primary", icon=":material/check:", width="stretch", key="chat_sim"):
            _enviar(estado, "sim")
            st.rerun()
        if c2.button("Não, cancelar", icon=":material/close:", width="stretch", key="chat_nao"):
            _enviar(estado, "não")
            st.rerun()

    mensagem = st.chat_input("Escreva um comando, por exemplo: criar tarefa Estudar amanhã", max_chars=500)
    if mensagem:
        _enviar(estado, mensagem)
        st.rerun()

    if estado.historico and st.button("Limpar conversa", icon=":material/delete_sweep:", type="tertiary"):
        st.session_state["chat_estado"] = EstadoChat()
        st.rerun()
