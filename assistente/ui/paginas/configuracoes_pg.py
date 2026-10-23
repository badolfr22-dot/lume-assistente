"""Configurações do assistente."""

from __future__ import annotations

import streamlit as st

from assistente import configuracoes as cfg_mod, db, demo, exportacao, usuarios
from assistente import validacao as v
from assistente.config import configuracao
from assistente.tempo import FORMATOS_DATA, FORMATOS_HORA, agora
from assistente.ui import componentes as ui

EXEMPLO_DATA = {"dd/mm/aaaa": "22/10/2026", "aaaa-mm-dd": "2026-10-22", "mm/dd/aaaa": "10/22/2026"}
EXEMPLO_HORA = {"24h": "14:30", "12h": "02:30 PM"}


def _minha_conta(conta: dict) -> None:
    st.markdown("#### Minha conta")
    st.caption(f"E-mail: {conta['email']}")
    with st.expander("Alterar nome"):
        with st.form("form_nome"):
            nome = st.text_input("Nome", value=conta["nome"], max_chars=60)
            if st.form_submit_button("Salvar nome", icon=":material/save:"):
                def salvar_nome() -> None:
                    usuarios.alterar_nome(conta["id"], nome)
                    st.session_state["_usuario"] = {**conta, "nome": nome.strip()}
                ui.executar_acao(salvar_nome, "Nome atualizado!")
    with st.expander("Alterar senha"):
        with st.form("form_senha", clear_on_submit=True):
            atual = st.text_input("Senha atual", type="password", max_chars=128, autocomplete="current-password")
            nova = st.text_input("Nova senha", type="password", max_chars=128, autocomplete="new-password",
                                 help=f"Pelo menos {usuarios.SENHA_MINIMA} caracteres, com letras e números.")
            confirmacao = st.text_input("Confirme a nova senha", type="password", max_chars=128,
                                        autocomplete="new-password")
            if st.form_submit_button("Alterar senha", icon=":material/key:"):
                ui.executar_acao(lambda: usuarios.alterar_senha(conta["id"], atual, nova, confirmacao),
                                 "Senha alterada!")
    with st.expander("Excluir minha conta"):
        st.warning("Isto apaga sua conta e **todos** os seus dados (tarefas, metas, agenda, anotações, "
                   "preferências, lembretes e automações). Não dá para desfazer. Se quiser, baixe seus dados antes "
                   "(seção Exportar meus dados).", icon="⚠️")
        with st.form("form_excluir_conta", clear_on_submit=True):
            senha = st.text_input("Digite sua senha para confirmar", type="password", max_chars=128,
                                  autocomplete="current-password")
            certeza = st.checkbox("Entendo que meus dados serão apagados para sempre")
            if st.form_submit_button("Excluir minha conta", icon=":material/delete_forever:"):
                if not certeza:
                    st.error("Marque a caixa de confirmação para excluir a conta.", icon="⚠️")
                else:
                    try:
                        usuarios.excluir_conta(conta["id"], senha)
                    except v.ErroValidacao as erro:
                        st.error(str(erro), icon="⚠️")
                    else:
                        st.session_state.clear()
                        st.rerun()


