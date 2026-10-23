"""Anotações: criar, editar, pesquisar e excluir."""

from __future__ import annotations

from typing import Any

import streamlit as st

from assistente import repositorio
from assistente.ui import componentes as ui


def _formulario(prefixo: str, atual: dict[str, Any] | None = None) -> dict[str, Any] | None:
    atual = atual or {}
    with st.form(f"form_nota_{prefixo}", clear_on_submit=not atual):
        titulo = st.text_input("Título *", value=atual.get("titulo", ""), max_chars=120)
        conteudo = st.text_area("Texto", value=atual.get("conteudo", ""), height=140, max_chars=5000)
        tags = st.text_input("Etiquetas", value=atual.get("tags", ""), max_chars=120,
                             placeholder="Separe por vírgula. Ex.: casa, ideias")
        if st.form_submit_button("Salvar alterações" if atual else "Salvar anotação", type="primary",
                                 icon=":material/save:"):
            return {"titulo": titulo, "conteudo": conteudo, "tags": tags}
    return None


def _cartao(n: dict[str, Any], destaque: bool = False) -> None:
    with st.container(border=True):
        if destaque:
            st.info("Item aberto pela pesquisa.", icon=":material/search:")
        chips = ui.chips(*[(t, "neutra") for t in n["tags"].split(", ") if t],
                         *([("Exemplo", "exemplo")] if n["exemplo"] else []))
        ui.titulo_item(n["titulo"], f"Atualizada em {ui.fmt_data(n['atualizado_em'])}", chips_html=chips)
        if n["conteudo"]:
            st.text(n["conteudo"])
        b1, b2 = st.columns(2)
        chave_ed = f"n_edit_{n['id']}"
        if b1.button("Editar", key=f"n_ed_{n['id']}", icon=":material/edit:", width="stretch"):
            st.session_state[chave_ed] = not st.session_state.get(chave_ed, False)
        chave_exc = f"n_exc_{n['id']}"
        if b2.button("Excluir", key=f"n_del_{n['id']}", icon=":material/delete:", width="stretch"):
            st.session_state[chave_exc] = True
        ui.confirmar_exclusao(chave_exc, f"a anotação “{n['titulo']}”", lambda: repositorio.excluir_anotacao(n["id"]),
                              "Anotação excluída.")
        if st.session_state.get(chave_ed) or destaque:
            dados = _formulario(f"ed_{n['id']}", n)
            if dados is not None:
                if ui.executar_acao(lambda: repositorio.atualizar_anotacao(n["id"], **dados), "Anotação atualizada!",
                                    rerun=False):
                    st.session_state[chave_ed] = False
                    ui.limpar_foco()
                    st.rerun()


def render() -> None:
    ui.cabecalho("Anotações", "Ideias, listas e lembretes rápidos.", "📝")

    foco = ui.consumir_foco("anotacoes")
    if foco:
        nota = repositorio.obter_anotacao(foco)
        if nota:
            _cartao(nota, destaque=True)
            if st.button("Fechar item aberto", key="n_fechar_foco"):
                ui.limpar_foco()
                st.rerun()
            st.divider()
        else:
            ui.limpar_foco()

    with st.expander("➕ Nova anotação", expanded=not repositorio.listar_anotacoes()):
        dados = _formulario("nova")
        if dados is not None:
            ui.executar_acao(lambda: repositorio.criar_anotacao(**dados), "Anotação salva!")

    busca = st.text_input("Pesquisar nas anotações", key="n_busca", placeholder="Digite uma palavra e pressione Enter",
                          max_chars=120)
    notas = [n for n in repositorio.listar_anotacoes(busca) if n["id"] != foco]
    if not notas:
        if busca:
            ui.vazio(f"Nenhuma anotação com “{busca}”.", "Tente outra palavra ou apague a pesquisa.")
        else:
            ui.vazio("Nenhuma anotação ainda.", "Use “Nova anotação” acima ou o painel principal.")
        return
    st.caption(f"{len(notas)} anotação(ões)")
    for n in notas:
        _cartao(n)
