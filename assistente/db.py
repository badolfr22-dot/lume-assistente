"""Acesso centralizado ao banco de dados (SQLite local ou PostgreSQL online).

- Todas as consultas usam parâmetros `?` (convertidos para `%s` no PostgreSQL),
  nunca concatenação de texto com dados do usuário.
- As linhas voltam sempre como dicionários.
- Cada registro pertence a um usuário (`usuario_id`). O usuário da sessão atual
  é guardado num ContextVar: cada sessão do Streamlit roda na sua própria thread.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from assistente import config

log = logging.getLogger(__name__)

VERSAO_ESQUEMA = 2
USUARIO_LOCAL = 1  # dono dos dados quando o app roda sem contas (uso pessoal)

# Ordem importa: tabelas referenciadas vêm antes.
TABELAS_DO_USUARIO = ("tarefas", "metas", "compromissos", "anotacoes", "configuracoes", "preferencias",
                      "plano_dia", "lembretes", "notificacoes", "automacoes", "automacoes_historico")


def _ddl(id_coluna: str) -> list[str]:
    """Comandos de criação. `id_coluna` muda entre SQLite e PostgreSQL."""
    dono = "usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE"
    return [
        "CREATE TABLE IF NOT EXISTS schema_versao (versao INTEGER NOT NULL)",
        f"""CREATE TABLE IF NOT EXISTS usuarios (
            id {id_coluna},
            email TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL,
            senha_hash TEXT NOT NULL DEFAULT '',
            criado_em TEXT NOT NULL,
            ultimo_login TEXT,
            falhas INTEGER NOT NULL DEFAULT 0,
            bloqueado_ate TEXT
        )""",
        f"""CREATE TABLE IF NOT EXISTS tarefas (
            id {id_coluna},
            {dono},
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL DEFAULT '',
            prioridade TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('alta','media','baixa')),
            prazo TEXT,
            categoria TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente','em_andamento','concluida')),
            duracao_min INTEGER NOT NULL DEFAULT 30 CHECK (duracao_min BETWEEN 5 AND 720),
            exemplo INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL,
            concluida_em TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_tarefas_usuario_status_prazo ON tarefas (usuario_id, status, prazo)",
        f"""CREATE TABLE IF NOT EXISTS metas (
            id {id_coluna},
            {dono},
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL DEFAULT '',
            prazo TEXT,
            progresso INTEGER NOT NULL DEFAULT 0 CHECK (progresso BETWEEN 0 AND 100),
            recorrencia TEXT NOT NULL DEFAULT 'nenhuma' CHECK (recorrencia IN ('nenhuma','semanal','mensal')),
            exemplo INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_metas_usuario ON metas (usuario_id)",
        f"""CREATE TABLE IF NOT EXISTS compromissos (
            id {id_coluna},
            {dono},
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL DEFAULT '',
            data TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            local TEXT NOT NULL DEFAULT '',
            exemplo INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_compromissos_usuario_data ON compromissos (usuario_id, data, hora_inicio)",
        f"""CREATE TABLE IF NOT EXISTS anotacoes (
            id {id_coluna},
            {dono},
            titulo TEXT NOT NULL,
            conteudo TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '',
            exemplo INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_anotacoes_usuario ON anotacoes (usuario_id)",
        f"""CREATE TABLE IF NOT EXISTS configuracoes (
            {dono},
            chave TEXT NOT NULL,
            valor TEXT NOT NULL,
            atualizado_em TEXT NOT NULL,
            PRIMARY KEY (usuario_id, chave)
        )""",
        f"""CREATE TABLE IF NOT EXISTS preferencias (
            id {id_coluna},
            {dono},
            categoria TEXT NOT NULL,
            chave TEXT NOT NULL,
            valor TEXT NOT NULL,
            criado_em TEXT NOT NULL,
            atualizado_em TEXT NOT NULL,
            UNIQUE (usuario_id, categoria, chave)
        )""",
        f"""CREATE TABLE IF NOT EXISTS plano_dia (
            {dono},
            data TEXT NOT NULL,
            tarefa_id INTEGER NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
            posicao INTEGER NOT NULL,
            PRIMARY KEY (usuario_id, data, tarefa_id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS lembretes (
            id {id_coluna},
            {dono},
            titulo TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            criado_em TEXT NOT NULL,
            disparado INTEGER NOT NULL DEFAULT 0
        )""",
        f"""CREATE TABLE IF NOT EXISTS notificacoes (
            id {id_coluna},
            {dono},
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL DEFAULT '',
            referencia TEXT NOT NULL,
            criada_em TEXT NOT NULL,
            lida INTEGER NOT NULL DEFAULT 0,
            lida_em TEXT,
            UNIQUE (usuario_id, referencia)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario_lida ON notificacoes (usuario_id, lida, criada_em)",
        f"""CREATE TABLE IF NOT EXISTS automacoes (
            id {id_coluna},
            {dono},
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            parametros TEXT NOT NULL DEFAULT '{{}}',
            ativa INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL,
            ultima_execucao TEXT,
            UNIQUE (usuario_id, nome)
        )""",
        f"""CREATE TABLE IF NOT EXISTS automacoes_historico (
            id {id_coluna},
            {dono},
            automacao_id INTEGER REFERENCES automacoes(id) ON DELETE SET NULL,
            nome_automacao TEXT NOT NULL,
            executado_em TEXT NOT NULL,
            situacao TEXT NOT NULL CHECK (situacao IN ('ok','sem_acao','erro')),
            mensagem TEXT NOT NULL DEFAULT ''
        )""",
    ]


# Colunas da versão 1 (antes das contas), usadas para migrar bancos antigos.
_COLUNAS_V1 = {
    "tarefas": "id, titulo, descricao, prioridade, prazo, categoria, status, duracao_min, exemplo, criado_em, "
               "atualizado_em, concluida_em",
    "metas": "id, titulo, descricao, prazo, progresso, recorrencia, exemplo, criado_em, atualizado_em",
    "compromissos": "id, titulo, descricao, data, hora_inicio, hora_fim, local, exemplo, criado_em, atualizado_em",
    "anotacoes": "id, titulo, conteudo, tags, exemplo, criado_em, atualizado_em",
    "configuracoes": "chave, valor, atualizado_em",
    "preferencias": "id, categoria, chave, valor, criado_em, atualizado_em",
    "plano_dia": "data, tarefa_id, posicao",
    "lembretes": "id, titulo, data_hora, criado_em, disparado",
    "notificacoes": "id, tipo, titulo, mensagem, referencia, criada_em, lida, lida_em",
    "automacoes": "id, nome, tipo, parametros, ativa, criado_em, ultima_execucao",
    "automacoes_historico": "id, automacao_id, nome_automacao, executado_em, situacao, mensagem",
}
_INDICES_V1 = ("idx_tarefas_status_prazo", "idx_compromissos_data", "idx_notificacoes_lida")


class ErroBanco(Exception):
    """Erro de banco com mensagem segura para mostrar ao usuário."""


class ErroAcesso(Exception):
    """Operação sem usuário identificado (nunca deve chegar à interface)."""


# ---------------------------------------------------------------------------
# Usuário da sessão
# ---------------------------------------------------------------------------

_usuario: ContextVar[int | None] = ContextVar("usuario_atual", default=None)


def definir_usuario(id_: int | None) -> None:
    _usuario.set(int(id_) if id_ is not None else None)


def usuario_atual() -> int:
    """Dono dos dados desta operação. Sem contas, é sempre o usuário local."""
    id_ = _usuario.get()
    if id_ is not None:
        return id_
    if not config.configuracao().multiusuario:
        return USUARIO_LOCAL
    raise ErroAcesso("Nenhum usuário autenticado nesta sessão.")


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

def _erros_driver() -> tuple[tuple[type, ...], tuple[type, ...]]:
    """(erros de integridade, erros gerais) dos drivers disponíveis."""
    integridade: list[type] = [sqlite3.IntegrityError]
    gerais: list[type] = [sqlite3.Error]
    try:
        import psycopg
        integridade.append(psycopg.IntegrityError)
        gerais.append(psycopg.Error)
    except ImportError:  # psycopg só é necessário com PostgreSQL
        pass
    return tuple(integridade), tuple(gerais)


class Conexao:
    """Embrulha a conexão do driver para que o resto do app não dependa dele."""

    def __init__(self, bruta: Any, postgres: bool) -> None:
        self.bruta = bruta
        self.postgres = postgres

    def _sql(self, sql: str) -> str:
        return sql.replace("%", "%%").replace("?", "%s") if self.postgres else sql

    def execute(self, sql: str, parametros: tuple[Any, ...] | list[Any] = ()) -> Any:
        if self.postgres:
            cursor = self.bruta.cursor()
            cursor.execute(self._sql(sql), tuple(parametros))
            return cursor
        return self.bruta.execute(sql, tuple(parametros))

    def executemany(self, sql: str, linhas: list[tuple[Any, ...]]) -> None:
        if self.postgres:
            with self.bruta.cursor() as cursor:
                cursor.executemany(self._sql(sql), linhas)
        else:
            self.bruta.executemany(sql, linhas)

    def commit(self) -> None:
        self.bruta.commit()

    def rollback(self) -> None:
        self.bruta.rollback()

    def close(self) -> None:
        self.bruta.close()


def _linha_como_dict(cursor: sqlite3.Cursor, linha: tuple) -> dict[str, Any]:
    return {coluna[0]: valor for coluna, valor in zip(cursor.description, linha)}


_lock = threading.Lock()
_caminho_override: Path | None = None
_url_override: str | None = None
_inicializados: set[str] = set()
# Uma conexão reaproveitada por thread (cada sessão do Streamlit roda numa thread).
# Abrir conexão a cada consulta custava ~3 ms; veja docs/REVISOES.md.
_local = threading.local()


def definir_caminho_banco(caminho: Path | str | None) -> None:
    """Troca o arquivo SQLite (usado nos testes). `None` volta ao padrão."""
    global _caminho_override
    fechar_conexao()
    _caminho_override = Path(caminho) if caminho else None


def definir_url_banco(url: str | None) -> None:
    """Força um PostgreSQL (usado nos testes). `None` volta ao padrão."""
    global _url_override
    fechar_conexao()
    _url_override = url or None


def caminho_banco() -> Path:
    if _caminho_override is not None:
        return _caminho_override
    return config.configuracao().caminho_banco


def url_banco() -> str:
    if _url_override is not None:
        return _url_override
    if _caminho_override is not None:
        return ""
    return config.configuracao().url_banco


def usando_postgres() -> bool:
    return url_banco().startswith(("postgresql://", "postgres://"))


def _destino() -> str:
    return url_banco() if usando_postgres() else str(caminho_banco())


def fechar_conexao() -> None:
    """Fecha a conexão reaproveitada desta thread, se houver."""
    con = getattr(_local, "con", None)
    if con is not None:
        try:
            con.close()
        except Exception:  # noqa: BLE001 - conexão já pode estar quebrada
            pass
    _local.con = None
    _local.destino = None


def _abrir(destino: str) -> Conexao:
    if usando_postgres():
        import psycopg
        from psycopg.rows import dict_row

        return Conexao(psycopg.connect(destino, row_factory=dict_row, connect_timeout=10), postgres=True)
    caminho = Path(destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    bruta = sqlite3.connect(caminho, timeout=10)
    bruta.row_factory = _linha_como_dict
    bruta.execute("PRAGMA foreign_keys = ON")
    return Conexao(bruta, postgres=False)


# ---------------------------------------------------------------------------
# Criação e migração do esquema
# ---------------------------------------------------------------------------

def _colunas(con: Conexao, tabela: str) -> set[str]:
    return {linha["name"] for linha in con.execute(f"PRAGMA table_info({tabela})").fetchall()}


def _copia_de_seguranca_sqlite(caminho: Path) -> Path:
    pasta = caminho.parent / "backups-migracao"  # junto do banco, fora do que é publicado
    pasta.mkdir(exist_ok=True)
    destino = pasta / f"antes-da-migracao-v2-{datetime.now():%Y%m%d-%H%M%S}.db"
    with sqlite3.connect(caminho) as fonte, sqlite3.connect(destino) as alvo:
        fonte.backup(alvo)
    return destino


def _migrar_sqlite_v1(con: Conexao, caminho: Path) -> None:
    """Versão 1 (sem contas) -> versão 2. Faz backup antes e não perde nenhum registro."""
    copia = _copia_de_seguranca_sqlite(caminho)
    log.warning("Migrando o banco para a versão 2 (contas). Cópia de segurança: %s", copia.name)
    bruta = con.bruta
    bruta.execute("PRAGMA foreign_keys = OFF")
    try:
        bruta.execute("BEGIN")
        for indice in _INDICES_V1:
            bruta.execute(f"DROP INDEX IF EXISTS {indice}")
        for tabela in _COLUNAS_V1:
            bruta.execute(f"ALTER TABLE {tabela} RENAME TO {tabela}__v1")
        for comando in _ddl("INTEGER PRIMARY KEY AUTOINCREMENT"):
            bruta.execute(comando)
        _garantir_usuario_local(con)
        for tabela, colunas in _COLUNAS_V1.items():
            bruta.execute(f"INSERT INTO {tabela} ({colunas}, usuario_id) SELECT {colunas}, ? FROM {tabela}__v1",
                          (USUARIO_LOCAL,))
        for tabela in reversed(list(_COLUNAS_V1)):
            bruta.execute(f"DROP TABLE {tabela}__v1")
        bruta.execute("UPDATE schema_versao SET versao = ?", (VERSAO_ESQUEMA,))
        bruta.execute("COMMIT")
    except Exception:
        bruta.execute("ROLLBACK")
        raise
    finally:
        bruta.execute("PRAGMA foreign_keys = ON")


def _garantir_usuario_local(con: Conexao) -> None:
    con.execute(
        "INSERT INTO usuarios (id, email, nome, senha_hash, criado_em) VALUES (?, ?, ?, '', ?) "
        "ON CONFLICT DO NOTHING",
        (USUARIO_LOCAL, "local@localhost", "Uso local", datetime.now().isoformat(sep=" ", timespec="seconds")),
    )
    if con.postgres:  # inserir id fixo não avança a sequência do PostgreSQL
        con.execute("SELECT setval(pg_get_serial_sequence('usuarios', 'id'), "
                    "GREATEST((SELECT MAX(id) FROM usuarios), 1))")


def inicializar() -> None:
    """Cria (ou migra) as tabelas. Nunca apaga dados."""
    destino = _destino()
    if destino in _inicializados and (usando_postgres() or Path(destino).exists()):
        return
    with _lock:
        con = _abrir(destino)
        try:
            if con.postgres:
                for comando in _ddl("SERIAL PRIMARY KEY"):
                    con.execute(comando)
            else:
                con.execute("PRAGMA journal_mode = WAL")
                tabelas = {linha["name"] for linha in
                           con.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
                if "tarefas" in tabelas and "usuario_id" not in _colunas(con, "tarefas"):
                    con.commit()
                    _migrar_sqlite_v1(con, Path(destino))
                for comando in _ddl("INTEGER PRIMARY KEY AUTOINCREMENT"):
                    con.execute(comando)
            _garantir_usuario_local(con)
            if con.execute("SELECT versao FROM schema_versao").fetchone() is None:
                con.execute("INSERT INTO schema_versao (versao) VALUES (?)", (VERSAO_ESQUEMA,))
            con.commit()
        finally:
            con.close()
        _inicializados.add(destino)


# ---------------------------------------------------------------------------
# Operações
# ---------------------------------------------------------------------------

@contextmanager
def conectar() -> Iterator[Conexao]:
    """Conexão da thread: commit no sucesso, rollback em caso de erro."""
    erros_integridade, erros_gerais = _erros_driver()
    destino = _destino()
    try:
        inicializar()
    except erros_gerais as exc:
        log.error("Falha ao preparar o banco: %s", type(exc).__name__)
        raise ErroBanco("Não foi possível abrir o banco de dados.") from exc
    con = getattr(_local, "con", None)
    if con is None or getattr(_local, "destino", None) != destino:
        fechar_conexao()
        try:
            con = _abrir(destino)
        except erros_gerais as exc:
            log.error("Falha ao abrir o banco: %s", type(exc).__name__)
            raise ErroBanco("Não foi possível abrir o banco de dados.") from exc
        _local.con, _local.destino = con, destino
    try:
        yield con
        con.commit()
    except erros_integridade as exc:
        con.rollback()
        log.warning("Violação de integridade: %s", type(exc).__name__)
        raise ErroBanco("Os dados não puderam ser salvos porque violam uma regra do banco.") from exc
    except erros_gerais as exc:
        # Falha temporária (ex.: banco bloqueado ou conexão perdida): descarta a conexão
        # para a próxima tentativa abrir outra.
        try:
            con.rollback()
        except Exception:  # noqa: BLE001
            pass
        fechar_conexao()
        log.error("Erro no banco: %s", type(exc).__name__)
        raise ErroBanco("O banco de dados está indisponível no momento. Tente novamente.") from exc
    except Exception:
        con.rollback()
        raise


def consultar(sql: str, parametros: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with conectar() as con:
        return list(con.execute(sql, parametros).fetchall())


def consultar_um(sql: str, parametros: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with conectar() as con:
        return con.execute(sql, parametros).fetchone()


def executar(sql: str, parametros: tuple[Any, ...] = ()) -> int:
    """Executa um comando e devolve o número de linhas afetadas."""
    with conectar() as con:
        return con.execute(sql, parametros).rowcount


def inserir(sql: str, parametros: tuple[Any, ...] = ()) -> int:
    """Executa um INSERT numa tabela com coluna `id` e devolve o id criado."""
    with conectar() as con:
        return int(con.execute(f"{sql} RETURNING id", parametros).fetchone()["id"])


def escapar_like(texto: str) -> str:
    """Escapa curingas do LIKE para que o texto do usuário seja literal."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def contem(coluna: str) -> str:
    """Trecho SQL de busca sem diferenciar maiúsculas (igual no SQLite e no PostgreSQL)."""
    return f"lower({coluna}) LIKE lower(?) ESCAPE '\\'"
