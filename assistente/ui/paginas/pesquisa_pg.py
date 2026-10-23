"""Pesquisa global."""

from __future__ import annotations

from datetime import timedelta

import streamlit as st

from assistente import pesquisa
from assistente.tempo import hoje
from assistente.ui import componentes as ui
from assistente.validacao import ErroValidacao


def _descricao(tipo: str, item: dict) -> str:
    if tipo == "tarefas":
        return f"Prazo: {ui.fmt_data(item['prazo'])} · {'Concluída' if item['status'] == 'concluida' else 'Em aberto'}"
    if tipo == "metas":
        return f"Progresso: {item['progresso']}% · Prazo: {ui.fmt_data(item['prazo'])}"
    if tipo == "compromissos":
        return f"{ui.fmt_data(item['data'])} · {ui.fmt_hora(item['hora_inicio'])}–{ui.fmt_hora(item['hora_fim'])}"
    texto = item["conteudo"]
    return (texto[:100] + "…") if len(texto) > 100 else texto


def render() -> None:
    ui.cabecalho("Pesquisa", "Encontre tarefas, metas, compromissos e anotações por palavra-chave.", "🔎")

    with st.form("form_pesquisa"):
        termo = st.text_input("O que você procura?", key="ps_termo", max_chars=120,
                              placeholder="Ex.: mercado, relatório, dentista")
        tipos = st.multiselect("Tipos", list(pesquisa.TIPOS), default=list(pesquisa.TIPOS),
                               format_func=pesquisa.TIPOS.get, key="ps_tipos")
        usar_periodo = st.checkbox("Filtrar por período", key="ps_usar_periodo",
                                   help="Usa o prazo das tarefas e metas, a data dos compromissos e a data de "
                                        "atualização das anotações.")
        c1, c2 = st.columns(2)
        inicio = c1.date_input("De", value=hoje() - timedelta(days=30), format=ui.formato_widget_data(), key="ps_ini")
        fim = c2.date_input("Até", value=hoje() + timedelta(days=30), format=ui.formato_widget_data(), key="ps_fim")
        enviado = st.form_submit_button("Pesquisar", type="primary", icon=":material/search:")

    if enviado:
        st.session_state["ps_ultima"] = (termo, tipos, inicio if usar_periodo else None, fim if usar_periodo else None)

    ultima = st.session_state.get("ps_ultima")
    if not ultima:
        ui.vazio("Digite uma palavra e clique em Pesquisar.", "A pesquisa ignora maiúsculas e minúsculas.")
        return
    termo, tipos, inicio, fim = ultima
    if not tipos:
        st.error("Escolha pelo menos um tipo para pesquisar.", icon="⚠️")
        return
    try:
        resultados = pesquisa.pesquisar(termo, tipos, inicio, fim)
    except ErroValidacao as erro:
        st.error(str(erro), icon="⚠️")
        return

    total = pesquisa.total(resultados)
    if total == 0:
        ui.vazio(f"Nada encontrado para “{termo}”.", "Confira a grafia, tente outra palavra ou remova o filtro de período.")
        return
    st.success(f"{total} resultado(s) para “{termo}”.", icon="🔎")
    for tipo, itens in resultados.items():
        if not itens:
            continue
        st.markdown(f"#### {pesquisa.TIPOS[tipo]} ({len(itens)})")
        for item in itens:
            with st.container(border=True):
                c1, c2 = st.columns([4, 1.2], vertical_alignment="center")
                with c1:
                    ui.titulo_item(item["titulo"], _descricao(tipo, item))
                if c2.button("Abrir", key=f"ps_ab_{tipo}_{item['id']}", icon=":material/open_in_new:",
                             width="stretch", help=f"Abrir “{item['titulo']}” na página {pesquisa.TIPOS[tipo]}"):
                    ui.abrir_item(tipo, item["id"])
