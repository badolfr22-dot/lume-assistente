"""Ponto de entrada do assistente pessoal digital.

Execute com:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Lume · Assistente pessoal",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={"About": "Assistente pessoal digital de produtividade. Dados salvos localmente em SQLite."},
)

from assistente.ui import navegacao  # noqa: E402  (precisa vir depois do set_page_config)

navegacao.executar()
