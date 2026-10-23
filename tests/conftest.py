"""Configuração comum dos testes.

Por padrão cada teste usa um banco SQLite novo e vazio. Para rodar a MESMA
suíte contra um PostgreSQL, defina ASSISTENTE_TESTE_PG_URL (um banco de teste
descartável: as tabelas são esvaziadas antes de cada teste).
"""

import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from assistente import config, db  # noqa: E402

URL_PG_TESTE = os.environ.get("ASSISTENTE_TESTE_PG_URL", "")


def pytest_report_header(config):  # noqa: ARG001
    return f"banco dos testes: {'PostgreSQL' if URL_PG_TESTE else 'SQLite temporário'}"


def pytest_configure(config):
    config.addinivalue_line("markers", "somente_sqlite: teste específico do SQLite (pulado no PostgreSQL)")


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    if URL_PG_TESTE:
        pular = pytest.mark.skip(reason="específico do SQLite")
        for item in items:
            if "somente_sqlite" in item.keywords:
                item.add_marker(pular)


def _esvaziar_postgres() -> None:
    with db.conectar() as con:
        con.execute("TRUNCATE usuarios, " + ", ".join(db.TABELAS_DO_USUARIO) + " RESTART IDENTITY CASCADE")
        db._garantir_usuario_local(con)


@pytest.fixture(autouse=True)
def banco_temporario(tmp_path, monkeypatch):
    """Cada teste usa um banco vazio. O banco real nunca é tocado."""
    caminho = tmp_path / "teste.db"
    monkeypatch.setenv("ASSISTENTE_BANCO", str(caminho))
    monkeypatch.delenv("ASSISTENTE_CONTAS", raising=False)
    monkeypatch.delenv("ASSISTENTE_CODIGO_CONVITE", raising=False)
    monkeypatch.delenv("ASSISTENTE_SENHA_ACESSO", raising=False)
    monkeypatch.delenv("ASSISTENTE_DATABASE_URL", raising=False)
    monkeypatch.setenv("ASSISTENTE_AMBIENTE", "desenvolvimento")
    config.recarregar()
    db.definir_usuario(None)
    from assistente import usuarios
    usuarios.limite_convite.zerar()  # o limite é global no processo; cada teste começa do zero
    if URL_PG_TESTE:
        db.definir_url_banco(URL_PG_TESTE)
        _esvaziar_postgres()
    else:
        db.definir_caminho_banco(caminho)
    yield caminho
    db.definir_usuario(None)
    db.definir_caminho_banco(None)
    db.definir_url_banco(None)
    config.recarregar()
