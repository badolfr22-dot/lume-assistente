import json

import pytest

from assistente import configuracoes as cfg, preferencias as pref, repositorio as r
from assistente.validacao import ErroValidacao


# --- Preferências / memória controlada ----------------------------------------------

def test_salvar_editar_excluir_preferencia():
    id_ = pref.salvar("categorias_favoritas", "Principal", "Estudos")
    item = pref.obter(id_)
    assert (item["categoria"], item["chave"], item["valor"]) == ("categorias_favoritas", "principal", "Estudos")
    assert pref.editar(id_, "Trabalho")
    assert pref.obter(id_)["valor"] == "Trabalho"
    assert pref.categorias_favoritas() == ["Trabalho"]
    assert pref.excluir(id_)
    assert pref.listar() == []


def test_salvar_mesma_chave_atualiza_sem_duplicar():
    a = pref.salvar("painel", "mostrar metas", "sim")
    b = pref.salvar("painel", "Mostrar  Metas", "não")
    assert a == b
    assert len(pref.listar()) == 1 and pref.listar()[0]["valor"] == "não"


def test_limpar_todas_preserva_tarefas():
    r.criar_tarefa("Continua")
    pref.salvar("outros", "cor favorita", "azul")
    pref.salvar("painel", "ordem", "tarefas primeiro")
    assert pref.limpar_tudo() == 2
    assert pref.listar() == []
    assert len(r.listar_tarefas()) == 1


@pytest.mark.parametrize("chave, valor", [
    ("senha do banco", "123456"),
    ("meu token", "abc"),
    ("api key", "qualquer"),
    ("cartão", "4111 1111 1111 1111"),
    ("documento", "123.456.789-09"),
    # Tokens falsos montados aqui para o arquivo não parecer conter segredos reais.
    ("github", "ghp" + "_abcdefghijklmnopqrstuvwxyz123456"),
    ("chave", "sk" + "-proj-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"),
])
def test_recusa_dados_sensiveis(chave, valor):
    with pytest.raises(ErroValidacao, match="Por segurança"):
        pref.salvar("outros", chave, valor)
    assert pref.listar() == []


def test_recusa_dado_sensivel_ao_editar():
    id_ = pref.salvar("outros", "lembrete", "beber água")
    with pytest.raises(ErroValidacao):
        pref.editar(id_, "minha senha é 1234")
    assert pref.obter(id_)["valor"] == "beber água"


def test_texto_comum_nao_e_bloqueado():
    pref.salvar("horarios", "melhor horário para estudar", "manhã, das 8h às 10h")
    pref.salvar("outros", "spinning", "terça e quinta")  # contém "pin" mas não é PIN


def test_horario_do_dia_validado():
    with pytest.raises(ErroValidacao, match="Horário inválido"):
        pref.salvar("horarios", "inicio do dia", "8 da manhã")
    pref.salvar("horarios", "inicio do dia", "08:00")


def test_categoria_invalida():
    with pytest.raises(ErroValidacao):
        pref.salvar("tarefas", "x", "y")


# --- Configurações ------------------------------------------------------------

def test_padroes_e_salvar():
    assert cfg.obter("tema") == "claro"
    novas = cfg.salvar({"tema": "escuro", "nome_assistente": "Aurora", "formato_data": "aaaa-mm-dd",
                        "sugestoes_maximo": 3})
    assert (novas["tema"], novas["nome_assistente"], novas["formato_data"], novas["sugestoes_maximo"]) == \
        ("escuro", "Aurora", "aaaa-mm-dd", 3)


@pytest.mark.parametrize("alteracao", [
    {"tema": "roxo"}, {"nome_assistente": ""}, {"formato_data": "dd.mm"}, {"sugestoes_maximo": 0},
    {"notificacoes_tipos": ["spam"]}, {"chave_inexistente": 1},
])
def test_configuracao_invalida(alteracao):
    with pytest.raises(ErroValidacao):
        cfg.salvar(alteracao)


def test_restaurar_padroes_nao_apaga_dados():
    r.criar_tarefa("T")
    r.criar_meta("M")
    r.criar_anotacao("A")
    pref.salvar("outros", "x", "y")
    cfg.salvar({"tema": "escuro", "nome_assistente": "Outro"})
    cfg.restaurar_padroes()
    assert cfg.obter_todas() == cfg.PADROES
    assert len(r.listar_tarefas()) == len(r.listar_metas()) == len(r.listar_anotacoes()) == 1
    assert len(pref.listar()) == 1


def test_valor_corrompido_volta_ao_padrao():
    from assistente import db
    db.executar("INSERT INTO configuracoes (usuario_id, chave, valor, atualizado_em) "
                "VALUES (1, 'tema', '{quebrado', 'x')")
    assert cfg.obter("tema") == "claro"


def test_configuracao_salva_como_json():
    cfg.salvar({"notificacoes_tipos": ["lembretes"]})
    from assistente import db
    assert json.loads(db.consultar_um("SELECT valor FROM configuracoes WHERE chave = 'notificacoes_tipos'")["valor"]) \
        == ["lembretes"]
