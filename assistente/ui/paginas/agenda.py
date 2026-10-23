"""Agenda: compromissos com data, horário, local e descrição."""

from __future__ import annotations

from datetime import time, timedelta
from typing import Any

import streamlit as st

from assistente import planejador, repositorio
from assistente.tempo import data_por_extenso, hoje, para_date
from assistente.ui import componentes as ui


def _hora(texto: str | None, padrao: time) -> time:
    if not texto:
        return padrao
    h, m = texto.split(":")
    return time(int(h), int(m))


def _formulario(prefixo: str, atual: dict[str, Any] | None = None) -> dict[str, Any] | None:
    atual = atual or {}
    with st.form(f"form_comp_{prefixo}", clear_on_submit=not atual):
        titulo = st.text_input("Título *", value=atual.get("titulo", ""), max_chars=120,
                               placeholder="Ex.: Consulta no dentista")
        c1, c2, c3 = st.columns(3)
        data = c1.date_input("Data *", value=para_date(atual.get("data")) or hoje(), format=ui.formato_widget_data())
        inicio = c2.time_input("Início *", value=_hora(atual.get("hora_inicio"), time(9, 0)), step=timedelta(minutes=15))
        fim = c3.time_input("Fim *", value=_hora(atual.get("hora_fim"), time(10, 0)), step=timedelta(minutes=15))
        local = st.text_input("Local", value=atual.get("local", ""), max_chars=120, placeholder="Opcional")
        descricao = st.text_area("Descrição", value=atual.get("descricao", ""), height=70, max_chars=5000)
        if st.form_submit_button("Salvar alterações" if atual else "Adicionar compromisso", type="primary",
                                 icon=":material/save:"):
            return {"titulo": titulo, "data": data, "hora_inicio": inicio, "hora_fim": fim, "local": local,
                    "descricao": descricao}
    return None


def _cartao(c: dict[str, Any], conflito: bool, destaque: bool = False) -> None:
    with st.container(border=True):
        if destaque:
            st.info("Item aberto pela pesquisa.", icon=":material/search:")
        chips = ui.chips(*([("Conflito de horário", "atrasada")] if conflito else []),
                         *([("Exemplo", "exemplo")] if c["exemplo"] else []))
        meta = f"{ui.fmt_hora(c['hora_inicio'])}–{ui.fmt_hora(c['hora_fim'])}"
        if c["local"]:
            meta += f" · {c['local']}"
        ui.titulo_item(c["titulo"], meta, chips_html=chips)
        if c["descricao"]:
            st.caption(c["descricao"])
        b1, b2 = st.columns(2)
        chave_ed = f"c_edit_{c['id']}"
        if b1.button("Editar", key=f"c_ed_{c['id']}", icon=":material/edit:", width="stretch"):
            st.session_state[chave_ed] = not st.session_state.get(chave_ed, False)
        chave_exc = f"c_exc_{c['id']}"
        if b2.button("Excluir", key=f"c_del_{c['id']}", icon=":material/delete:", width="stretch"):
            st.session_state[chave_exc] = True
        ui.confirmar_exclusao(chave_exc, f"o compromisso “{c['titulo']}”",
                              lambda: repositorio.excluir_compromisso(c["id"]), "Compromisso excluído.")
        if st.session_state.get(chave_ed) or destaque:
            dados = _formulario(f"ed_{c['id']}", c)
            if dados is not None:
                if ui.executar_acao(lambda: repositorio.atualizar_compromisso(c["id"], **dados),
                                    "Compromisso atualizado!", rerun=False):
                    st.session_state[chave_ed] = False
                    ui.limpar_foco()
                    st.rerun()


def render() -> None:
    ui.cabecalho("Agenda", "Seus compromissos com data e horário.", "📅")
    dia = hoje()

    foco = ui.consumir_foco("compromissos")
    if foco:
        comp = repositorio.obter_compromisso(foco)
        if comp:
            _cartao(comp, False, destaque=True)
            if st.button("Fechar item aberto", key="c_fechar_foco"):
                ui.limpar_foco()
                st.rerun()
            st.divider()
        else:
            ui.limpar_foco()

    with st.expander("➕ Novo compromisso", expanded=not repositorio.listar_compromissos()):
        dados = _formulario("novo")
        if dados is not None:
            ui.executar_acao(lambda: repositorio.criar_compromisso(**dados), "Compromisso adicionado!")

    periodos = {"7": "Próximos 7 dias", "30": "Próximos 30 dias", "passados": "Anteriores", "todos": "Todos"}
    periodo = st.segmented_control("Período", list(periodos), format_func=periodos.get, default="7",
                                   key="c_periodo") or "7"
    if periodo == "passados":
        itens = list(reversed(repositorio.listar_compromissos(fim=dia - timedelta(days=1))))
    elif periodo == "todos":
        itens = repositorio.listar_compromissos()
    else:
        itens = repositorio.listar_compromissos(dia, dia + timedelta(days=int(periodo)))
    itens = [c for c in itens if c["id"] != foco]

    conflitos = planejador.encontrar_conflitos(itens)
    em_conflito = {c["id"] for par in conflitos for c in par}
    for a, b in conflitos:
        st.warning(f"Conflito em {ui.fmt_data(a['data'])}: “{a['titulo']}” ({a['hora_inicio']}–{a['hora_fim']}) e "
                   f"“{b['titulo']}” ({b['hora_inicio']}–{b['hora_fim']}) se sobrepõem.", icon="⚠️")

    if not itens:
        ui.vazio("Nenhum compromisso neste período.", "Use “Novo compromisso” acima para agendar.")
        return
    dia_atual = None
    for c in itens:
        if c["data"] != dia_atual:
            dia_atual = c["data"]
            d = para_date(dia_atual)
            rotulo = "Hoje" if d == dia else ("Amanhã" if d == dia + timedelta(days=1) else "")
            st.markdown(f"**{data_por_extenso(d).capitalize()}**" + (f" · {rotulo}" if rotulo else ""))
        _cartao(c, c["id"] in em_conflito)
