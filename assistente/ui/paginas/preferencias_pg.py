"""Preferências e memória controlada."""

from __future__ import annotations

import streamlit as st

from assistente import preferencias
from assistente.ui import componentes as ui


def render() -> None:
    ui.cabecalho("Preferências e memória", "Informações úteis que você escolhe guardar. Você tem controle total.", "🧠")
    st.info(
        "O assistente só lembra do que você cadastrar aqui. Nada é coletado automaticamente. "
        "Por segurança, senhas, tokens, chaves de API, CPF e números de cartão são recusados. "
        "Estas informações ficam separadas das suas tarefas e compromissos.",
        icon="🔒",
    )
    with st.expander("Como o app usa estas informações"):
        st.markdown(
            "- **Horários → `inicio do dia` / `fim do dia`** (formato HH:MM): usados pelo Planejador.\n"
            "- **Categorias favoritas**: aparecem como opções no cadastro de tarefas.\n"
            "- As demais informações ficam guardadas para sua consulta (por exemplo, metas recorrentes "
            "ou como prefere ver o painel)."
        )

    with st.form("form_pref", clear_on_submit=True):
        categoria = st.selectbox("Categoria", list(preferencias.CATEGORIAS), format_func=preferencias.CATEGORIAS.get)
        c1, c2 = st.columns(2)
        chave = c1.text_input("Nome da informação *", max_chars=60, placeholder="Ex.: inicio do dia")
        valor = c2.text_input("Valor *", max_chars=500, placeholder="Ex.: 08:00")
        if st.form_submit_button("Salvar na memória", type="primary", icon=":material/save:"):
            ui.executar_acao(lambda: preferencias.salvar(categoria, chave, valor), "Informação salva!")

    itens = preferencias.listar()
    if not itens:
        ui.vazio("Nenhuma informação salva.", "Exemplo: categoria Horários, nome “inicio do dia”, valor “08:00”.")
        return

    for cat, rotulo in preferencias.CATEGORIAS.items():
        do_grupo = [p for p in itens if p["categoria"] == cat]
        if not do_grupo:
            continue
        st.markdown(f"#### {rotulo}")
        for p in do_grupo:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1], vertical_alignment="bottom")
                novo = c1.text_input(p["chave"].replace("_", " "), value=p["valor"], key=f"pf_v_{p['id']}",
                                     max_chars=500)
                if c2.button("Salvar", key=f"pf_s_{p['id']}", icon=":material/save:", width="stretch",
                             disabled=novo == p["valor"]):
                    ui.executar_acao(lambda i=p["id"], val=novo: preferencias.editar(i, val), "Informação atualizada!")
                if c3.button("Excluir", key=f"pf_d_{p['id']}", icon=":material/delete:", width="stretch"):
                    ui.executar_acao(lambda i=p["id"]: preferencias.excluir(i), "Informação excluída.")

    st.divider()
    chave_limpar = "pf_limpar"
    if st.button("Limpar toda a memória", icon=":material/delete_forever:"):
        st.session_state[chave_limpar] = True
    ui.confirmar_exclusao(chave_limpar, f"todas as {len(itens)} informações salvas (tarefas e compromissos não são afetados)",
                          preferencias.limpar_tudo, "Memória limpa.")
