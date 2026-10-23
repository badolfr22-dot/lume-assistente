"""Automações configuráveis e histórico."""

from __future__ import annotations

import streamlit as st

from assistente import automacoes
from assistente.ui import componentes as ui

SITUACOES = {"ok": "✅ Executada", "sem_acao": "➖ Sem ação necessária", "erro": "⚠️ Erro"}


def render() -> None:
    ui.cabecalho("Automações", "Regras que verificam seus dados e criam avisos e resumos para você.", "⚡")
    st.caption("As automações ativas rodam uma vez por dia, quando você abre o app. Elas apenas criam avisos "
               "dentro do app: nunca excluem dados, concluem tarefas, alteram compromissos ou enviam nada para fora.")

    with st.expander("➕ Nova automação", expanded=not automacoes.listar()):
        tipo = st.selectbox("Tipo de automação", list(automacoes.TIPOS), format_func=lambda k: automacoes.TIPOS[k].nome,
                            key="au_tipo")
        definicao = automacoes.TIPOS[tipo]
        st.info(definicao.descricao, icon="ℹ️")
        with st.form("form_automacao", clear_on_submit=True):
            nome = st.text_input("Nome *", value="", max_chars=60, placeholder=definicao.nome)
            parametros = {}
            for chave, (rotulo, padrao, minimo, maximo) in definicao.parametros.items():
                parametros[chave] = st.number_input(rotulo, minimo, maximo, padrao, key=f"au_p_{tipo}_{chave}")
            if st.form_submit_button("Criar automação", type="primary", icon=":material/add:"):
                ui.executar_acao(lambda: automacoes.criar(nome or definicao.nome, tipo, parametros), "Automação criada!")

    lista = automacoes.listar()
    if not lista:
        ui.vazio("Nenhuma automação criada.", "Crie a primeira acima. Sugestão: “Resumo diário”.")
    else:
        if st.button("Executar todas as ativas agora", icon=":material/play_arrow:"):
            ativas = [a for a in lista if a["ativa"]]
            for a in ativas:
                automacoes.executar(a["id"])
            ui.avisar(f"{len(ativas)} automação(ões) executada(s). Veja o histórico abaixo.")
            st.rerun()
    for a in lista:
        with st.container(border=True):
            definicao = automacoes.TIPOS.get(a["tipo"])
            parametros = ", ".join(f"{definicao.parametros[k][0].lower()}: {v}" for k, v in a["parametros"].items()) \
                if definicao else ""
            ultima = f"Última execução: {ui.fmt_data(a['ultima_execucao'])} {a['ultima_execucao'][11:16]}" \
                if a["ultima_execucao"] else "Ainda não executada"
            ui.titulo_item(a["nome"], f"{definicao.nome if definicao else a['tipo']}"
                           + (f" · {parametros}" if parametros else "") + f" · {ultima}",
                           chips_html=ui.chips(("Ativa", "concluida") if a["ativa"] else ("Desativada", "neutra")))
            c1, c2, c3 = st.columns(3)
            ativa = c1.toggle("Ativa", value=bool(a["ativa"]), key=f"au_on_{a['id']}")
            if ativa != bool(a["ativa"]):
                automacoes.definir_ativa(a["id"], ativa)
                ui.avisar("Automação ativada." if ativa else "Automação desativada.")
                st.rerun()
            if c2.button("Executar agora", key=f"au_run_{a['id']}", icon=":material/play_arrow:", width="stretch"):
                resultado = automacoes.executar(a["id"])
                ui.avisar(f"{SITUACOES[resultado.situacao]}: {resultado.mensagem}",
                          "erro" if resultado.situacao == "erro" else "sucesso")
                st.rerun()
            chave_exc = f"au_exc_{a['id']}"
            if c3.button("Excluir", key=f"au_del_{a['id']}", icon=":material/delete:", width="stretch"):
                st.session_state[chave_exc] = True
            ui.confirmar_exclusao(chave_exc, f"a automação “{a['nome']}” (o histórico é mantido)",
                                  lambda: automacoes.excluir(a["id"]), "Automação excluída.")

    st.markdown("#### Histórico de execuções")
    historico = automacoes.historico()
    if not historico:
        ui.vazio("Nenhuma execução registrada.", "Quando uma automação rodar, o resultado aparece aqui.")
        return
    st.dataframe(
        [{"Quando": h["executado_em"][:16], "Automação": h["nome_automacao"], "Resultado": SITUACOES[h["situacao"]],
          "Detalhes": h["mensagem"]} for h in historico],
        hide_index=True, width="stretch",
    )
    chave = "au_limpar_hist"
    if st.button("Limpar histórico", icon=":material/delete_sweep:", type="tertiary"):
        st.session_state[chave] = True
    ui.confirmar_exclusao(chave, "todo o histórico de execuções", automacoes.limpar_historico, "Histórico limpo.")
