"""Tarefas: cadastrar, editar, concluir, excluir e filtrar."""

from __future__ import annotations

from typing import Any

import streamlit as st

from assistente import planejador, preferencias, repositorio
from assistente.tempo import hoje, para_date
from assistente.ui import componentes as ui
from assistente.validacao import PRIORIDADES, STATUS_TAREFA


def _opcoes_categoria() -> list[str]:
    return sorted(set(preferencias.categorias_favoritas()) | set(repositorio.categorias_tarefas()))


def _formulario(prefixo: str, atual: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Campos comuns de criação/edição. Devolve os dados quando o formulário é enviado."""
    atual = atual or {}
    with st.form(f"form_{prefixo}", clear_on_submit=not atual):
        titulo = st.text_input("Título *", value=atual.get("titulo", ""), max_chars=120,
                               placeholder="Ex.: Pagar a conta de luz", help="Obrigatório. Até 120 caracteres.")
        descricao = st.text_area("Descrição", value=atual.get("descricao", ""), height=80, max_chars=5000)
        c1, c2 = st.columns(2)
        prioridades = list(PRIORIDADES)
        prioridade = c1.selectbox("Prioridade", prioridades, index=prioridades.index(atual.get("prioridade", "media")),
                                  format_func=PRIORIDADES.get)
        prazo = c2.date_input("Prazo", value=para_date(atual.get("prazo")), format=ui.formato_widget_data(),
                              help="Opcional. Deixe vazio se não houver prazo.")
        c3, c4 = st.columns(2)
        categorias = _opcoes_categoria()
        cat_atual = atual.get("categoria") or None
        if cat_atual and cat_atual not in categorias:
            categorias.append(cat_atual)
        categoria = c3.selectbox("Categoria", categorias, index=categorias.index(cat_atual) if cat_atual else None,
                                 accept_new_options=True, placeholder="Escolha ou digite uma nova",
                                 help="Suas categorias favoritas (Preferências) aparecem aqui.")
        duracao = c4.number_input("Duração estimada (min)", min_value=5, max_value=720, step=5,
                                  value=int(atual.get("duracao_min", 30)), help="Usada pelo planejador do dia.")
        status = None
        if atual:
            estados = list(STATUS_TAREFA)
            status = st.selectbox("Status", estados, index=estados.index(atual["status"]), format_func=STATUS_TAREFA.get)
        rotulo = "Salvar alterações" if atual else "Adicionar tarefa"
        if st.form_submit_button(rotulo, type="primary", icon=":material/save:"):
            dados = {"titulo": titulo, "descricao": descricao, "prioridade": prioridade, "prazo": prazo,
                     "categoria": categoria or "", "duracao_min": duracao}
            if status:
                dados["status"] = status
            return dados
    return None


def _cartao(t: dict[str, Any], destaque: bool = False) -> None:
    dia = hoje()
    with st.container(border=True):
        if destaque:
            st.info("Item aberto pela pesquisa.", icon=":material/search:")
        atrasada = repositorio.esta_atrasada(t, dia)
        chips = ui.chips(
            (PRIORIDADES[t["prioridade"]], t["prioridade"]),
            (STATUS_TAREFA[t["status"]], "concluida" if t["status"] == "concluida" else "neutra"),
            *([("Atrasada", "atrasada")] if atrasada else []),
            *([("Exemplo", "exemplo")] if t["exemplo"] else []),
        )
        meta = f"Prazo: {ui.fmt_data(t['prazo'])} · {t['duracao_min']} min"
        if t["categoria"]:
            meta += f" · {t['categoria']}"
        ui.titulo_item(t["titulo"], meta, feito=t["status"] == "concluida", chips_html=chips)
        if t["descricao"]:
            st.caption(t["descricao"])

        b1, b2, b3 = st.columns(3)
        if t["status"] == "concluida":
            if b1.button("Reabrir", key=f"t_re_{t['id']}", icon=":material/undo:", width="stretch"):
                ui.executar_acao(lambda: repositorio.reabrir_tarefa(t["id"]), "Tarefa reaberta.")
        elif b1.button("Concluir", key=f"t_ok_{t['id']}", icon=":material/check:", type="primary", width="stretch"):
            ui.executar_acao(lambda: repositorio.concluir_tarefa(t["id"]), "Tarefa concluída!")
        chave_edicao = f"t_edit_{t['id']}"
        if b2.button("Editar", key=f"t_ed_{t['id']}", icon=":material/edit:", width="stretch"):
            st.session_state[chave_edicao] = not st.session_state.get(chave_edicao, False)
        chave_exc = f"t_exc_{t['id']}"
        if b3.button("Excluir", key=f"t_del_{t['id']}", icon=":material/delete:", width="stretch"):
            st.session_state[chave_exc] = True
        ui.confirmar_exclusao(chave_exc, f"a tarefa “{t['titulo']}”", lambda: repositorio.excluir_tarefa(t["id"]),
                              "Tarefa excluída.")
        if st.session_state.get(chave_edicao) or destaque:
            dados = _formulario(f"editar_{t['id']}", t)
            if dados is not None:
                if ui.executar_acao(lambda: repositorio.atualizar_tarefa(t["id"], **dados), "Tarefa atualizada!",
                                    rerun=False):
                    st.session_state[chave_edicao] = False
                    ui.limpar_foco()
                    st.rerun()


def render() -> None:
    ui.cabecalho("Tarefas", "Cadastre, priorize e acompanhe o que precisa ser feito.", "✅")

    foco = ui.consumir_foco("tarefas")
    if foco:
        tarefa = repositorio.obter_tarefa(foco)
        if tarefa:
            _cartao(tarefa, destaque=True)
            if st.button("Fechar item aberto", key="t_fechar_foco"):
                ui.limpar_foco()
                st.rerun()
            st.divider()
        else:
            ui.limpar_foco()

    with st.expander("➕ Nova tarefa", expanded=not repositorio.listar_tarefas()):
        dados = _formulario("nova")
        if dados is not None:
            ui.executar_acao(lambda: repositorio.criar_tarefa(**dados), "Tarefa adicionada!")

    ind = repositorio.indicadores()
    rotulos = {
        "pendentes": f"Pendentes ({ind['tarefas_pendentes']})",
        "atrasadas": f"Atrasadas ({ind['tarefas_atrasadas']})",
        "hoje": f"Para hoje ({ind['tarefas_hoje']})",
        "concluidas": f"Concluídas ({ind['tarefas_concluidas']})",
        "todas": f"Todas ({ind['tarefas_total']})",
    }
    c1, c2 = st.columns([3, 1.3], vertical_alignment="bottom")
    with c1:
        filtro = st.segmented_control("Mostrar", list(rotulos), format_func=rotulos.get, default="pendentes",
                                      key="t_filtro") or "pendentes"
    with c2:
        categorias = repositorio.categorias_tarefas()
        categoria = st.selectbox("Categoria", ["Todas"] + categorias, key="t_categoria")

    tarefas = repositorio.listar_tarefas(filtro, None if categoria == "Todas" else categoria)
    tarefas = [t for t in tarefas if t["id"] != foco]  # o item aberto já aparece no topo
    if not tarefas:
        dicas = {
            "pendentes": "Use “Nova tarefa” acima para cadastrar a primeira.",
            "atrasadas": "Ótimo! Nenhuma tarefa passou do prazo.",
            "hoje": "Nenhuma tarefa tem prazo para hoje.",
            "concluidas": "Quando concluir uma tarefa, ela aparece aqui.",
            "todas": "Use “Nova tarefa” acima para cadastrar a primeira.",
        }
        ui.vazio("Nenhuma tarefa neste filtro.", dicas[filtro])
        return
    st.caption(f"{len(tarefas)} tarefa(s) · ordenadas por prazo e prioridade "
               f"({', '.join(planejador.NOME_PRIORIDADE.values())})")
    for t in tarefas:
        _cartao(t)
