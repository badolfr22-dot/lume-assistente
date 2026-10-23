"""Backup e restauração do banco SQLite.

Fazer backup (pode ser com o app aberto; usa a API de backup do SQLite):
    .venv\\Scripts\\python.exe scripts\\backup.py
    -> cria backups\\assistente-AAAAMMDD-HHMMSS.db

Restaurar (feche o app antes):
    .venv\\Scripts\\python.exe scripts\\backup.py --restaurar backups\\assistente-AAAAMMDD-HHMMSS.db
    -> o banco atual é guardado antes como backups\\antes-de-restaurar-AAAAMMDD-HHMMSS.db
    (nada é apagado: o banco anterior fica salvo)
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from assistente import db  # noqa: E402

PASTA_BACKUPS = RAIZ / "backups"


def copiar(origem: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(origem) as fonte, sqlite3.connect(destino) as alvo:
        fonte.backup(alvo)
    with sqlite3.connect(destino) as conferencia:
        if conferencia.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("A cópia não passou na verificação de integridade.")


def fazer_backup(destino_pasta: Path = PASTA_BACKUPS) -> Path:
    origem = db.caminho_banco()
    if not origem.exists():
        raise FileNotFoundError("Ainda não existe banco de dados para copiar.")
    destino = destino_pasta / f"assistente-{datetime.now():%Y%m%d-%H%M%S}.db"
    copiar(origem, destino)
    return destino


def restaurar(arquivo: Path, destino_pasta: Path = PASTA_BACKUPS) -> Path | None:
    if not arquivo.is_file():
        raise FileNotFoundError(f"Arquivo de backup não encontrado: {arquivo}")
    with sqlite3.connect(arquivo) as conferencia:
        tabelas = {linha[0] for linha in conferencia.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "tarefas" not in tabelas:
        raise ValueError("Este arquivo não parece ser um backup do assistente.")
    atual = db.caminho_banco()
    guardado = None
    if atual.exists():
        guardado = destino_pasta / f"antes-de-restaurar-{datetime.now():%Y%m%d-%H%M%S}.db"
        copiar(atual, guardado)
    db.fechar_conexao()
    copiar(arquivo, atual)
    return guardado


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup e restauração do banco do assistente.")
    parser.add_argument("--restaurar", type=Path, help="Arquivo .db de backup para restaurar")
    args = parser.parse_args()
    if db.usando_postgres():
        print("Com PostgreSQL, use o backup do provedor do banco (ex.: painel do Neon) e o 'Exportar meus dados'.")
        return 1
    try:
        if args.restaurar:
            guardado = restaurar(args.restaurar)
            print("Backup restaurado com sucesso.")
            if guardado:
                print(f"O banco anterior foi guardado em: {guardado}")
        else:
            print(f"Backup criado: {fazer_backup()}")
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as erro:
        print(f"Erro: {erro}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
