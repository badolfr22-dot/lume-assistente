"""Verificações básicas de saúde da aplicação (sem expor dados pessoais)."""

from __future__ import annotations

import time
from typing import Any

from assistente import __version__, config, db

TABELAS_ESPERADAS = {"usuarios", *db.TABELAS_DO_USUARIO}


def verificar() -> dict[str, Any]:
    cfg = config.configuracao()
    resultado: dict[str, Any] = {
        "versao": __version__, "ambiente": cfg.ambiente,
        "banco": "postgresql" if db.usando_postgres() else "sqlite", "ok": True, "checagens": {},
    }
    inicio = time.perf_counter()
    try:
        with db.conectar() as con:
            if con.postgres:
                integridade = "ok" if con.execute("SELECT 1 AS um").fetchone()["um"] == 1 else "falhou"
                linhas = con.execute("SELECT table_name AS nome FROM information_schema.tables "
                                     "WHERE table_schema = current_schema()").fetchall()
            else:
                integridade = con.execute("PRAGMA quick_check").fetchone()["quick_check"]
                linhas = con.execute("SELECT name AS nome FROM sqlite_master WHERE type = 'table'").fetchall()
        faltando = sorted(TABELAS_ESPERADAS - {linha["nome"] for linha in linhas})
        resultado["checagens"]["banco_integridade"] = integridade
        resultado["checagens"]["tabelas_faltando"] = faltando
        if integridade != "ok" or faltando:
            resultado["ok"] = False
    except db.ErroBanco as exc:
        resultado["ok"] = False
        resultado["checagens"]["banco_erro"] = type(exc.__cause__ or exc).__name__
    resultado["checagens"]["tempo_ms"] = round((time.perf_counter() - inicio) * 1000, 1)
    return resultado


if __name__ == "__main__":  # python -m assistente.saude
    import json
    import sys

    estado = verificar()
    print(json.dumps(estado, ensure_ascii=False, indent=2))
    sys.exit(0 if estado["ok"] else 1)
