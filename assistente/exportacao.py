"""Exportação dos dados pessoais (JSON completo ou CSVs dentro de um ZIP)."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from typing import Any

from assistente import __version__, db
from assistente.tempo import agora_iso

TABELAS_EXPORTADAS = ("tarefas", "metas", "compromissos", "anotacoes", "preferencias", "configuracoes",
                      "lembretes", "notificacoes", "automacoes", "automacoes_historico")


def coletar() -> dict[str, list[dict[str, Any]]]:
    # Nomes de tabela vêm da tupla fixa acima.
    return {tabela: db.consultar(f"SELECT * FROM {tabela} WHERE usuario_id = ? ORDER BY 2, 1",
                                 (db.usuario_atual(),)) for tabela in TABELAS_EXPORTADAS}


def para_json() -> bytes:
    conta = db.consultar_um("SELECT nome, email, criado_em FROM usuarios WHERE id = ?", (db.usuario_atual(),))
    pacote = {"aplicativo": "Assistente pessoal digital", "versao": __version__,
              "exportado_em": agora_iso(), "conta": conta, "dados": coletar()}
    return json.dumps(pacote, ensure_ascii=False, indent=2).encode("utf-8")


def para_zip_csv() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as arquivo_zip:
        for tabela, linhas in coletar().items():
            texto = io.StringIO()
            if linhas:
                escritor = csv.DictWriter(texto, fieldnames=list(linhas[0].keys()))
                escritor.writeheader()
                for linha in linhas:
                    # Evita "injeção de fórmulas" ao abrir o CSV no Excel.
                    escritor.writerow({k: (f"'{x}" if isinstance(x, str) and x[:1] in "=+-@" else x)
                                       for k, x in linha.items()})
            arquivo_zip.writestr(f"{tabela}.csv", "﻿" + texto.getvalue())
    return buffer.getvalue()
