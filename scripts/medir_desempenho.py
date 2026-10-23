"""Mede o desempenho do assistente com volumes diferentes de dados.

Uso (na pasta do projeto, com o ambiente virtual):
    .venv\\Scripts\\python.exe scripts\\medir_desempenho.py

Usa SEMPRE um banco temporário com registros sintéticos de medição, criado e
apagado pelo próprio script. O banco real (dados/assistente.db) não é tocado.
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from assistente import db, pesquisa, planejador, repositorio, sugestoes  # noqa: E402

REPETICOES = 7
HOJE = date(2026, 10, 22)


def medir(funcao, repeticoes: int = REPETICOES) -> float:
    """Mediana em milissegundos."""
    tempos = []
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        funcao()
        tempos.append((time.perf_counter() - inicio) * 1000)
    return statistics.median(tempos)


def popular(quantidade: int) -> None:
    prioridades = ("alta", "media", "baixa")
    with db.conectar() as con:
        agora = "2026-10-22 08:00:00"
        con.executemany(
            "INSERT INTO tarefas (titulo, prioridade, prazo, categoria, status, duracao_min, criado_em, atualizado_em, "
            "concluida_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(f"Registro de medição {i}", prioridades[i % 3], (HOJE + timedelta(days=(i % 40) - 20)).isoformat(),
              f"Cat{i % 8}", "concluida" if i % 4 == 0 else "pendente", 15 + (i % 6) * 15, agora, agora,
              agora if i % 4 == 0 else None) for i in range(quantidade)],
        )
        con.executemany(
            "INSERT INTO metas (titulo, progresso, prazo, criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?)",
            [(f"Meta de medição {i}", i % 101, (HOJE + timedelta(days=i % 30)).isoformat(), agora, agora)
             for i in range(quantidade // 10)],
        )
        con.executemany(
            "INSERT INTO compromissos (titulo, data, hora_inicio, hora_fim, criado_em, atualizado_em) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(f"Compromisso de medição {i}", (HOJE + timedelta(days=i % 30)).isoformat(),
              f"{8 + i % 9:02d}:00", f"{9 + i % 9:02d}:00", agora, agora) for i in range(quantidade // 5)],
        )
        con.executemany(
            "INSERT INTO anotacoes (titulo, conteudo, criado_em, atualizado_em) VALUES (?, ?, ?, ?)",
            [(f"Anotação de medição {i}", "texto " * 20, agora, agora) for i in range(quantidade // 5)],
        )


def renderizar_painel() -> tuple[float, float]:
    """Tempo (ms, mediana) e pico de memória (MB) para desenhar o painel via AppTest."""
    from streamlit.testing.v1 import AppTest

    def script():
        from assistente.ui.paginas import painel
        painel.render()

    def uma_vez():
        at = AppTest.from_function(script, default_timeout=120)
        at.run()
        assert not at.exception

    uma_vez()  # aquecimento
    tracemalloc.start()
    uma_vez()
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return medir(uma_vez, 5), pico / 1024 / 1024


def tempo_de_importacao() -> float:
    """Tempo (s) para um processo novo importar o Streamlit e os módulos do app."""
    codigo = ("import time; t=time.perf_counter(); import streamlit; import assistente.ui.navegacao; "
              "print(time.perf_counter()-t)")
    saida = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True, check=True)
    return float(saida.stdout.strip().splitlines()[-1])


def main() -> None:
    print(f"Python {sys.version.split()[0]} · repetições por medição: {REPETICOES} (mediana)\n")
    importacoes = [tempo_de_importacao() for _ in range(3)]
    print(f"Importação em processo novo (s): {', '.join(f'{x:.2f}' for x in importacoes)}\n")

    cabecalho = f"{'registros':>9} | {'indicadores':>11} | {'pendentes':>9} | {'pesquisa':>8} | " \
                f"{'sugestões':>9} | {'planejador':>10} | {'painel':>8} | {'memória':>8}"
    print(cabecalho)
    print("-" * len(cabecalho))
    for quantidade in (0, 1000, 5000):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as pasta:
            db.definir_caminho_banco(Path(pasta) / "medicao.db")
            popular(quantidade)
            t_ind = medir(lambda: repositorio.indicadores(HOJE))
            t_pend = medir(lambda: repositorio.listar_tarefas("pendentes", hoje=HOJE))
            t_pesq = medir(lambda: pesquisa.pesquisar("medição 12"))
            t_sug = medir(lambda: sugestoes.gerar(HOJE))
            t_plan = medir(lambda: planejador.plano_do_dia(HOJE))
            t_painel, memoria = renderizar_painel()
            print(f"{quantidade:>9} | {t_ind:>8.1f} ms | {t_pend:>6.1f} ms | {t_pesq:>5.1f} ms | "
                  f"{t_sug:>6.1f} ms | {t_plan:>7.1f} ms | {t_painel:>5.0f} ms | {memoria:>5.1f} MB")
            with db.conectar() as con:
                plano = con.execute("EXPLAIN QUERY PLAN SELECT * FROM tarefas WHERE status != 'concluida' "
                                    "AND prazo < ?", (HOJE.isoformat(),)).fetchall()
            db.definir_caminho_banco(None)
    print("\nPlano de consulta (tarefas atrasadas):", "; ".join(str(tuple(linha)[-1]) for linha in plano))


if __name__ == "__main__":
    main()
