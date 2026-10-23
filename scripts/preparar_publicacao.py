"""Monta a pasta `publicacao/` com SOMENTE os arquivos que podem ir para o GitHub.

Uso:
    .venv\\Scripts\\python.exe scripts\\preparar_publicacao.py

Nunca copia: dados pessoais (dados/, backups/), segredos (.env, secrets.toml),
ambiente virtual (.venv), configurações locais (.claude), caches nem o PDF.
A pasta antiga `publicacao/` é substituída a cada execução.
"""

from __future__ import annotations

import re
import shutil
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "publicacao"

# Lista do que entra (todo o resto fica de fora).
ARQUIVOS = ["app.py", "requirements.txt", "requirements-dev.txt", ".gitignore", ".env.example", "pytest.ini",
            "README.md"]
PASTAS = ["assistente", "scripts", "tests", "docs"]
IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc", "*.db", "*.db-*", ".pytest_cache")

# Configuração do Streamlit para a hospedagem (porta/endereço ficam por conta do serviço).
CONFIG_PUBLICACAO = """\
[server]
headless = true
enableXsrfProtection = true
maxUploadSize = 5
runOnSave = false

[browser]
gatherUsageStats = false

[client]
showErrorDetails = "none"
toolbarMode = "viewer"

[logger]
level = "warning"
"""

PROIBIDOS = re.compile(r"(^|/)(\.env$|secrets\.toml$|dados/|backups|\.venv/|\.claude/)|\.db$|\.pdf$", re.IGNORECASE)
# Senha numa URL de banco (exemplos entre < > são ignorados) ou prefixos comuns de chaves.
SEGREDO = re.compile(r"(postgres(ql)?://[^\s'\"]*:[^\s'\"@<]+@|sk-[A-Za-z0-9-]{20,}|ghp_[A-Za-z0-9]{20,})")


def _limpar_arquivos_antigos(destino: Path) -> None:
    """Apaga os arquivos gerados antes. As pastas são reaproveitadas, porque o Windows/OneDrive
    pode mantê-las travadas por instantes; pastas vazias não são enviadas ao GitHub."""
    if not destino.exists():
        return
    for arquivo in sorted(destino.rglob("*"), reverse=True):
        if arquivo.is_file():
            for tentativa in range(5):
                try:
                    arquivo.unlink()
                    break
                except PermissionError:
                    if tentativa == 4:
                        raise
                    time.sleep(1)


def montar(destino: Path = DESTINO) -> list[str]:
    _limpar_arquivos_antigos(destino)
    destino.mkdir(parents=True, exist_ok=True)
    for nome in ARQUIVOS:
        shutil.copy2(RAIZ / nome, destino / nome)
    for pasta in PASTAS:
        shutil.copytree(RAIZ / pasta, destino / pasta, ignore=IGNORAR, dirs_exist_ok=True)
    tema = (RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8").split("[theme]", 1)[1]
    (destino / ".streamlit").mkdir(exist_ok=True)
    (destino / ".streamlit" / "config.toml").write_text(CONFIG_PUBLICACAO + "\n[theme]" + tema, encoding="utf-8")
    return sorted(p.relative_to(destino).as_posix() for p in destino.rglob("*") if p.is_file())


def conferir(arquivos: list[str], destino: Path = DESTINO) -> list[str]:
    """Problemas encontrados: arquivo proibido ou texto parecido com segredo."""
    problemas = [f"arquivo proibido: {a}" for a in arquivos if PROIBIDOS.search(a)]
    for a in arquivos:
        texto = (destino / a).read_text(encoding="utf-8", errors="ignore")
        if SEGREDO.search(texto):
            problemas.append(f"possível segredo em: {a}")
    return problemas


def main() -> int:
    arquivos = montar()
    problemas = conferir(arquivos)
    if problemas:
        print("ATENÇÃO, não publique:\n- " + "\n- ".join(problemas))
        return 1
    print(f"Pasta pronta: {DESTINO}")
    print(f"{len(arquivos)} arquivos, nenhum dado pessoal ou segredo encontrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
