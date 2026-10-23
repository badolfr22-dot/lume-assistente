from datetime import date

import pytest

from assistente import repositorio as r
from assistente.chat import EstadoChat, ProvedorRegras, normalizar
from assistente.ia import obter_provedor

HOJE = date(2026, 10, 22)


@pytest.fixture
def chat():
    provedor = ProvedorRegras()
    estado = EstadoChat()
    return lambda msg: provedor.responder(msg, estado, HOJE), estado


def test_normalizar_mantem_tamanho():
    texto = "Reunião amanhã às 10h"
    assert normalizar(texto) == "reuniao amanha as 10h"
    assert len(normalizar(texto)) == len(texto)


def test_ajuda_e_topicos(chat):
    falar, _ = chat
    assert "Exemplos" in falar("ajuda").texto
    assert "Planejador" in falar("como funciona o planejador?").texto
    assert "Metas" in falar("ajuda metas").texto


def test_comando_desconhecido_e_honesto(chat):
    falar, _ = chat
    resposta = falar("qual a capital da França?")
    assert "não entendi" in resposta.texto
    assert "não com inteligência artificial" in resposta.texto


def test_mensagem_vazia_e_longa(chat):
    falar, _ = chat
    assert "Digite" in falar("   ").texto
    assert "muito longa" in falar("a" * 600).texto


def test_criar_tarefa_pede_confirmacao_e_preserva_acentos(chat):
    falar, estado = chat
    resposta = falar("Criar tarefa Ligar para o médico amanhã prioridade alta")
    assert resposta.aguardando_confirmacao
    assert "Ligar para o médico" in resposta.texto
    assert r.listar_tarefas() == []  # nada criado antes de confirmar
    assert "Pronto" in falar("sim").texto
    tarefa = r.listar_tarefas()[0]
    assert tarefa["titulo"] == "Ligar para o médico"
    assert tarefa["prazo"] == "2026-10-23"
    assert tarefa["prioridade"] == "alta"
    assert estado.pendente is None


def test_criar_tarefa_com_data_numerica(chat):
    falar, _ = chat
    falar("nova tarefa Pagar boleto até 30/10")
    falar("sim")
    assert r.listar_tarefas()[0]["prazo"] == "2026-10-30"


def test_data_inexistente_gera_erro_claro(chat):
    falar, _ = chat
    assert "não existe" in falar("criar tarefa X 31/02").texto


def test_cancelar_nao_altera_nada(chat):
    falar, _ = chat
    id_ = r.criar_tarefa("Importante")
    falar(f"excluir tarefa {id_}")
    assert "cancelei" in falar("não").texto
    assert r.obter_tarefa(id_) is not None


def test_excluir_com_confirmacao(chat):
    falar, _ = chat
    id_ = r.criar_tarefa("Apagar")
    resposta = falar(f"apagar tarefa #{id_}")
    assert resposta.aguardando_confirmacao and "não pode ser desfeita" in resposta.texto
    falar("sim")
    assert r.obter_tarefa(id_) is None


def test_outro_comando_cancela_pendente(chat):
    falar, estado = chat
    id_ = r.criar_tarefa("Fica")
    falar(f"excluir tarefa {id_}")
    resposta = falar("tarefas")
    assert "foi cancelada" in resposta.texto
    assert r.obter_tarefa(id_) is not None
    assert estado.pendente is None


def test_concluir_tarefa(chat):
    falar, _ = chat
    id_ = r.criar_tarefa("Concluir")
    falar(f"concluir tarefa {id_}")
    falar("sim")
    assert r.obter_tarefa(id_)["status"] == "concluida"
    assert "já está concluída" in falar(f"concluir tarefa {id_}").texto


def test_item_inexistente(chat):
    falar, _ = chat
    assert "Não encontrei" in falar("excluir tarefa 999").texto
    assert "Não encontrei" in falar("concluir tarefa 999").texto
    assert "Não encontrei" in falar("excluir meta 999").texto


def test_consultas_usam_dados_reais(chat):
    falar, _ = chat
    assert "não tem tarefas pendentes" in falar("tarefas").texto
    r.criar_tarefa("Atrasada de verdade", prazo="2026-10-01")
    resposta = falar("tarefas atrasadas")
    assert "Atrasada de verdade" in resposta.texto and "⚠️" in resposta.texto
    assert "não tem metas" in falar("metas").texto.lower() or "ainda não tem metas" in falar("metas").texto
    r.criar_compromisso("Consulta", HOJE, "15:00", "16:00", local="Clínica")
    assert "Consulta" in falar("agenda hoje").texto
    assert "Nenhum compromisso amanhã" in falar("agenda amanhã").texto


def test_progresso_de_meta(chat):
    falar, _ = chat
    id_ = r.criar_meta("Ler", progresso=10)
    assert falar(f"meta {id_} progresso 60%").aguardando_confirmacao
    falar("sim")
    assert r.obter_meta(id_)["progresso"] == 60
    assert "entre 0 e 100" in falar(f"meta {id_} progresso 150").texto


def test_anotar(chat):
    falar, _ = chat
    falar("anotar Ideias: aprender SQL")
    falar("sim")
    nota = r.listar_anotacoes()[0]
    assert (nota["titulo"], nota["conteudo"]) == ("Ideias", "aprender SQL")


def test_pesquisa_sugestoes_resumo_e_plano(chat):
    falar, _ = chat
    r.criar_tarefa("Comprar caderno", prazo=HOJE, prioridade="alta")
    assert "Comprar caderno" in falar("pesquisar caderno").texto
    assert "Não encontrei nada" in falar("buscar xyzxyz").texto
    assert "sugestões" in falar("o que devo fazer?").texto.lower()
    assert "Pendentes: 1" in falar("resumo do dia").texto
    assert "Sequência sugerida" in falar("planejar meu dia").texto


def test_texto_com_sql_e_tratado_como_texto(chat):
    falar, _ = chat
    falar("criar tarefa '); DROP TABLE tarefas; --")
    falar("sim")
    assert len(r.listar_tarefas()) == 1  # tabela continua existindo


def test_provedor_padrao_e_fallback():
    assert obter_provedor("regras").nome == "regras"
    assert obter_provedor("inexistente").nome == "regras"
