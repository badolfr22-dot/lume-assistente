"""Ferramenta do administrador: define uma senha temporária para uma conta.

Uso (com a variável ASSISTENTE_DATABASE_URL apontando para o banco da hospedagem):
    .venv\\Scripts\\python.exe scripts\\redefinir_senha.py pessoa@exemplo.com

A senha temporária é gerada aleatoriamente e mostrada UMA vez. Entregue-a à
pessoa por um canal privado e peça que ela troque em Configurações → Minha conta.
"""

from __future__ import annotations

import secrets
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assistente import db, usuarios  # noqa: E402


def gerar_senha_temporaria() -> str:
    alfabeto = string.ascii_letters + string.digits
    while True:
        senha = "".join(secrets.choice(alfabeto) for _ in range(14))
        if any(c.isdigit() for c in senha) and any(c.isalpha() for c in senha):
            return senha


def redefinir(email: str) -> str:
    conta = db.consultar_um("SELECT id FROM usuarios WHERE email = ? AND id != ?",
                            (email.strip().lower(), db.USUARIO_LOCAL))
    if conta is None:
        raise ValueError("Nenhuma conta com esse e-mail.")
    senha = gerar_senha_temporaria()
    db.executar("UPDATE usuarios SET senha_hash = ?, falhas = 0, bloqueado_ate = NULL WHERE id = ?",
                (usuarios.gerar_hash(senha), conta["id"]))
    return senha


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    try:
        senha = redefinir(sys.argv[1])
    except (ValueError, db.ErroBanco) as erro:
        print(f"Erro: {erro}")
        return 1
    print(f"Senha temporária (mostrada só agora): {senha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
