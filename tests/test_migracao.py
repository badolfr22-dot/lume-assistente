"""Migração de um banco da versão 1.0 (sem contas) para a versão com contas."""

import sqlite3
from datetime import date

import pytest

from assistente import automacoes, configuracoes, db, notificacoes, planejador, preferencias, repositorio as r

ESQUEMA_V1 = """
CREATE TABLE schema_versao (versao INTEGER NOT NULL);
INSERT INTO schema_versao VALUES (1);
CREATE TABLE tarefas (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, descricao TEXT NOT NULL DEFAULT '',
  prioridade TEXT NOT NULL DEFAULT 'media', prazo TEXT, categoria TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pendente', duracao_min INTEGER NOT NULL DEFAULT 30, exemplo INTEGER NOT NULL DEFAULT 0,
  criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL, concluida_em TEXT);
CREATE INDEX idx_tarefas_status_prazo ON tarefas (status, prazo);
CREATE TABLE metas (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, descricao TEXT NOT NULL DEFAULT '',
  prazo TEXT, progresso INTEGER NOT NULL DEFAULT 0, recorrencia TEXT NOT NULL DEFAULT 'nenhuma',
  exemplo INTEGER NOT NULL DEFAULT 0, criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL);
CREATE TABLE compromissos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL,
  descricao TEXT NOT NULL DEFAULT '', data TEXT NOT NULL, hora_inicio TEXT NOT NULL, hora_fim TEXT NOT NULL,
  local TEXT NOT NULL DEFAULT '', exemplo INTEGER NOT NULL DEFAULT 0, criado_em TEXT NOT NULL,
  atualizado_em TEXT NOT NULL);
CREATE INDEX idx_compromissos_data ON compromissos (data, hora_inicio);
CREATE TABLE anotacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, conteudo TEXT NOT NULL DEFAULT '',
  tags TEXT NOT NULL DEFAULT '', exemplo INTEGER NOT NULL DEFAULT 0, criado_em TEXT NOT NULL,
  atualizado_em TEXT NOT NULL);
CREATE TABLE configuracoes (chave TEXT PRIMARY KEY, valor TEXT NOT NULL, atualizado_em TEXT NOT NULL);
CREATE TABLE preferencias (id INTEGER PRIMARY KEY AUTOINCREMENT, categoria TEXT NOT NULL, chave TEXT NOT NULL,
  valor TEXT NOT NULL, criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL, UNIQUE (categoria, chave));
CREATE TABLE plano_dia (data TEXT NOT NULL, tarefa_id INTEGER NOT NULL REFERENCES tarefas(id) ON DELETE CASCADE,
  posicao INTEGER NOT NULL, PRIMARY KEY (data, tarefa_id));
CREATE TABLE lembretes (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, data_hora TEXT NOT NULL,
  criado_em TEXT NOT NULL, disparado INTEGER NOT NULL DEFAULT 0);
CREATE TABLE notificacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL, titulo TEXT NOT NULL,
  mensagem TEXT NOT NULL DEFAULT '', referencia TEXT NOT NULL UNIQUE, criada_em TEXT NOT NULL,
  lida INTEGER NOT NULL DEFAULT 0, lida_em TEXT);
CREATE INDEX idx_notificacoes_lida ON notificacoes (lida, criada_em);
CREATE TABLE automacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, tipo TEXT NOT NULL,
  parametros TEXT NOT NULL DEFAULT '{}', ativa INTEGER NOT NULL DEFAULT 1, criado_em TEXT NOT NULL,
  ultima_execucao TEXT);
CREATE TABLE automacoes_historico (id INTEGER PRIMARY KEY AUTOINCREMENT,
  automacao_id INTEGER REFERENCES automacoes(id) ON DELETE SET NULL, nome_automacao TEXT NOT NULL,
  executado_em TEXT NOT NULL, situacao TEXT NOT NULL, mensagem TEXT NOT NULL DEFAULT '');
INSERT INTO tarefas (id, titulo, prazo, criado_em, atualizado_em) VALUES (7, 'Tarefa antiga', '2026-10-22', 'x', 'x');
INSERT INTO metas (titulo, progresso, criado_em, atualizado_em) VALUES ('Meta antiga', 40, 'x', 'x');
INSERT INTO compromissos (titulo, data, hora_inicio, hora_fim, criado_em, atualizado_em)
  VALUES ('Compromisso antigo', '2026-10-22', '09:00', '10:00', 'x', 'x');
INSERT INTO anotacoes (titulo, conteudo, criado_em, atualizado_em) VALUES ('Nota antiga', 'conteúdo', 'x', 'x');
INSERT INTO configuracoes VALUES ('tema', '"escuro"', 'x');
INSERT INTO preferencias (categoria, chave, valor, criado_em, atualizado_em)
  VALUES ('outros', 'cor', 'azul', 'x', 'x');
INSERT INTO plano_dia VALUES ('2026-10-22', 7, 0);
INSERT INTO lembretes (titulo, data_hora, criado_em) VALUES ('Lembrete antigo', '2026-10-22 08:00:00', 'x');
INSERT INTO notificacoes (tipo, titulo, referencia, criada_em) VALUES ('prazos', 'Aviso antigo', 'ref:1', 'x');
INSERT INTO automacoes (nome, tipo, criado_em) VALUES ('Automação antiga', 'resumo_diario', 'x');
INSERT INTO automacoes_historico (automacao_id, nome_automacao, executado_em, situacao)
  VALUES (1, 'Automação antiga', 'x', 'ok');
"""


@pytest.mark.somente_sqlite
def test_migra_banco_antigo_sem_perder_nada(tmp_path):
    caminho = tmp_path / "antigo.db"
    with sqlite3.connect(caminho) as con:
        con.executescript(ESQUEMA_V1)
    db.definir_caminho_banco(caminho)

    assert [t["titulo"] for t in r.listar_tarefas()] == ["Tarefa antiga"]
    assert r.obter_tarefa(7)["usuario_id"] == db.USUARIO_LOCAL
    assert [m["progresso"] for m in r.listar_metas()] == [40]
    assert len(r.listar_compromissos()) == len(r.listar_anotacoes()) == 1
    assert configuracoes.obter("tema") == "escuro"
    assert preferencias.listar()[0]["valor"] == "azul"
    assert planejador.ordem_manual(date(2026, 10, 22)) == {7: 0}
    assert len(notificacoes.listar_lembretes()) == 1 and len(notificacoes.listar("todas")) == 1
    assert len(automacoes.listar()) == 1 and len(automacoes.historico()) == 1

    # Backup automático feito antes de migrar
    copias = list((tmp_path / "backups-migracao").glob("antes-da-migracao-v2-*.db"))
    assert len(copias) == 1
    with sqlite3.connect(copias[0]) as con:
        assert con.execute("SELECT titulo FROM tarefas").fetchone()[0] == "Tarefa antiga"

    # Índices novos existem e versão foi atualizada
    with sqlite3.connect(caminho) as con:
        indices = {linha[0] for linha in con.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
        assert "idx_tarefas_usuario_status_prazo" in indices
        assert con.execute("SELECT versao FROM schema_versao").fetchone()[0] == db.VERSAO_ESQUEMA
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []

    # Novos registros continuam numerando depois dos antigos
    assert r.criar_tarefa("Nova depois da migração") > 7
