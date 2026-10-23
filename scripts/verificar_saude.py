"""Verificação de saúde do assistente.

Uso:
    .venv\\Scripts\\python.exe scripts\\verificar_saude.py
    .venv\\Scripts\\python.exe scripts\\verificar_saude.py --url http://localhost:8501

Sem --url: confere o banco (integridade e tabelas).
Com --url: também confere se o servidor Streamlit responde em /_stcore/health.
Saída 0 = saudável, 1 = problema. Nenhum dado pessoal é exibido.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assistente import saude  # noqa: E402


def checar_servidor(url: str) -> bool:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/_stcore/health", timeout=5) as resposta:  # noqa: S310
            return resposta.status == 200
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica a saúde do assistente.")
    parser.add_argument("--url", help="Endereço do app em execução, ex.: http://localhost:8501")
    args = parser.parse_args()
    estado = saude.verificar()
    if args.url:
        if not args.url.startswith(("http://", "https://")):
            parser.error("--url deve começar com http:// ou https://")
        estado["checagens"]["servidor_responde"] = checar_servidor(args.url)
        estado["ok"] = estado["ok"] and estado["checagens"]["servidor_responde"]
    print(json.dumps(estado, ensure_ascii=False, indent=2))
    return 0 if estado["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
