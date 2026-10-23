from datetime import date, datetime

from assistente import planejador as p, preferencias, repositorio as r

DIA = date(2026, 10, 22)


def tarefa(id_, titulo, prioridade="media", prazo=None, duracao=30, status="pendente"):
    return {"id": id_, "titulo": titulo, "prioridade": prioridade, "prazo": prazo,
            "duracao_min": duracao, "status": status}


def compromisso(id_, inicio, fim, data="2026-10-22", titulo="Reunião"):
    return {"id": id_, "titulo": titulo, "data": data, "hora_inicio": inicio, "hora_fim": fim}


# --- Ordenação ------------------------------------------------------------------

def test_atrasada_vem_antes_de_prioridade_alta():
    tarefas = [tarefa(1, "Alta hoje", "alta", "2026-10-22"), tarefa(2, "Baixa atrasada", "baixa", "2026-10-20")]
    assert [t["id"] for t in p.ordenar_tarefas(tarefas, DIA)] == [2, 1]


def test_prazo_mais_proximo_e_sem_prazo_por_ultimo():
    tarefas = [tarefa(1, "Sem prazo", "alta"), tarefa(2, "Depois", prazo="2026-10-24"),
               tarefa(3, "Hoje", prazo="2026-10-22")]
    assert [t["id"] for t in p.ordenar_tarefas(tarefas, DIA)] == [3, 2, 1]


def test_mesmo_prazo_ordena_por_prioridade_e_depois_duracao():
    tarefas = [tarefa(1, "Média longa", "media", "2026-10-22", 90), tarefa(2, "Média curta", "media", "2026-10-22", 15),
               tarefa(3, "Alta", "alta", "2026-10-22", 120)]
    assert [t["id"] for t in p.ordenar_tarefas(tarefas, DIA)] == [3, 2, 1]


def test_ordem_manual_tem_precedencia():
    tarefas = [tarefa(1, "A", "alta", "2026-10-20"), tarefa(2, "B", "baixa")]
    assert [t["id"] for t in p.ordenar_tarefas(tarefas, DIA, {2: 0})] == [2, 1]


# --- Conflitos ----------------------------------------------------------------------

def test_detecta_conflito_de_horario():
    a = compromisso(1, "09:00", "10:00")
    b = compromisso(2, "09:30", "11:00")
    c = compromisso(3, "11:00", "12:00")  # encosta, mas não sobrepõe
    conflitos = p.encontrar_conflitos([a, b, c])
    assert [(x["id"], y["id"]) for x, y in conflitos] == [(1, 2)]


def test_sem_conflito_em_dias_diferentes():
    assert p.encontrar_conflitos([compromisso(1, "09:00", "10:00"),
                                  compromisso(2, "09:00", "10:00", data="2026-10-23")]) == []


# --- Montagem do plano -----------------------------------------------------------

def test_tarefas_desviam_dos_compromissos():
    plano = p.montar_plano([tarefa(1, "T1", duracao=60), tarefa(2, "T2", duracao=30)],
                           [compromisso(10, "08:30", "09:30")], DIA, inicio="08:00", fim="18:00")
    horarios = {(i.tipo, i.id): (i.inicio, i.fim) for i in plano.itens}
    assert horarios[("compromisso", 10)] == ("08:30", "09:30")
    # T2 (mais curta) vem primeiro e cabe antes do compromisso; T1 (60 min) não cabe e vai para depois.
    assert horarios[("tarefa", 2)] == ("08:00", "08:30")
    assert horarios[("tarefa", 1)] == ("09:30", "10:30")
    assert [i.id for i in plano.itens] == [2, 10, 1]


def test_tarefa_que_nao_cabe_vai_para_lista_separada():
    plano = p.montar_plano([tarefa(1, "Longa", duracao=600)], [], DIA, inicio="08:00", fim="12:00")
    assert [t["id"] for t in plano.nao_couberam] == [1]
    assert not [i for i in plano.itens if i.tipo == "tarefa"]


def test_plano_comeca_agora_quando_e_hoje():
    plano = p.montar_plano([tarefa(1, "T")], [], DIA, agora=datetime(2026, 10, 22, 13, 2))
    assert plano.itens[0].inicio == "13:05"


def test_explicacao_e_atrasadas():
    plano = p.montar_plano([tarefa(1, "Velha", "alta", "2026-10-19", 15)], [], DIA)
    item = plano.itens[0]
    assert item.atrasada
    assert "atrasada há 3 dia(s)" in item.explicacao
    assert "prioridade alta" in item.explicacao
    assert "curta" in item.explicacao
    assert [t["id"] for t in plano.atrasadas] == [1]


def test_planejador_nao_altera_dados():
    id_ = r.criar_tarefa("Não mexer", prazo=DIA)
    c = r.criar_compromisso("Fixo", DIA, "09:00", "10:00")
    antes_t, antes_c = r.obter_tarefa(id_), r.obter_compromisso(c)
    p.plano_do_dia(DIA)
    assert r.obter_tarefa(id_) == antes_t
    assert r.obter_compromisso(c) == antes_c


# --- Integração com banco ----------------------------------------------------------

def test_reorganizacao_manual_persistida():
    a = r.criar_tarefa("A", prioridade="alta", prazo=DIA)
    b = r.criar_tarefa("B", prioridade="baixa", prazo=DIA)
    plano = p.plano_do_dia(DIA)
    assert plano.ordem_tarefas == [a, b]
    p.mover(DIA, plano.ordem_tarefas, b, -1)
    assert p.plano_do_dia(DIA).ordem_tarefas == [b, a]
    p.limpar_ordem(DIA)
    assert p.plano_do_dia(DIA).ordem_tarefas == [a, b]


def test_usa_horarios_das_preferencias():
    preferencias.salvar("horarios", "inicio do dia", "09:30")
    r.criar_tarefa("A", prazo=DIA)
    plano = p.plano_do_dia(DIA)
    assert plano.itens[0].inicio == "09:30"


def test_progresso_do_dia():
    a = r.criar_tarefa("A", prazo=DIA)
    r.criar_tarefa("B", prazo=DIA)
    r.concluir_tarefa(a)
    feitas, total = p.progresso_do_dia(date.today())
    # A foi concluída hoje (data real do computador)
    assert feitas == 1
    assert total >= 1
