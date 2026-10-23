"""Metas pessoais com prazo, descrição, recorrência e progresso."""

from __future__ import annotations

from typing import Any

import streamlit as st

from assistente import repositorio
from assistente.tempo import para_date
from assistente.ui import componentes as ui
from assistente.validacao import RECORRENCIAS


def _formulario(prefixo: str, atual: dict[str, Any] | None = None) -> dict[str, Any] | None:
    atual = atual or {}
    with st.form(f"form_meta_{prefixo}", clear_on_submit=not atual):
        titulo = st.text_input("Título *", value=atual.get("titulo", ""), max_chars=120,
                               placeholder="Ex.: Ler 12 livros no ano")
        descricao = st.text_area("Descrição", value=atual.get("descricao", ""), height=80, max_chars=5000)
        c1, c2 = st.columns(2)
        prazo = c1.date_input("Prazo", value=para_date(atual.get("prazo")), format=ui.formato_widget_data(),
                              help="Opcional.")
        recorrencias = list(RECORRENCIAS)
        recorrencia = c2.selectbox("Recorrência", recorrencias,
                                   index=recorrencias.index(atual.get("recorrencia", "nenhuma")),
                                   format_func=RECORRENCIAS.get)
        progresso = st.slider("Progresso (%)", 0, 100, int(atual.get("progresso", 0)), step=5)
        if st.form_submit_button("Salvar alterações" if atual else "Criar meta", type="primary", icon=":material/save:"):
            return {"titulo": titulo, "descricao": descricao, "prazo": prazo, "recorrencia": recorrencia,
                    "progresso": progresso}
    return None


def _cartao(m: dict[str, Any], destaque: bool = False) -> None:
    with st.container(border=True):
        if destaque:
            st.info("Item aberto pela pesquisa.", icon=":material/search:")
        chips = ui.chips(
            ("Concluída", "concluida") if m["progresso"] == 100 else ("Em andamento", "neutra"),
            *([(RECORRENCIAS[m["recorrencia"]], "neutra")] if m["recorrencia"] != "nenhuma" else []),
            *([("Exemplo", "exemplo")] if m["exemplo"] else []),
        )
        ui.titulo_item(m["titulo"], f"Prazo: {ui.fmt_data(m['prazo'])}", chips_html=chips)
        if m["descricao"]:
            st.caption(m["descricao"])
        ui.barra("Progresso", m["progresso"], "--lume-dest")

        c1, c2, c3 = st.columns([2, 1, 1], vertical_alignment="bottom")
        novo = c1.slider("Atualizar progresso", 0, 100, int(m["progresso"]), step=5, key=f"m_sl_{m['id']}")
        if c2.button("Salvar", key=f"m_sv_{m['id']}", icon=":material/save:", width="stretch",
                     disabled=novo == m["progresso"]):
            ui.executar_acao(lambda: repositorio.atualizar_meta(m["id"], progresso=novo), "Progresso atualizado!")
        chave_exc = f"m_exc_{m['id']}"
        if c3.button("Excluir", key=f"m_del_{m['id']}", icon=":material/delete:", width="stretch"):
            st.session_state[chave_exc] = True
        ui.confirmar_exclusao(chave_exc, f"a meta “{m['titulo']}”", lambda: repositorio.excluir_meta(m["id"]),
                              "Meta excluída.")
        with st.expander("Editar meta", expanded=destaque):
            dados = _formulario(f"ed_{m['id']}", m)
            if dados is not None:
                if ui.executar_acao(lambda: repositorio.atualizar_meta(m["id"], **dados), "Meta atualizada!",
                                    rerun=False):
                    ui.limpar_foco()
                    st.rerun()


def render() -> None:
    ui.cabecalho("Metas", "Defina objetivos e acompanhe seu progresso.", "🎯")

    foco = ui.consumir_foco("metas")
    if foco:
        meta = repositorio.obter_meta(foco)
        if meta:
            _cartao(meta, destaque=True)
            if st.button("Fechar item aberto", key="m_fechar_foco"):
                ui.limpar_foco()
                st.rerun()
            st.divider()
        else:
            ui.limpar_foco()

    with st.expander("➕ Nova meta", expanded=not repositorio.listar_metas()):
        dados = _formulario("nova")
        if dados is not None:
            ui.executar_acao(lambda: repositorio.criar_meta(**dados), "Meta criada!")

    filtros = {"ativas": "Ativas", "concluidas": "Concluídas", "todas": "Todas"}
    filtro = st.segmented_control("Mostrar", list(filtros), format_func=filtros.get, default="ativas",
                                  key="m_filtro") or "ativas"
    metas = [m for m in repositorio.listar_metas(filtro) if m["id"] != foco]
    if not metas:
        ui.vazio("Nenhuma meta neste filtro.", "Use “Nova meta” acima. Dica: metas com prazo aparecem nas sugestões.")
        return
    for m in metas:
        _cartao(m)
