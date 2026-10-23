"""Planejador diário."""

from __future__ import annotations

import streamlit as st

from assistente import planejador, repositorio
from assistente.tempo import agora, data_por_extenso, hoje
from assistente.ui import componentes as ui


def render() -> None:
    ui.cabecalho("Planejador do dia", "Uma sequência realista para o seu dia, com o motivo de cada sugestão.", "🗓️")

    c1, c2 = st.columns([1.3, 2], vertical_alignment="bottom")
    dia = c1.date_input("Dia", value=hoje(), format=ui.formato_widget_data(), key="pl_dia")
    inicio, fim = planejador.horario_trabalho()
    c2.caption(f"Horário considerado: {inicio} às {fim}. Para mudar, salve “inicio do dia” e “fim do dia” "
               "na categoria Horários em Preferências e memória.")

    momento = agora()
    usar_hora_atual = True
    if dia == momento.date():
        usar_hora_atual = st.toggle("Começar a partir do horário atual", value=True, key="pl_agora",
                                    help="Desligue para ver o plano do dia inteiro, desde o início.")
    plano = planejador.plano_do_dia(dia, momento if usar_hora_atual else None)
    if usar_hora_atual and dia == momento.date() and momento.strftime("%H:%M") >= fim:
        st.info(f"Já passou do fim do seu dia ({fim}), por isso as tarefas não cabem mais hoje. "
                "Desligue a opção acima para ver o plano completo ou escolha o dia de amanhã.", icon="🌙")
    feitas, total = planejador.progresso_do_dia(dia)
    st.markdown(f"**{data_por_extenso(dia).capitalize()}**")
    ui.barra("Progresso do dia", round(100 * feitas / total) if total else 0, "--lume-sucesso")
    st.caption(f"{feitas} tarefa(s) concluída(s) neste dia de {total} (concluídas + pendentes com prazo até este dia).")

    for a, b in plano.conflitos:
        st.warning(f"Conflito de horário: “{a['titulo']}” ({a['hora_inicio']}–{a['hora_fim']}) e “{b['titulo']}” "
                   f"({b['hora_inicio']}–{b['hora_fim']}). Ajuste na Agenda — o planejador não altera compromissos.",
                   icon="⚠️")
    if plano.atrasadas:
        st.error(f"{len(plano.atrasadas)} tarefa(s) atrasada(s): "
                 + ", ".join(t["titulo"] for t in plano.atrasadas[:5]) + ". Elas foram colocadas primeiro.", icon="⏰")

    if not plano.itens and not plano.nao_couberam:
        ui.vazio("Nada para planejar neste dia.",
                 "Cadastre tarefas (com ou sem prazo) e compromissos para montar o plano.")
        return

    st.markdown("#### Sequência sugerida")
    ordem = plano.ordem_tarefas
    for item in plano.itens:
        with st.container(border=True):
            col_h, col_t, col_b = st.columns([1.1, 4, 1.6], vertical_alignment="center")
            col_h.markdown(f'<span class="lume-hora">{ui.e(item.inicio)}–{ui.e(item.fim)}</span>',
                           unsafe_allow_html=True)
            with col_t:
                if item.tipo == "compromisso":
                    ui.titulo_item(f"📅 {item.titulo}", chips_html=ui.chips(("Compromisso", "neutra")))
                else:
                    ui.titulo_item(item.titulo, chips_html=ui.chips(("Atrasada", "atrasada")) if item.atrasada else "")
                st.caption(item.explicacao)
            if item.tipo == "tarefa":
                with col_b:
                    b1, b2 = st.columns(2)
                    pos = ordem.index(item.id)
                    if b1.button("Subir", key=f"pl_up_{item.id}", icon=":material/arrow_upward:", disabled=pos == 0,
                                 help="Subir na ordem", width="stretch"):
                        planejador.mover(dia, ordem, item.id, -1)
                        st.rerun()
                    if b2.button("Descer", key=f"pl_dn_{item.id}", icon=":material/arrow_downward:",
                                 disabled=pos == len(ordem) - 1, help="Descer na ordem", width="stretch"):
                        planejador.mover(dia, ordem, item.id, +1)
                        st.rerun()
                    with st.popover("Duração", icon=":material/timer:", width="stretch"):
                        tarefa = repositorio.obter_tarefa(item.id)
                        nova = st.number_input("Duração estimada (min)", 5, 720, int(tarefa["duracao_min"]), 5,
                                               key=f"pl_dur_{item.id}")
                        if st.button("Salvar duração", key=f"pl_dsv_{item.id}", type="primary"):
                            ui.executar_acao(lambda: repositorio.atualizar_tarefa(item.id, duracao_min=nova),
                                             "Duração atualizada!")

    if plano.nao_couberam:
        st.markdown("#### Não couberam neste dia")
        for t in plano.nao_couberam:
            ui.titulo_item(t["titulo"], f"{t['duracao_min']} min · prazo {ui.fmt_data(t['prazo'])}")
        st.caption("Reduza a duração estimada, mude a ordem ou amplie o horário do dia nas Preferências.")

    if planejador.ordem_manual(dia):
        if st.button("Voltar à ordem automática", icon=":material/restart_alt:"):
            planejador.limpar_ordem(dia)
            ui.avisar("Ordem automática restaurada.")
            st.rerun()
    st.caption("O planejador só sugere: ele não conclui tarefas nem altera compromissos.")