def render() -> None:
    ui.cabecalho("Configurações", "Personalize o assistente. As mudanças ficam salvas no seu perfil.", "⚙️")
    cfg = ui.config()
    conta = st.session_state.get("_usuario")

    with st.form("form_config"):
        st.markdown("#### Geral")
        c1, c2 = st.columns(2)
        nome_assistente = c1.text_input("Nome do assistente *", value=cfg["nome_assistente"], max_chars=40)
        nome_usuario = c2.text_input("Como devo chamar você?", value=cfg["nome_usuario"], max_chars=40,
                                     help="Opcional. Aparece na saudação do painel.")

        st.markdown("#### Aparência")
        temas = list(cfg_mod.TEMAS)
        tema = st.radio("Tema", temas, index=temas.index(cfg["tema"]), format_func=cfg_mod.TEMAS.get, horizontal=True)
        c1, c2 = st.columns(2)
        formatos_d = list(FORMATOS_DATA)
        formato_data = c1.selectbox("Formato de data", formatos_d, index=formatos_d.index(cfg["formato_data"]),
                                    format_func=lambda f: f"{f.upper()} (ex.: {EXEMPLO_DATA[f]})")
        formatos_h = list(FORMATOS_HORA)
        formato_hora = c2.selectbox("Formato de hora", formatos_h, index=formatos_h.index(cfg["formato_hora"]),
                                    format_func=lambda f: f"{f} (ex.: {EXEMPLO_HORA[f]})")

        st.markdown("#### Notificações")
        notif_tipos = st.multiselect("Quais avisos você quer receber?", list(cfg_mod.TIPOS_NOTIFICACAO),
                                     default=cfg["notificacoes_tipos"], format_func=cfg_mod.TIPOS_NOTIFICACAO.get)
        c1, c2 = st.columns(2)
        antecedencia = c1.number_input("Avisar prazos com quantos dias de antecedência", 0, 30,
                                       int(cfg["notificacoes_antecedencia_dias"]))
        minutos_comp = c2.number_input("Avisar compromissos quantos minutos antes", 5, 240,
                                       int(cfg["notificacoes_compromisso_min"]), step=5)

        st.markdown("#### Sugestões automáticas")
        sug_ativas = st.toggle("Mostrar sugestões inteligentes", value=bool(cfg["sugestoes_ativas"]))
        sug_tipos = st.multiselect("Tipos de sugestão", list(cfg_mod.TIPOS_SUGESTAO), default=cfg["sugestoes_tipos"],
                                   format_func=cfg_mod.TIPOS_SUGESTAO.get)
        sug_max = st.slider("Máximo de sugestões no painel", 1, 10, int(cfg["sugestoes_maximo"]))

        if st.form_submit_button("Salvar configurações", type="primary", icon=":material/save:"):
            def salvar() -> None:
                cfg_mod.salvar({
                    "nome_assistente": nome_assistente, "nome_usuario": nome_usuario, "tema": tema,
                    "formato_data": formato_data, "formato_hora": formato_hora,
                    "notificacoes_tipos": notif_tipos, "notificacoes_antecedencia_dias": antecedencia,
                    "notificacoes_compromisso_min": minutos_comp, "sugestoes_ativas": sug_ativas,
                    "sugestoes_tipos": sug_tipos, "sugestoes_maximo": sug_max,
                })
                ui.invalidar_config()
            ui.executar_acao(salvar, "Configurações salvas!")

    st.markdown("#### Exportar meus dados")
    st.caption("Baixe uma cópia de tudo o que está salvo (tarefas, metas, agenda, anotações, preferências, "
               "configurações, notificações e automações). O arquivo fica só com você.")
    carimbo = agora().strftime("%Y%m%d-%H%M")
    if st.button("Preparar exportação", icon=":material/inventory_2:"):
        st.session_state["cfg_export"] = (exportacao.para_json(), exportacao.para_zip_csv())
    if "cfg_export" in st.session_state:
        dados_json, dados_zip = st.session_state["cfg_export"]
        c1, c2 = st.columns(2)
        c1.download_button("Baixar JSON (completo)", dados_json, f"assistente-{carimbo}.json", "application/json",
                           icon=":material/download:", width="stretch")
        c2.download_button("Baixar CSV (planilhas, .zip)", dados_zip, f"assistente-{carimbo}.zip", "application/zip",
                           icon=":material/download:", width="stretch")

    st.markdown("#### Dados de exemplo")
    qtd = demo.contar()
    st.caption("Para conhecer o app sem digitar nada. Os exemplos têm o prefixo “[Exemplo]” e podem ser removidos "
               "sem afetar seus dados reais.")
    c1, c2 = st.columns(2)
    if c1.button("Carregar exemplos", icon=":material/science:", disabled=qtd > 0, width="stretch"):
        ui.executar_acao(demo.carregar, "Exemplos carregados. Eles estão marcados como [Exemplo].")
    if c2.button(f"Remover exemplos ({qtd})", icon=":material/delete:", disabled=qtd == 0, width="stretch"):
        ui.executar_acao(demo.remover, "Exemplos removidos. Seus dados reais foram mantidos.")

    st.markdown("#### Restaurar padrões")
    st.caption("Volta nome, tema, formatos, notificações e sugestões ao padrão. "
               "Suas tarefas, metas, compromissos, anotações e preferências NÃO são apagados.")
    chave = "cfg_restaurar"
    if st.button("Restaurar configurações padrão", icon=":material/restart_alt:"):
        st.session_state[chave] = True
    if st.session_state.get(chave):
        st.warning("Restaurar as configurações padrão?", icon="⚠️")
        c1, c2 = st.columns(2)
        if c1.button("Sim, restaurar", type="primary", key="cfg_rest_sim"):
            st.session_state.pop(chave, None)
            cfg_mod.restaurar_padroes()
            ui.invalidar_config()
            ui.avisar("Configurações restauradas para o padrão.")
            st.rerun()
        if c2.button("Cancelar", key="cfg_rest_nao"):
            st.session_state.pop(chave, None)
            st.rerun()

    if conta:
        _minha_conta(conta)
    elif not configuracao().producao and not db.usando_postgres():
        st.markdown("#### Onde ficam meus dados")
        st.caption(f"Banco SQLite local: `{db.caminho_banco()}`. Para backup, use `scripts\\backup.py` "
                   "(veja o README).")
