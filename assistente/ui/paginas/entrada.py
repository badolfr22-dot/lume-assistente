"""Tela de entrada: login e criação de conta (modo com contas)."""

from __future__ import annotations

import streamlit as st

from assistente import acesso, config, usuarios
from assistente import validacao as v
from assistente.ui import componentes as ui

AVISO_PRIVACIDADE = """
**Aviso de privacidade (resumo)**

- **O que guardamos:** seu nome, seu e-mail, um código gerado a partir da sua senha (a senha em si nunca é
  guardada) e o que você cadastrar no app (tarefas, metas, agenda, anotações, preferências, lembretes e automações).
- **Para quê:** só para o app funcionar para você. Não usamos seus dados para propaganda, não vendemos e
  não compartilhamos com ninguém.
- **Onde:** num banco de dados na hospedagem do app, acessado por conexão protegida.
- **Quem vê:** só você vê seus dados dentro do app. Quem administra a hospedagem tem acesso técnico ao banco.
- **Seus direitos (LGPD):** você pode baixar todos os seus dados e excluir sua conta a qualquer momento em
  *Configurações → Minha conta*. Ao excluir, tudo é apagado.
- **Cookies e rastreamento:** o app não usa ferramentas de rastreamento nem estatísticas de uso.
"""


def _entrar(usuario: dict) -> None:
    st.session_state.clear()
    st.session_state["_usuario"] = usuario
    st.rerun()


def render() -> None:
    _, centro, _ = st.columns([1, 2.2, 1])
    with centro:
        st.markdown(
            '<div class="lume-hero"><div class="icone" aria-hidden="true">✨</div><div><h1>Lume</h1>'
            "<p>Seu assistente pessoal de produtividade.</p></div></div>",
            unsafe_allow_html=True,
        )
        controle = st.session_state.setdefault("_tentativas", acesso.ControleTentativas())
        aba_entrar, aba_criar = st.tabs(["Entrar", "Criar conta"])

        with aba_entrar:
            with st.form("form_entrar"):
                email = st.text_input("E-mail", max_chars=254, autocomplete="email")
                senha = st.text_input("Senha", type="password", max_chars=128, autocomplete="current-password")
                enviado = st.form_submit_button("Entrar", type="primary", icon=":material/login:", width="stretch")
            if enviado:
                if controle.bloqueado():
                    st.error("Muitas tentativas erradas. Aguarde um minuto e tente novamente.", icon="⚠️")
                else:
                    try:
                        _entrar(usuarios.autenticar(email, senha))
                    except v.ErroValidacao as erro:
                        controle.registrar_erro()
                        st.error(str(erro), icon="⚠️")

        with aba_criar:
            exige_convite = bool(config.configuracao().codigo_convite)
            with st.form("form_criar"):
                nome = st.text_input("Seu nome *", max_chars=60, autocomplete="name")
                email_novo = st.text_input("E-mail *", max_chars=254, autocomplete="email")
                senha_nova = st.text_input("Senha *", type="password", max_chars=128, autocomplete="new-password",
                                           help=f"Pelo menos {usuarios.SENHA_MINIMA} caracteres, com letras e números.")
                confirmacao = st.text_input("Confirme a senha *", type="password", max_chars=128,
                                            autocomplete="new-password")
                convite = ""
                if exige_convite:
                    convite = st.text_input("Código de convite *", type="password", max_chars=100,
                                            help="Peça o código a quem te convidou para usar o app.")
                with st.expander("Ler o aviso de privacidade"):
                    st.markdown(AVISO_PRIVACIDADE)
                aceitou = st.checkbox("Li e concordo com o aviso de privacidade")
                criar = st.form_submit_button("Criar conta", type="primary", icon=":material/person_add:",
                                              width="stretch")
            if criar:
                # Limite por sessão; o limite geral (todas as sessões) fica em usuarios.limite_convite.
                controle_convite = st.session_state.setdefault("_tentativas_convite", acesso.ControleTentativas())
                if exige_convite and controle_convite.bloqueado():
                    st.error("Muitas tentativas com código de convite errado. Aguarde um minuto e tente novamente.",
                             icon="⚠️")
                else:
                    try:
                        _entrar(usuarios.criar_conta(email_novo, nome, senha_nova, confirmacao, convite, aceitou))
                    except v.ErroValidacao as erro:
                        if str(erro).startswith("Código de convite incorreto"):
                            controle_convite.registrar_erro()
                        st.error(str(erro), icon="⚠️")
        st.caption("Esqueceu a senha? Por enquanto, peça ajuda a quem administra o app.")
    ui.mostrar_avisos()
