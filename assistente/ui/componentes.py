"""Componentes visuais reutilizados pelas páginas.

Todo texto vindo do usuário passa por `html.escape` antes de entrar em HTML.
"""

from __future__ import annotations

import html
from typing import Any, Callable

import streamlit as st

from assistente import configuracoes, db
from assistente import validacao as v
from assistente.tempo import formatar_data, formatar_hora

FORMATO_WIDGET_DATA = {"dd/mm/aaaa": "DD/MM/YYYY", "aaaa-mm-dd": "YYYY-MM-DD", "mm/dd/aaaa": "MM/DD/YYYY"}


def e(texto: Any) -> str:
    return html.escape(str(texto if texto is not None else ""))


# --- Configuração da sessão -------------------------------------------------------

def config() -> dict[str, Any]:
    """Configurações lidas uma vez por execução da página."""
    if "_config_cache" not in st.session_state or st.session_state.get("_config_sujo", True):
        st.session_state["_config_cache"] = configuracoes.obter_todas()
        st.session_state["_config_sujo"] = False
    return st.session_state["_config_cache"]


def invalidar_config() -> None:
    st.session_state["_config_sujo"] = True


def fmt_data(valor: Any) -> str:
    return formatar_data(valor, config()["formato_data"])


def fmt_hora(valor: Any) -> str:
    return formatar_hora(valor, config()["formato_hora"])


def formato_widget_data() -> str:
    return FORMATO_WIDGET_DATA.get(config()["formato_data"], "DD/MM/YYYY")


# --- Mensagens que sobrevivem ao st.rerun -------------------------------------------

def avisar(mensagem: str, tipo: str = "sucesso") -> None:
    st.session_state.setdefault("_flash", []).append((tipo, mensagem))


def mostrar_avisos() -> None:
    for tipo, mensagem in st.session_state.pop("_flash", []):
        if tipo == "sucesso":
            st.toast(mensagem, icon="✅")
            st.success(mensagem, icon="✅")
        elif tipo == "erro":
            st.error(mensagem, icon="⚠️")
        else:
            st.info(mensagem, icon="ℹ️")


def executar_acao(funcao: Callable[[], Any], sucesso: str, rerun: bool = True) -> bool:
    """Executa uma operação e mostra mensagem clara de sucesso ou erro."""
    try:
        funcao()
    except v.ErroValidacao as erro:
        st.error(str(erro), icon="⚠️")
        return False
    except db.ErroBanco as erro:
        st.error(str(erro), icon="⚠️")
        return False
    avisar(sucesso)
    if rerun:
        st.rerun()
    return True


# --- Navegação entre páginas e "abrir item" -------------------------------------------

def abrir_item(tipo: str, id_: int) -> None:
    from assistente.ui import navegacao

    st.session_state["_foco"] = (tipo, int(id_))
    st.switch_page(navegacao.pagina(tipo))


def consumir_foco(tipo: str) -> int | None:
    foco = st.session_state.get("_foco")
    if foco and foco[0] == tipo:
        return foco[1]
    return None


def limpar_foco() -> None:
    st.session_state.pop("_foco", None)


def ir_para(nome: str) -> None:
    from assistente.ui import navegacao

    st.switch_page(navegacao.pagina(nome))


# --- Blocos visuais ----------------------------------------------------------------

def cabecalho(titulo: str, subtitulo: str, icone: str) -> None:
    st.markdown(
        f'<div class="lume-hero"><div class="icone" aria-hidden="true">{e(icone)}</div>'
        f"<div><h1>{e(titulo)}</h1><p>{e(subtitulo)}</p></div></div>",
        unsafe_allow_html=True,
    )
    mostrar_avisos()


def metricas(itens: list[tuple[str, Any, str, str]]) -> None:
    """itens: (rótulo, valor, detalhe, variável de cor CSS)."""
    cartoes = "".join(
        f'<div class="lume-metric" style="--cor: var({cor})" role="group" aria-label="{e(rotulo)}: {e(valor)}">'
        f'<div class="rotulo">{e(rotulo)}</div><div class="valor">{e(valor)}</div>'
        f'<div class="detalhe">{e(detalhe)}</div></div>'
        for rotulo, valor, detalhe, cor in itens
    )
    st.markdown(f'<div class="lume-grid">{cartoes}</div>', unsafe_allow_html=True)


def barra(rotulo: str, percentual: int, cor: str = "--lume-pri") -> None:
    p = max(0, min(100, int(percentual)))
    st.markdown(
        f'<div class="lume-barra" role="progressbar" aria-valuenow="{p}" aria-valuemin="0" aria-valuemax="100" '
        f'aria-label="{e(rotulo)}"><div class="topo"><span>{e(rotulo)}</span><span>{p}%</span></div>'
        f'<div class="trilho"><div class="cheio" style="width:{p}%; --cor: var({cor})"></div></div></div>',
        unsafe_allow_html=True,
    )


def vazio(titulo: str, dica: str) -> None:
    st.markdown(f'<div class="lume-vazio"><strong>{e(titulo)}</strong><br>{e(dica)}</div>', unsafe_allow_html=True)


def chips(*itens: tuple[str, str]) -> str:
    return "".join(f'<span class="lume-chip {e(classe)}">{e(texto)}</span>' for texto, classe in itens)


def titulo_item(titulo: str, meta: str = "", feito: bool = False, chips_html: str = "") -> None:
    classe = "lume-item-titulo feito" if feito else "lume-item-titulo"
    st.markdown(
        f'<p class="{classe}">{e(titulo)}</p>'
        + (f'<p class="lume-item-meta">{chips_html}{e(meta)}</p>' if (meta or chips_html) else ""),
        unsafe_allow_html=True,
    )


def sugestao(icone: str, titulo: str, motivo: str) -> None:
    st.markdown(
        f'<div class="lume-sug"><div class="t">{e(icone)} {e(titulo)}</div>'
        f'<div class="m">Por quê: {e(motivo)}</div></div>',
        unsafe_allow_html=True,
    )


def confirmar_exclusao(chave: str, descricao: str, acao: Callable[[], Any], sucesso: str) -> None:
    """Fluxo de confirmação em duas etapas (funciona bem no celular)."""
    if st.session_state.get(chave):
        st.warning(f"Excluir {descricao}? Esta ação não pode ser desfeita.", icon="⚠️")
        c1, c2 = st.columns(2)
        if c1.button("Sim, excluir", key=f"{chave}_sim", type="primary", icon=":material/delete:"):
            st.session_state.pop(chave, None)
            executar_acao(acao, sucesso)
        if c2.button("Cancelar", key=f"{chave}_nao"):
            st.session_state.pop(chave, None)
            st.rerun()
