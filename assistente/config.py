"""Configuração da aplicação lida de variáveis de ambiente.

Ordem de prioridade: variáveis de ambiente do sistema > arquivo .env > padrões.
Nenhum segredo fica no código. O arquivo .env é opcional e não vai para o
controle de versão (veja .env.example). Na hospedagem, as variáveis são
definidas no painel de segredos do serviço.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent

AMBIENTES_VALIDOS = ("desenvolvimento", "producao")
VERDADEIRO = ("1", "sim", "true", "verdadeiro", "yes", "on")


def _ler_arquivo_env(caminho: Path) -> dict[str, str]:
    """Lê um arquivo .env simples (CHAVE=valor). Linhas com # são ignoradas."""
    valores: dict[str, str] = {}
    if not caminho.is_file():
        return valores
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valor = valor.strip().strip('"').strip("'")
        valores[chave.strip()] = valor
    return valores


def _ler_segredos_streamlit() -> dict[str, str]:
    """Chaves de primeiro nível do painel "Secrets" do Streamlit (ou .streamlit/secrets.toml)."""
    try:
        import streamlit as st

        return {str(k): str(v) for k, v in st.secrets.items() if isinstance(v, (str, int, float, bool))}
    except Exception:  # noqa: BLE001 - sem arquivo de segredos é o caso normal no uso local
        return {}


@dataclass(frozen=True)
class Configuracao:
    ambiente: str
    caminho_banco: Path
    url_banco: str  # vazio = SQLite local; "postgresql://..." = banco online
    nivel_log: str
    senha_acesso: str  # senha única opcional (modo de uma pessoa só)
    provedor_ia: str  # "regras" (padrão, local). Outros provedores são opcionais/futuros.
    multiusuario: bool  # True = cada pessoa tem conta e dados separados
    codigo_convite: str  # se definido, só cria conta quem souber o código

    @property
    def producao(self) -> bool:
        return self.ambiente == "producao"

    @property
    def postgres(self) -> bool:
        return self.url_banco.startswith(("postgresql://", "postgres://"))


def carregar_configuracao(env: dict[str, str] | None = None) -> Configuracao:
    """Monta a configuração. `env` permite injetar valores nos testes."""
    if env is None:
        # Prioridade: variáveis do sistema > Secrets do Streamlit > arquivo .env
        env = {**_ler_arquivo_env(RAIZ_PROJETO / ".env"), **_ler_segredos_streamlit(), **os.environ}

    ambiente = env.get("ASSISTENTE_AMBIENTE", "desenvolvimento").strip().lower()
    if ambiente not in AMBIENTES_VALIDOS:
        ambiente = "desenvolvimento"

    caminho = env.get("ASSISTENTE_BANCO", "").strip()
    caminho_banco = Path(caminho) if caminho else RAIZ_PROJETO / "dados" / "assistente.db"
    if not caminho_banco.is_absolute():
        caminho_banco = RAIZ_PROJETO / caminho_banco

    nivel_padrao = "WARNING" if ambiente == "producao" else "INFO"
    nivel_log = env.get("ASSISTENTE_NIVEL_LOG", nivel_padrao).strip().upper() or nivel_padrao

    contas = env.get("ASSISTENTE_CONTAS", "").strip().lower()
    multiusuario = contas in VERDADEIRO if contas else ambiente == "producao"

    return Configuracao(
        ambiente=ambiente,
        caminho_banco=caminho_banco,
        url_banco=env.get("ASSISTENTE_DATABASE_URL", "").strip(),
        nivel_log=nivel_log,
        senha_acesso=env.get("ASSISTENTE_SENHA_ACESSO", ""),
        provedor_ia=env.get("ASSISTENTE_IA_PROVEDOR", "regras").strip().lower() or "regras",
        multiusuario=multiusuario,
        codigo_convite=env.get("ASSISTENTE_CODIGO_CONVITE", "").strip(),
    )


@lru_cache(maxsize=1)
def configuracao() -> Configuracao:
    """Configuração lida uma vez por processo (evita ler o .env a cada consulta)."""
    return carregar_configuracao()


def recarregar() -> Configuracao:
    configuracao.cache_clear()
    return configuracao()
