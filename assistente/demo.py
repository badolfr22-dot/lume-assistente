"""Dados de demonstração.

Só são criados quando o usuário clica no botão. Todos ficam marcados com
`exemplo = 1` e com o prefixo "[Exemplo]" no título, e podem ser removidos
de uma vez sem afetar os dados reais.
"""

from __future__ import annotations

from datetime import date, timedelta

from assistente import db, repositorio
from assistente.tempo import hoje as _hoje

PREFIXO = "[Exemplo] "
TABELAS = ("tarefas", "metas", "compromissos", "anotacoes")


def carregar(hoje: date | None = None) -> int:
    if contar() > 0:
        return 0
    d = hoje or _hoje()
    criados = [
        repositorio.criar_tarefa(PREFIXO + "Revisar o orçamento do mês", prioridade="alta",
                                 prazo=d - timedelta(days=1), categoria="Finanças", duracao_min=45, exemplo=True),
        repositorio.criar_tarefa(PREFIXO + "Responder e-mails pendentes", prioridade="media", prazo=d,
                                 categoria="Trabalho", duracao_min=20, exemplo=True),
        repositorio.criar_tarefa(PREFIXO + "Caminhada de 30 minutos", prioridade="baixa", prazo=d,
                                 categoria="Saúde", duracao_min=30, exemplo=True),
        repositorio.criar_tarefa(PREFIXO + "Organizar a mesa de trabalho", prioridade="baixa",
                                 categoria="Casa", duracao_min=15, exemplo=True),
        repositorio.criar_meta(PREFIXO + "Ler 2 livros", descricao="Meta de demonstração",
                               prazo=d + timedelta(days=10), progresso=30, exemplo=True),
        repositorio.criar_compromisso(PREFIXO + "Reunião de alinhamento", d, "10:00", "11:00",
                                      local="Online", exemplo=True),
        repositorio.criar_anotacao(PREFIXO + "Ideias para a semana", "Esta é uma anotação de demonstração.",
                                   "exemplo", exemplo=True),
    ]
    return len(criados)


def contar() -> int:
    return sum(int(db.consultar_um(f"SELECT COUNT(*) AS n FROM {t} WHERE usuario_id = ? AND exemplo = 1",
                                   (db.usuario_atual(),))["n"]) for t in TABELAS)


def remover() -> int:
    """Remove os exemplos e também os avisos que foram gerados a partir deles."""
    total = 0
    uid = db.usuario_atual()
    with db.conectar() as con:
        for linha in con.execute("SELECT id FROM tarefas WHERE usuario_id = ? AND exemplo = 1", (uid,)).fetchall():
            con.execute("DELETE FROM notificacoes WHERE usuario_id = ? AND referencia LIKE ?",
                        (uid, f"prazo:{int(linha['id'])}:%"))
        for linha in con.execute("SELECT id FROM compromissos WHERE usuario_id = ? AND exemplo = 1",
                                 (uid,)).fetchall():
            con.execute("DELETE FROM notificacoes WHERE usuario_id = ? AND referencia LIKE ?",
                        (uid, f"compromisso:{int(linha['id'])}:%"))
        for tabela in TABELAS:  # nomes fixos
            total += con.execute(f"DELETE FROM {tabela} WHERE usuario_id = ? AND exemplo = 1", (uid,)).rowcount
    return total
