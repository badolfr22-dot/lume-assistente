"""Memória controlada: preferências que o próprio usuário decide salvar.

- Nada é salvo automaticamente: só o que o usuário digitar e confirmar.
- Fica numa tabela separada das tarefas e compromissos.
- Recusa textos que pareçam senhas, tokens, chaves de API, CPF ou cartões.
"""

from __future__ import annotations

from typing import Any

from assistente import db
from assistente import validacao as v
from assistente.tempo import agora_iso

CATEGORIAS = {
    "horarios": "Horários preferidos",
    "categorias_favoritas": "Categorias favoritas de tarefas",
    "notificacoes": "Preferências de notificações",
    "metas_recorrentes": "Metas recorrentes",
    "painel": "Visualização do painel",
    "outros": "Outras informações úteis",
}

# Chaves com significado especial, usadas por outras partes do app.
CHAVE_INICIO_DIA = ("horarios", "inicio_do_dia")
CHAVE_FIM_DIA = ("horarios", "fim_do_dia")

MENSAGEM_SENSIVEL = (
    "Por segurança, a memória não guarda senhas, tokens, chaves de API, CPF, "
    "números de cartão ou textos parecidos com isso."
)


def _validar(categoria: str, chave: str, valor: str) -> tuple[str, str, str]:
    categoria = v.opcao(categoria, CATEGORIAS, "Categoria")
    chave = v.texto_obrigatorio(chave, "Nome da informação", v.LIMITE_CURTO)
    chave = "_".join(chave.lower().split())
    valor = v.texto_obrigatorio(valor, "Valor", 500)
    if v.parece_sensivel(chave, valor):
        raise v.ErroValidacao(MENSAGEM_SENSIVEL)
    if (categoria, chave) in (CHAVE_INICIO_DIA, CHAVE_FIM_DIA):
        valor = v.hora_iso(valor, "Horário")
    return categoria, chave, valor


def salvar(categoria: str, chave: str, valor: str) -> int:
    """Cria ou atualiza (mesma categoria + nome) uma preferência."""
    categoria, chave, valor = _validar(categoria, chave, valor)
    momento = agora_iso()
    uid = db.usuario_atual()
    with db.conectar() as con:
        linha = con.execute(
            "INSERT INTO preferencias (usuario_id, categoria, chave, valor, criado_em, atualizado_em) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(usuario_id, categoria, chave) DO UPDATE SET "
            "valor = excluded.valor, atualizado_em = excluded.atualizado_em RETURNING id",
            (uid, categoria, chave, valor, momento, momento),
        ).fetchone()
    return int(linha["id"])


def editar(id_: int, valor: str) -> bool:
    atual = obter(id_)
    if atual is None:
        raise v.ErroValidacao("Preferência não encontrada.")
    _, _, valor = _validar(atual["categoria"], atual["chave"], valor)
    return db.executar("UPDATE preferencias SET valor = ?, atualizado_em = ? WHERE id = ? AND usuario_id = ?",
                       (valor, agora_iso(), int(id_), db.usuario_atual())) > 0


def obter(id_: int) -> dict[str, Any] | None:
    return db.consultar_um("SELECT * FROM preferencias WHERE id = ? AND usuario_id = ?",
                           (int(id_), db.usuario_atual()))


def valor(categoria: str, chave: str, padrao: str | None = None) -> str | None:
    linha = db.consultar_um("SELECT valor FROM preferencias WHERE usuario_id = ? AND categoria = ? AND chave = ?",
                            (db.usuario_atual(), categoria, chave))
    return linha["valor"] if linha else padrao


def listar(categoria: str | None = None) -> list[dict[str, Any]]:
    if categoria:
        return db.consultar("SELECT * FROM preferencias WHERE usuario_id = ? AND categoria = ? ORDER BY chave",
                            (db.usuario_atual(), categoria))
    return db.consultar("SELECT * FROM preferencias WHERE usuario_id = ? ORDER BY categoria, chave",
                        (db.usuario_atual(),))


def excluir(id_: int) -> bool:
    return db.executar("DELETE FROM preferencias WHERE id = ? AND usuario_id = ?",
                       (int(id_), db.usuario_atual())) > 0


def limpar_tudo() -> int:
    return db.executar("DELETE FROM preferencias WHERE usuario_id = ?", (db.usuario_atual(),))


def categorias_favoritas() -> list[str]:
    return [p["valor"] for p in listar("categorias_favoritas")]
