import re
from pathlib import Path

import pytest

from assistente import acesso, db, repositorio as r, saude
from assistente.config import carregar_configuracao
from assistente.validacao import ErroValidacao, texto_opcional

RAIZ = Path(__file__).resolve().parent.parent


# --- SQL injection -------------------------------------------------------------------

@pytest.mark.parametrize("malicioso", [
    "'; DROP TABLE tarefas; --",
    "\" OR \"1\"=\"1",
    "Robert'); DELETE FROM metas; --",
])
def test_entradas_maliciosas_sao_gravadas_como_texto(malicioso):
    r.criar_meta("Meta que deve sobreviver")
    id_ = r.criar_tarefa(malicioso)
    assert r.obter_tarefa(id_)["titulo"] == malicioso
    assert len(r.listar_metas()) == 1
    assert r.listar_anotacoes(malicioso) == []


def test_id_nao_numerico_e_rejeitado():
    with pytest.raises((ValueError, TypeError)):
        r.obter_tarefa("1 OR 1=1")


def test_nenhum_sql_monta_valores_do_usuario_com_fstring():
    """Procura f-strings SQL que interpolem algo além de nomes fixos conhecidos."""
    permitidos = {"tabela", "trecho", "' AND '.join(condicoes)", "tipo", "coluna_data", "t", "colunas",
                  "extra[filtro]", "consultas[filtro]", "_soma('progresso = 100')", "indice",
                  "db.contem('titulo')", "db.contem('conteudo')", "db.contem('tags')"}
    sql = re.compile(r'f"((?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE)[^"]*)"')
    for arquivo in (RAIZ / "assistente").rglob("*.py"):
        for trecho in sql.findall(arquivo.read_text(encoding="utf-8")):
            for expressao in re.findall(r"\{([^}]+)\}", trecho):
                assert expressao.strip() in permitidos, f"{arquivo.name}: {{{expressao}}}"


# --- Validação ----------------------------------------------------------------------

def test_remove_caracteres_de_controle():
    assert texto_opcional("a\x00b\x07c\nd", "x") == "abc\nd"


def test_tipos_inesperados():
    with pytest.raises(ErroValidacao):
        r.criar_tarefa(None)  # type: ignore[arg-type]
    id_ = r.criar_tarefa(12345)  # type: ignore[arg-type]
    assert r.obter_tarefa(id_)["titulo"] == "12345"


# --- Erros sem vazar detalhes ------------------------------------------------------------

def test_erro_de_banco_tem_mensagem_amigavel():
    with pytest.raises(db.ErroBanco) as info:
        db.executar("INSERT INTO tarefas (usuario_id, titulo, prioridade, criado_em, atualizado_em) "
                    "VALUES (?, ?, ?, ?, ?)", (1, "x", "urgente", "a", "b"))
    assert "CHECK" not in str(info.value)


def test_recupera_apos_falha_temporaria_do_banco():
    r.criar_tarefa("Antes da falha")
    with pytest.raises(db.ErroBanco, match="indisponível"):
        db.consultar("SELECT * FROM tabela_que_nao_existe")
    assert [t["titulo"] for t in r.listar_tarefas()] == ["Antes da falha"]


def test_erro_no_meio_da_operacao_desfaz_tudo():
    with pytest.raises(RuntimeError):
        with db.conectar() as con:
            con.execute("INSERT INTO anotacoes (usuario_id, titulo, criado_em, atualizado_em) "
                        "VALUES (1, 'x', 'a', 'b')")
            raise RuntimeError("falha simulada")
    assert r.listar_anotacoes() == []


# --- Segredos e configuração -----------------------------------------------------------

def test_nao_ha_chaves_no_codigo():
    padrao = re.compile(r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
                        r"(api_key|password|senha)\s*=\s*['\"][^'\"]{6,}['\"])", re.IGNORECASE)
    arquivos = [*RAIZ.glob("*.py"), *(RAIZ / "assistente").rglob("*.py"), *(RAIZ / "scripts").glob("*.py"),
                RAIZ / ".env.example"]
    for arquivo in arquivos:
        if arquivo.exists():
            assert not padrao.search(arquivo.read_text(encoding="utf-8")), arquivo.name


def test_gitignore_protege_dados_e_env():
    conteudo = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    for item in (".env", "dados/", "*.db", ".venv/", ".streamlit/secrets.toml"):
        assert item in conteudo


