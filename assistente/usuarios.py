"""Contas de usuário: cadastro, login, troca de senha e exclusão.

- Senhas nunca são guardadas: só um hash scrypt com sal aleatório.
- Após 5 senhas erradas seguidas, a conta fica bloqueada por 5 minutos.
- Excluir a conta apaga, em cascata, todos os dados daquela pessoa.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta
from typing import Any

from assistente import config, db
from assistente import validacao as v
from assistente.tempo import agora as _agora

TENTATIVAS_MAXIMAS = 5
BLOQUEIO_MINUTOS = 5
SENHA_MINIMA = 8
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MENSAGEM_LOGIN_INVALIDO = "E-mail ou senha incorretos."


# --- Senhas ----------------------------------------------------------------------

def gerar_hash(senha: str) -> str:
    sal = secrets.token_bytes(16)
    chave = hashlib.scrypt(senha.encode("utf-8"), salt=sal, dklen=32, **_SCRYPT)
    return "scrypt${n}${r}${p}${sal}${chave}".format(
        **_SCRYPT, sal=base64.b64encode(sal).decode(), chave=base64.b64encode(chave).decode())


def conferir_hash(senha: str, guardado: str) -> bool:
    try:
        nome, n, r, p, sal, chave = guardado.split("$")
        if nome != "scrypt":
            return False
        calculada = hashlib.scrypt(senha.encode("utf-8"), salt=base64.b64decode(sal), dklen=32,
                                   n=int(n), r=int(r), p=int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calculada, base64.b64decode(chave))


def validar_senha(senha: str) -> str:
    if not isinstance(senha, str) or len(senha) < SENHA_MINIMA:
        raise v.ErroValidacao(f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.")
    if len(senha) > 128:
        raise v.ErroValidacao("A senha aceita no máximo 128 caracteres.")
    if not re.search(r"[A-Za-zÀ-ÿ]", senha) or not re.search(r"\d", senha):
        raise v.ErroValidacao("A senha precisa ter letras e números.")
    return senha


def _validar_email(email: str) -> str:
    email = v.texto_obrigatorio(email, "E-mail", 254).lower()
    if not _EMAIL.match(email):
        raise v.ErroValidacao("Digite um e-mail válido, como nome@exemplo.com.")
    return email


# --- Contas ----------------------------------------------------------------------

def _publico(linha: dict[str, Any] | None) -> dict[str, Any] | None:
    """Dados da conta sem o hash da senha."""
    if linha is None:
        return None
    return {"id": linha["id"], "email": linha["email"], "nome": linha["nome"], "criado_em": linha["criado_em"]}


def criar_conta(email: str, nome: str, senha: str, confirmacao: str, codigo_convite: str = "",
                aceitou_privacidade: bool = False) -> dict[str, Any]:
    esperado = config.configuracao().codigo_convite
    if esperado and not hmac.compare_digest(codigo_convite.strip().encode(), esperado.encode()):
        raise v.ErroValidacao("Código de convite incorreto. Peça o código a quem administra o app.")
    email = _validar_email(email)
    nome = v.texto_obrigatorio(nome, "Nome", 60)
    validar_senha(senha)
    if senha != confirmacao:
        raise v.ErroValidacao("A confirmação não é igual à senha.")
    if not aceitou_privacidade:
        raise v.ErroValidacao("Para criar a conta, é preciso concordar com o aviso de privacidade.")
    if db.consultar_um("SELECT id FROM usuarios WHERE email = ?", (email,)):
        raise v.ErroValidacao("Já existe uma conta com esse e-mail.")
    id_ = db.inserir("INSERT INTO usuarios (email, nome, senha_hash, criado_em) VALUES (?, ?, ?, ?)",
                     (email, nome, gerar_hash(senha), _agora().isoformat(sep=" ")))
    return _publico(obter(id_))  # type: ignore[return-value]


def obter(id_: int) -> dict[str, Any] | None:
    return db.consultar_um("SELECT * FROM usuarios WHERE id = ?", (int(id_),))


def autenticar(email: str, senha: str, agora: datetime | None = None) -> dict[str, Any]:
    """Devolve a conta se e-mail e senha conferem. Mensagem igual para e-mail ou senha errados."""
    agora = agora or _agora()
    email = (email or "").strip().lower()
    conta = db.consultar_um("SELECT * FROM usuarios WHERE email = ? AND id != ?", (email, db.USUARIO_LOCAL))
    if conta is None:
        conferir_hash(senha or "", gerar_hash("tempo-constante-1"))  # evita revelar se o e-mail existe pelo tempo
        raise v.ErroValidacao(MENSAGEM_LOGIN_INVALIDO)
    if conta["bloqueado_ate"] and conta["bloqueado_ate"] > agora.isoformat(sep=" "):
        raise v.ErroValidacao(f"Muitas tentativas erradas. Tente de novo em {BLOQUEIO_MINUTOS} minutos.")
    if not conferir_hash(senha or "", conta["senha_hash"]):
        falhas = conta["falhas"] + 1
        bloqueio = None
        if falhas >= TENTATIVAS_MAXIMAS:
            bloqueio = (agora + timedelta(minutes=BLOQUEIO_MINUTOS)).isoformat(sep=" ")
            falhas = 0
        db.executar("UPDATE usuarios SET falhas = ?, bloqueado_ate = ? WHERE id = ?", (falhas, bloqueio, conta["id"]))
        raise v.ErroValidacao(MENSAGEM_LOGIN_INVALIDO)
    db.executar("UPDATE usuarios SET falhas = 0, bloqueado_ate = NULL, ultimo_login = ? WHERE id = ?",
                (agora.isoformat(sep=" "), conta["id"]))
    return _publico(conta)  # type: ignore[return-value]


def alterar_senha(id_: int, atual: str, nova: str, confirmacao: str) -> None:
    conta = obter(id_)
    if conta is None or not conferir_hash(atual or "", conta["senha_hash"]):
        raise v.ErroValidacao("A senha atual está incorreta.")
    validar_senha(nova)
    if nova != confirmacao:
        raise v.ErroValidacao("A confirmação não é igual à nova senha.")
    db.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (gerar_hash(nova), int(id_)))


def alterar_nome(id_: int, nome: str) -> None:
    db.executar("UPDATE usuarios SET nome = ? WHERE id = ?", (v.texto_obrigatorio(nome, "Nome", 60), int(id_)))


def excluir_conta(id_: int, senha: str) -> None:
    """Apaga a conta e TODOS os dados dela (tarefas, metas, agenda, anotações...)."""
    conta = obter(id_)
    if conta is None or int(id_) == db.USUARIO_LOCAL or not conferir_hash(senha or "", conta["senha_hash"]):
        raise v.ErroValidacao("Senha incorreta. A conta não foi excluída.")
    with db.conectar() as con:
        for tabela in reversed(db.TABELAS_DO_USUARIO):  # nomes fixos
            con.execute(f"DELETE FROM {tabela} WHERE usuario_id = ?", (int(id_),))
        con.execute("DELETE FROM usuarios WHERE id = ?", (int(id_),))
