"""Painel principal: resumo do dia, indicadores, tarefas, agenda, metas, anotações e sugestões."""

from __future__ import annotations

import streamlit as st

from assistente import planejador, repositorio, sugestoes
from assistente.tempo import agora, data_por_extenso, hoje
from assistente.ui import componentes as ui


def _saudacao() -> str:
    hora = agora().hour
    return "Bom dia" if hora < 12 else ("Boa tarde" if hora < 18 else "Boa noite")


def render() -> None:
    cfg = ui.config()
    dia = hoje()
    nome = cfg["nome_usuario"] or (st.session_state.get("_usuario") or {}).get("nome", "")
    ui.cabecalho(f"{_saudacao()}{', ' + nome if nome else ''}!",
                 f"Hoje é {data_por_extenso(dia)}. Aqui está o resumo do seu dia.", "✨")

    ind = repositorio.indicadores(dia)
    feitas_dia, total_dia = planejador.progresso_do_dia(dia)

    # 1. Resumo do dia (indicadores)
    ui.metricas([
        ("Pendentes", ind["tarefas_pendentes"], f"{ind['tarefas_hoje']} vencem hoje", "--lume-pri"),
        ("Concluídas hoje", ind["tarefas_concluidas_hoje"], f"{ind['tarefas_concluidas']} no total", "--lume-sucesso"),
        ("Atrasadas", ind["tarefas_atrasadas"], "precisam de atenção" if ind["tarefas_atrasadas"] else "nenhuma 🎉",
         "--lume-perigo"),
        ("Compromissos hoje", ind["compromissos_hoje"], "na agenda", "--lume-info"),
    ])

    # 6. Indicadores visuais de progresso
    with st.container(border=True):
        st.markdown("##### 📈 Progresso")
        c1, c2, c3 = st.columns(3)
        with c1:
            ui.barra("Tarefas do dia", round(100 * feitas_dia / total_dia) if total_dia else 0, "--lume-sucesso")
            st.caption(f"{feitas_dia} de {total_dia} (concluídas hoje + pendentes até hoje)")
        with c2:
            ui.barra("Todas as tarefas", ind["percentual_tarefas"])
            st.caption(f"{ind['tarefas_concluidas']} de {ind['tarefas_total']} concluídas")
        with c3:
            ui.barra("Média das metas", ind["metas_media"], "--lume-dest")
            st.caption(f"{ind['metas_concluidas']} de {ind['metas_total']} metas concluídas")

    esquerda, direita = st.columns([3, 2], gap="medium")

    with esquerda:
        # 2. Tarefas pendentes e concluídas
        with st.container(border=True):
            st.markdown("##### ✅ Tarefas")
            aba_p, aba_c = st.tabs(["Pendentes", "Concluídas"])
            with aba_p:
                pendentes = repositorio.listar_tarefas("pendentes", hoje=dia)
                if not pendentes:
                    ui.vazio("Nenhuma tarefa pendente.", "Cadastre uma tarefa na página Tarefas ou pela Conversa.")
                for t in pendentes[:6]:
                    col_t, col_b = st.columns([4, 1.4], vertical_alignment="center")
                    with col_t:
                        atrasada = repositorio.esta_atrasada(t, dia)
                        chips = ui.chips((planejador.NOME_PRIORIDADE[t["prioridade"]].capitalize(), t["prioridade"]),
                                         *([("Atrasada", "atrasada")] if atrasada else []))
                        ui.titulo_item(t["titulo"], f"Prazo: {ui.fmt_data(t['prazo'])}", chips_html=chips)
                    if col_b.button("Concluir", key=f"p_ok_{t['id']}", icon=":material/check:",
                                    help=f"Marcar “{t['titulo']}” como concluída"):
                        ui.executar_acao(lambda i=t["id"]: repositorio.concluir_tarefa(i), "Tarefa concluída!")
                if len(pendentes) > 6:
                    st.caption(f"…e mais {len(pendentes) - 6}.")
                if st.button("Ver todas as tarefas", key="p_ver_tarefas", type="tertiary", icon=":material/arrow_forward:"):
                    ui.ir_para("tarefas")
            with aba_c:
                concluidas = repositorio.listar_tarefas("concluidas", hoje=dia)
                if not concluidas:
                    ui.vazio("Nenhuma tarefa concluída ainda.", "Quando concluir uma tarefa, ela aparece aqui.")
                for t in sorted(concluidas, key=lambda x: x["concluida_em"] or "", reverse=True)[:6]:
                    ui.titulo_item(t["titulo"], f"Concluída em {ui.fmt_data(t['concluida_em'])}", feito=True)

        # 4. Agenda e compromissos
        with st.container(border=True):
            st.markdown("##### 📅 Agenda — próximos 7 dias")
            proximos = repositorio.proximos_compromissos(7, dia)
            if not proximos:
                ui.vazio("Nenhum compromisso nos próximos 7 dias.", "Cadastre compromissos na página Agenda.")
            for c in proximos[:6]:
                ui.titulo_item(c["titulo"], f"{ui.fmt_data(c['data'])} · {ui.fmt_hora(c['hora_inicio'])}–"
                               f"{ui.fmt_hora(c['hora_fim'])}" + (f" · {c['local']}" if c["local"] else ""))

    with direita:
        # 7. Sugestões inteligentes
        with st.container(border=True):
            st.markdown("##### 💡 Sugestões inteligentes")
            lista = sugestoes.gerar(dia, cfg)
            if not lista:
                ui.vazio("Sugestões desativadas.", "Ative em Configurações → Sugestões automáticas.")
            for s in lista:
                ui.sugestao(s.icone, s.titulo, s.motivo)
            st.caption("Geradas por regras locais a partir dos seus dados. Nada é alterado sem você pedir.")

        # 3. Metas pessoais
        with st.container(border=True):
            st.markdown("##### 🎯 Metas")
            metas = repositorio.listar_metas("ativas")
            if not metas:
                ui.vazio("Nenhuma meta ativa.", "Crie uma meta na página Metas.")
            for m in metas[:4]:
                ui.barra(m["titulo"], m["progresso"], "--lume-dest")

        # 5. Anotações rápidas
        with st.container(border=True):
            st.markdown("##### 📝 Anotações rápidas")
            with st.form("nota_rapida", clear_on_submit=True, border=False):
                titulo = st.text_input("Título da anotação", placeholder="Ex.: Ideia para o projeto",
                                       max_chars=120)
                conteudo = st.text_area("Texto (opcional)", height=80, max_chars=5000)
                if st.form_submit_button("Salvar anotação", icon=":material/save:"):
                    ui.executar_acao(lambda: repositorio.criar_anotacao(titulo, conteudo), "Anotação salva!")
            for n in repositorio.listar_anotacoes()[:3]:
                ui.titulo_item(n["titulo"], (n["conteudo"][:80] + "…") if len(n["conteudo"]) > 80 else n["conteudo"])
