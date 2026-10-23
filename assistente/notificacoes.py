"""Lembretes e notificações dentro do próprio aplicativo.

As notificações aparecem enquanto o app está aberto (não há envio para o
sistema operacional ou para o celular nesta versão). Cada aviso tem uma
`referencia` única, então o mesmo aviso nunca é criado duas vezes.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from assistente import configuracoes, db, repositorio
from assistente import validacao as v
from assistente.tempo import agora as _agora, agora_iso

ICONES = {"lembretes": "🔔", "prazos": "⏳", "compromissos": "📅", "automacoes": "⚙️"}


# --- Lembretes ---------------------------------------------------------------

def criar_lembrete(titulo: str, data: Any, hora: Any) -> int:
    titulo = v.texto_obrigatorio(titulo, "Lembrete")
    data_iso = v.data_iso(data, "Data", obrigatoria=True)
    hora_iso = v.hora_iso(hora, "Horário")
    data_hora = f"{data_iso} {hora_iso}:00"
    if db.consultar_um("SELECT id FROM lembretes WHERE usuario_id = ? AND lower(titulo) = lower(?) AND data_hora = ?",
                       (db.usuario_atual(), titulo, data_hora)):
        raise v.ErroValidacao("Já existe um lembrete igual nesse horário.")
    return db.inserir("INSERT INTO lembretes (usuario_id, titulo, data_hora, criado_em) VALUES (?, ?, ?, ?)",
                      (db.usuario_atual(), titulo, data_hora, agora_iso()))


def listar_lembretes() -> list[dict[str, Any]]:
    return db.consultar("SELECT * FROM lembretes WHERE usuario_id = ? ORDER BY disparado, data_hora",
                        (db.usuario_atual(),))


def excluir_lembrete(id_: int) -> bool:
    return db.executar("DELETE FROM lembretes WHERE id = ? AND usuario_id = ?", (int(id_), db.usuario_atual())) > 0


# --- Notificações --------------------------------------------------------------

def registrar(tipo: str, titulo: str, mensagem: str, referencia: str) -> bool:
    """Cria a notificação se a referência ainda não existir. Devolve True se criou."""
    with db.conectar() as con:
        cursor = con.execute(
            "INSERT INTO notificacoes (usuario_id, tipo, titulo, mensagem, referencia, criada_em) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
            (db.usuario_atual(), tipo, titulo, mensagem, referencia, agora_iso()),
        )
        return cursor.rowcount > 0


def gerar_avisos(agora: datetime | None = None, config: dict | None = None) -> int:
    """Verifica lembretes, prazos e compromissos e cria os avisos novos."""
    agora = agora or _agora()
    config = config or configuracoes.obter_todas()
    tipos = set(config.get("notificacoes_tipos", []))
    criadas = 0

    if "lembretes" in tipos:
        vencidos = db.consultar("SELECT * FROM lembretes WHERE usuario_id = ? AND disparado = 0 AND data_hora <= ?",
                                (db.usuario_atual(), agora.isoformat(sep=" ")))
        for lembrete in vencidos:
            if registrar("lembretes", lembrete["titulo"], f"Lembrete agendado para {lembrete['data_hora'][:16]}.",
                         f"lembrete:{lembrete['id']}"):
                criadas += 1
            db.executar("UPDATE lembretes SET disparado = 1 WHERE id = ? AND usuario_id = ?",
                        (lembrete["id"], db.usuario_atual()))

    if "prazos" in tipos:
        dias = int(config.get("notificacoes_antecedencia_dias", 1))
        limite = (agora.date() + timedelta(days=dias)).isoformat()
        for t in repositorio.listar_tarefas("pendentes", hoje=agora.date()):
            if t["prazo"] and t["prazo"] <= limite:
                atrasada = t["prazo"] < agora.date().isoformat()
                texto = "está atrasada" if atrasada else ("vence hoje" if t["prazo"] == agora.date().isoformat()
                                                          else "vence em breve")
                if registrar("prazos", t["titulo"], f"A tarefa {texto} (prazo {t['prazo']}).",
                             f"prazo:{t['id']}:{t['prazo']}:{'atrasada' if atrasada else 'proxima'}"):
                    criadas += 1

    if "compromissos" in tipos:
        janela = int(config.get("notificacoes_compromisso_min", 30))
        for c in repositorio.compromissos_do_dia(agora.date()):
            inicio = datetime.fromisoformat(f"{c['data']} {c['hora_inicio']}:00")
            if agora <= inicio <= agora + timedelta(minutes=janela):
                if registrar("compromissos", c["titulo"], f"Começa às {c['hora_inicio']}.",
                             f"compromisso:{c['id']}:{c['data']}:{c['hora_inicio']}"):
                    criadas += 1
    return criadas


def listar(filtro: str = "nao_lidas") -> list[dict[str, Any]]:
    consultas = {
        "nao_lidas": "AND lida = 0 ORDER BY criada_em DESC, id DESC",
        "lidas": "AND lida = 1 ORDER BY lida_em DESC, id DESC LIMIT 200",
        "todas": "ORDER BY criada_em DESC, id DESC LIMIT 300",
    }
    if filtro not in consultas:
        raise v.ErroValidacao("Filtro de notificações inválido.")
    return db.consultar(f"SELECT * FROM notificacoes WHERE usuario_id = ? {consultas[filtro]}", (db.usuario_atual(),))


def contar_nao_lidas() -> int:
    return int(db.consultar_um("SELECT COUNT(*) AS n FROM notificacoes WHERE usuario_id = ? AND lida = 0",
                               (db.usuario_atual(),))["n"])


def marcar_lida(id_: int) -> bool:
    return db.executar("UPDATE notificacoes SET lida = 1, lida_em = ? WHERE id = ? AND usuario_id = ? AND lida = 0",
                       (agora_iso(), int(id_), db.usuario_atual())) > 0


def marcar_todas_lidas() -> int:
    return db.executar("UPDATE notificacoes SET lida = 1, lida_em = ? WHERE usuario_id = ? AND lida = 0",
                       (agora_iso(), db.usuario_atual()))
