import subprocess
import sys
from pathlib import Path

import pytest

from assistente import repositorio as r
from scripts import backup

RAIZ = Path(__file__).resolve().parent.parent


@pytest.mark.somente_sqlite
def test_backup_e_restauracao(tmp_path):
    r.criar_tarefa("Guardada no backup")
    arquivo = backup.fazer_backup(tmp_path / "bk")
    assert arquivo.exists()
    r.criar_tarefa("Criada depois do backup")
    guardado = backup.restaurar(arquivo, tmp_path / "bk")
    assert guardado is not None and guardado.exists()  # o banco anterior não foi perdido
    assert [t["titulo"] for t in r.listar_tarefas()] == ["Guardada no backup"]


@pytest.mark.somente_sqlite
def test_restaurar_recusa_arquivo_estranho(tmp_path):
    import sqlite3

    estranho = tmp_path / "outro.db"
    with sqlite3.connect(estranho) as con:
        con.execute("CREATE TABLE qualquer (x)")
    with pytest.raises(ValueError):
        backup.restaurar(estranho, tmp_path / "bk")


@pytest.mark.somente_sqlite
def test_verificar_saude_por_linha_de_comando(banco_temporario):
    resultado = subprocess.run([sys.executable, "scripts/verificar_saude.py"], cwd=RAIZ, capture_output=True,
                               text=True, env={**__import__("os").environ, "ASSISTENTE_BANCO": str(banco_temporario)})
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert '"ok": true' in resultado.stdout


def test_pasta_de_publicacao_so_tem_arquivos_seguros(tmp_path):
    from scripts import preparar_publicacao as pp
    destino = tmp_path / "publicacao"
    arquivos = pp.montar(destino)
    assert pp.conferir(arquivos, destino) == []
    assert {"app.py", "requirements.txt", ".streamlit/config.toml", "assistente/db.py"} <= set(arquivos)
    assert not any(a.startswith(("dados/", ".venv/", ".claude/", "backups")) or a.endswith((".db", ".pdf", ".env"))
                   for a in arquivos)
    config_pub = (destino / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert 'showErrorDetails = "none"' in config_pub and "localhost" not in config_pub and "[theme]" in config_pub


def test_conferencia_detecta_segredo(tmp_path):
    from scripts import preparar_publicacao as pp
    falso = "postgresql://user" + ":senha" + "@host/db"  # montado aqui para este arquivo não parecer ter segredo
    (tmp_path / "x.py").write_text(f'URL = "{falso}"', encoding="utf-8")
    (tmp_path / ".env").write_text("A=1", encoding="utf-8")
    problemas = pp.conferir(["x.py", ".env"], tmp_path)
    assert any("segredo" in p for p in problemas) and any("proibido" in p for p in problemas)


def test_redefinir_senha_do_administrador():
    from assistente import usuarios
    from scripts import redefinir_senha
    usuarios.criar_conta("ana@exemplo.com", "Ana", "senha1234", "senha1234", aceitou_privacidade=True)
    temporaria = redefinir_senha.redefinir("ANA@exemplo.com")
    assert usuarios.autenticar("ana@exemplo.com", temporaria)
    with pytest.raises(ValueError):
        redefinir_senha.redefinir("ninguem@exemplo.com")
