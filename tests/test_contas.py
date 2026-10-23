from datetime import datetime, timedelta

import pytest

from assistente import config, db, repositorio as r, usuarios as u
from assistente.validacao import ErroValidacao

SENHA = "segredo123"


def criar(email="ana@exemplo.com", nome="Ana", senha=SENHA, **extra):
    return u.criar_conta(email, nome, senha, senha, aceitou_privacidade=True, **extra)


def test_criar_conta_e_entrar():
    conta = criar(email="  Ana@Exemplo.COM ")
    assert conta["email"] == "ana@exemplo.com"
    assert "senha_hash" not in conta
    assert u.autenticar("ANA@exemplo.com", SENHA)["id"] == conta["id"]


def test_senha_nunca_e_guardada_em_texto():
    conta = criar()
    guardado = u.obter(conta["id"])["senha_hash"]
    assert SENHA not in guardado and guardado.startswith("scrypt$")
    assert u.gerar_hash(SENHA) != u.gerar_hash(SENHA)  # sal aleatório


@pytest.mark.parametrize("dados, trecho", [
    ({"email": "sem-arroba"}, "e-mail válido"),
    ({"senha": "curta1"}, "pelo menos 8"),
    ({"senha": "somenteletras"}, "letras e números"),
    ({"senha": "12345678"}, "letras e números"),
    ({"nome": ""}, "obrigatório"),
])
def test_validacoes_do_cadastro(dados, trecho):
    with pytest.raises(ErroValidacao, match=trecho):
        criar(**dados)


def test_confirmacao_privacidade_e_duplicado():
    with pytest.raises(ErroValidacao, match="confirmação"):
        u.criar_conta("a@b.com", "A", SENHA, "outra123", aceitou_privacidade=True)
    with pytest.raises(ErroValidacao, match="aviso de privacidade"):
        u.criar_conta("a@b.com", "A", SENHA, SENHA)
    criar()
    with pytest.raises(ErroValidacao, match="Já existe"):
        criar(nome="Outra Ana")


def test_codigo_de_convite(monkeypatch):
    monkeypatch.setenv("ASSISTENTE_CODIGO_CONVITE", "convite-123")
    config.recarregar()
    with pytest.raises(ErroValidacao, match="convite"):
        criar()
    with pytest.raises(ErroValidacao, match="convite"):
        criar(codigo_convite="errado")
    assert criar(codigo_convite="convite-123")["id"]


def test_login_errado_tem_mensagem_unica():
    criar()
    with pytest.raises(ErroValidacao) as senha_errada:
        u.autenticar("ana@exemplo.com", "errada999")
    with pytest.raises(ErroValidacao) as email_errado:
        u.autenticar("ninguem@exemplo.com", SENHA)
    assert str(senha_errada.value) == str(email_errado.value) == u.MENSAGEM_LOGIN_INVALIDO


def test_bloqueio_apos_tentativas_erradas():
    criar()
    agora = datetime(2026, 10, 22, 10, 0)
    for _ in range(u.TENTATIVAS_MAXIMAS):
        with pytest.raises(ErroValidacao):
            u.autenticar("ana@exemplo.com", "errada999", agora)
    with pytest.raises(ErroValidacao, match="Muitas tentativas"):
        u.autenticar("ana@exemplo.com", SENHA, agora)  # nem a senha certa entra durante o bloqueio
    depois = agora + timedelta(minutes=u.BLOQUEIO_MINUTOS, seconds=1)
    assert u.autenticar("ana@exemplo.com", SENHA, depois)


def test_usuario_local_nao_pode_entrar():
    with pytest.raises(ErroValidacao):
        u.autenticar("local@localhost", "")


def test_alterar_senha_e_nome():
    conta = criar()
    with pytest.raises(ErroValidacao, match="atual está incorreta"):
        u.alterar_senha(conta["id"], "errada999", "nova12345", "nova12345")
    u.alterar_senha(conta["id"], SENHA, "nova12345", "nova12345")
    assert u.autenticar("ana@exemplo.com", "nova12345")
    with pytest.raises(ErroValidacao):
        u.autenticar("ana@exemplo.com", SENHA)
    u.alterar_nome(conta["id"], "Ana Maria")
    assert u.obter(conta["id"])["nome"] == "Ana Maria"


def test_excluir_conta_apaga_todos_os_dados_so_dela():
    ana = criar()
    bia = criar(email="bia@exemplo.com", nome="Bia")
    db.definir_usuario(ana["id"])
    r.criar_tarefa("Da Ana")
    r.criar_meta("Meta da Ana")
    db.definir_usuario(bia["id"])
    r.criar_tarefa("Da Bia")
    with pytest.raises(ErroValidacao, match="Senha incorreta"):
        u.excluir_conta(ana["id"], "errada999")
    u.excluir_conta(ana["id"], SENHA)
    assert u.obter(ana["id"]) is None
    restantes = db.consultar("SELECT titulo, usuario_id FROM tarefas")
    assert restantes == [{"titulo": "Da Bia", "usuario_id": bia["id"]}]
    assert db.consultar("SELECT * FROM metas") == []


def test_modo_com_contas_exige_usuario(monkeypatch):
    monkeypatch.setenv("ASSISTENTE_CONTAS", "sim")
    config.recarregar()
    with pytest.raises(db.ErroAcesso):
        r.listar_tarefas()
    conta = criar()
    db.definir_usuario(conta["id"])
    assert r.listar_tarefas() == []