def test_env_example_sem_valores_secretos():
    for linha in (RAIZ / ".env.example").read_text(encoding="utf-8").splitlines():
        if linha.startswith("ASSISTENTE_SENHA_ACESSO="):
            assert linha.strip() == "ASSISTENTE_SENHA_ACESSO="


def test_configuracao_dev_e_prod(tmp_path):
    dev = carregar_configuracao({})
    assert dev.ambiente == "desenvolvimento" and not dev.producao and dev.nivel_log == "INFO"
    prod = carregar_configuracao({"ASSISTENTE_AMBIENTE": "producao", "ASSISTENTE_BANCO": str(tmp_path / "p.db")})
    assert prod.producao and prod.nivel_log == "WARNING" and prod.caminho_banco == tmp_path / "p.db"
    assert carregar_configuracao({"ASSISTENTE_AMBIENTE": "qualquer"}).ambiente == "desenvolvimento"
    relativo = carregar_configuracao({"ASSISTENTE_BANCO": "dados/x.db"})
    assert relativo.caminho_banco.is_absolute()
    # Contas: ligadas por padrão em produção, desligadas no uso local, e controláveis pela variável
    assert prod.multiusuario and not dev.multiusuario
    assert carregar_configuracao({"ASSISTENTE_CONTAS": "sim"}).multiusuario
    assert not carregar_configuracao({"ASSISTENTE_AMBIENTE": "producao", "ASSISTENTE_CONTAS": "nao"}).multiusuario
    pg = carregar_configuracao({"ASSISTENTE_DATABASE_URL": "postgresql://u@h/b"})
    assert pg.postgres and not dev.postgres


def test_secrets_do_streamlit_sao_lidos_e_ambiente_tem_prioridade(monkeypatch):
    from assistente import config
    monkeypatch.setattr(config, "_ler_segredos_streamlit",
                        lambda: {"ASSISTENTE_CONTAS": "sim", "ASSISTENTE_CODIGO_CONVITE": "do-secrets"})
    monkeypatch.setenv("ASSISTENTE_CODIGO_CONVITE", "do-ambiente")
    cfg = config.carregar_configuracao()
    assert cfg.multiusuario
    assert cfg.codigo_convite == "do-ambiente"


URL_FALSA = "postgresql://u" + ":s" + "@ep-x.neon.tech/neondb?sslmode=require"  # montada aqui de propósito


@pytest.mark.parametrize("colado", [
    URL_FALSA,
    f"  {URL_FALSA}  ",
    f"psql '{URL_FALSA}'",
    f"DATABASE_URL={URL_FALSA}",
    f'DATABASE_URL="{URL_FALSA}"',
])
def test_url_do_banco_e_extraida_de_formatos_copiados(colado):
    from assistente import config
    cfg = config.carregar_configuracao({"ASSISTENTE_DATABASE_URL": colado})
    assert cfg.postgres
    assert cfg.url_banco == URL_FALSA


@pytest.mark.parametrize("valor, trecho", [
    ("", "vazia"),
    ("COLE-AQUI-A-CONNECTION-STRING-DO-NEON", "texto de exemplo"),
    ("mysql://x", "não contém"),
])
def test_diagnostico_da_url_nao_mostra_o_valor(valor, trecho):
    from assistente import config
    motivo = config.diagnosticar_url_banco(valor)
    assert trecho in motivo
    assert not valor or valor not in motivo


def test_sem_secrets_nao_quebra():
    from assistente import config
    assert isinstance(config._ler_segredos_streamlit(), dict)


# --- Senha de acesso opcional ------------------------------------------------------------

def test_senha_de_acesso():
    assert acesso.senha_confere("qualquer", "")
    assert acesso.senha_confere("certa", "certa")
    assert not acesso.senha_confere("errada", "certa")


def test_bloqueio_apos_tentativas():
    controle = acesso.ControleTentativas()
    for _ in range(acesso.TENTATIVAS_MAXIMAS):
        controle.registrar_erro(agora=100.0)
    assert controle.bloqueado(agora=110.0)
    assert not controle.bloqueado(agora=100.0 + acesso.BLOQUEIO_SEGUNDOS + 1)


# --- Saúde --------------------------------------------------------------------------------

def test_health_check():
    estado = saude.verificar()
    assert estado["ok"] is True
    assert estado["checagens"]["banco_integridade"] == "ok"
    assert estado["checagens"]["tabelas_faltando"] == []
    assert "caminho" not in str(estado).lower()  # não expõe caminho de arquivos
