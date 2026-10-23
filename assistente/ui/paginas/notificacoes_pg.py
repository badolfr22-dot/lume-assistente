"""Notificações dentro do app e lembretes."""

from __future__ import annotations

from datetime import time, timedelta

import streamlit as st

from assistente import notificacoes
from assistente.tempo import agora, hoje
from assistente.ui import componentes as ui


def _lista(itens: list[dict], permitir_marcar: bool) -> None:
    for n in itens:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
            with c1:
                icone = notificacoes.ICONES.get(n["tipo"], "🔔")
                quando = f"{ui.fmt_data(n['criada_em'])} {ui.fmt_hora(n['criada_em'][11:16])}"
                ui.titulo_item(f"{icone} {n['titulo']}", f"{quando} · {n['mensagem']}")
            if permitir_marcar and c2.button("Marcar como lida", key=f"nt_l_{n['id']}", icon=":material/done:",
                                             width="stretch"):
                notificacoes.marcar_lida(n["id"])
                st.rerun()


def render() -> None:
    ui.cabecalho("Notificações", "Avisos e lembretes dentro do aplicativo.", "🔔")
    st.caption("Os avisos aparecem aqui enquanto o app está aberto no navegador. Avisos no sistema do computador "
               "ou do celular (push) não fazem parte desta versão: exigiriam um serviço extra, como um app instalado "
               "ou um servidor de notificações.")

    if st.button("Verificar novos avisos agora", icon=":material/refresh:"):
        criadas = notificacoes.gerar_avisos(config=ui.config())
        ui.avisar(f"{criadas} aviso(s) novo(s)." if criadas else "Nenhum aviso novo.", "info")
        st.rerun()

    nao_lidas = notificacoes.listar("nao_lidas")
    aba1, aba2, aba3 = st.tabs([f"Não lidas ({len(nao_lidas)})", "Anteriores", "Lembretes"])
    with aba1:
        if not nao_lidas:
            ui.vazio("Tudo em dia!", "Nenhuma notificação pendente.")
        else:
            if st.button("Marcar todas como lidas", icon=":material/done_all:"):
                total = notificacoes.marcar_todas_lidas()
                ui.avisar(f"{total} notificação(ões) marcada(s) como lida(s).")
                st.rerun()
            _lista(nao_lidas, True)
    with aba2:
        lidas = notificacoes.listar("lidas")
        if not lidas:
            ui.vazio("Nenhuma notificação lida ainda.", "As notificações marcadas como lidas ficam guardadas aqui.")
        _lista(lidas, False)
    with aba3:
        with st.form("form_lembrete", clear_on_submit=True):
            titulo = st.text_input("Lembrete *", max_chars=120, placeholder="Ex.: Tomar o remédio")
            c1, c2 = st.columns(2)
            proxima_hora = (agora() + timedelta(hours=1)).replace(minute=0)
            data = c1.date_input("Data *", value=hoje(), format=ui.formato_widget_data())
            hora = c2.time_input("Horário *", value=time(proxima_hora.hour, 0), step=timedelta(minutes=5))
            if st.form_submit_button("Criar lembrete", type="primary", icon=":material/alarm_add:"):
                ui.executar_acao(lambda: notificacoes.criar_lembrete(titulo, data, hora), "Lembrete criado!")
        lembretes = notificacoes.listar_lembretes()
        if not lembretes:
            ui.vazio("Nenhum lembrete.", "Crie um lembrete acima; ele vira um aviso quando chegar a hora.")
        for lem in lembretes:
            with st.container(border=True):
                c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
                with c1:
                    situacao = ("Disparado", "concluida") if lem["disparado"] else ("Agendado", "neutra")
                    ui.titulo_item(lem["titulo"], f"{ui.fmt_data(lem['data_hora'])} {ui.fmt_hora(lem['data_hora'][11:16])}",
                                   chips_html=ui.chips(situacao))
                if c2.button("Excluir", key=f"lem_del_{lem['id']}", icon=":material/delete:", width="stretch"):
                    ui.executar_acao(lambda i=lem["id"]: notificacoes.excluir_lembrete(i), "Lembrete excluído.")
