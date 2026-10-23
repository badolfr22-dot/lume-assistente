"""Chat do assistente com regras locais (sem API paga, sem modelo de linguagem).

Arquitetura:
- `Provedor` é a interface. `ProvedorRegras` é a implementação local padrão.
- Um provedor de IA futuro (opcional) pode implementar a mesma interface em
  `assistente/ia.py`, mas qualquer alteração de dados continua passando por
  `AcaoPendente` e pela confirmação explícita do usuário.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable, Protocol

from assistente import automacoes, pesquisa, planejador, repositorio, sugestoes
from assistente import validacao as v
from assistente.tempo import hoje as _hoje

LIMITE_MENSAGEM = 500


@dataclass
class AcaoPendente:
    descricao: str
    operacao: str  # chave de OPERACOES (lista fixa)
    argumentos: dict[str, Any]


@dataclass
class EstadoChat:
    pendente: AcaoPendente | None = None
    historico: list[tuple[str, str]] = field(default_factory=list)  # (autor, texto)


@dataclass
class Resposta:
    texto: str
    aguardando_confirmacao: bool = False


class Provedor(Protocol):
    nome: str

    def responder(self, mensagem: str, estado: EstadoChat, hoje: date | None = None) -> Resposta: ...


# Operações que o chat pode executar depois da confirmação. Lista fechada.
OPERACOES: dict[str, Callable[..., Any]] = {
    "criar_tarefa": repositorio.criar_tarefa,
    "concluir_tarefa": repositorio.concluir_tarefa,
    "excluir_tarefa": repositorio.excluir_tarefa,
    "excluir_meta": repositorio.excluir_meta,
    "excluir_compromisso": repositorio.excluir_compromisso,
    "excluir_anotacao": repositorio.excluir_anotacao,
    "atualizar_meta": repositorio.atualizar_meta,
    "criar_anotacao": repositorio.criar_anotacao,
}

AJUDA_GERAL = """Eu entendo comandos simples em português. Exemplos:
• **tarefas pendentes** · **tarefas atrasadas** · **tarefas de hoje**
• **criar tarefa Pagar a conta de luz amanhã prioridade alta**
• **concluir tarefa 3** · **excluir tarefa 3**
• **metas** · **meta 2 progresso 60%**
• **agenda hoje** · **agenda amanhã** · **agenda semana**
• **anotar Ideias: texto da anotação**
• **pesquisar mercado** · **sugestões** · **resumo do dia** · **planejar meu dia**
• **ajuda tarefas** (ou metas, agenda, anotações, planejador, pesquisa, notificações, configurações, memória, automações)

Antes de criar, alterar ou excluir algo, eu sempre peço sua confirmação."""

AJUDA_TOPICOS = {
    "tarefa": "Em **Tarefas** você cadastra título, prioridade, prazo, categoria e duração estimada. "
              "Use os filtros Pendentes, Atrasadas, Para hoje e Concluídas. Cada tarefa pode ser editada, "
              "concluída ou excluída (a exclusão pede confirmação).",
    "meta": "Em **Metas** você cria objetivos com prazo, descrição, recorrência e progresso de 0 a 100%. "
            "Arraste o controle de progresso e clique em Salvar.",
    "agenda": "Em **Agenda** você cadastra compromissos com data, início, fim, local e descrição. "
              "O planejador avisa quando dois compromissos se sobrepõem.",
    "anotac": "Em **Anotações** você cria notas rápidas com etiquetas e pode pesquisar pelo texto.",
    "planej": "O **Planejador** monta uma sequência sugerida para o dia, encaixando as tarefas entre os "
              "compromissos e explicando o motivo de cada posição. Você pode subir ou descer itens. "
              "Ele nunca conclui tarefas sozinho.",
    "pesquis": "A **Pesquisa** procura palavras em tarefas, metas, compromissos e anotações, "
               "com filtros por tipo e por período.",
    "notific": "Em **Notificações** você vê avisos não lidos e anteriores, cria lembretes com data e hora "
               "e marca avisos como lidos. Os avisos aparecem dentro do app enquanto ele está aberto.",
    "config": "Em **Configurações** você muda o nome do assistente, tema claro/escuro, formatos de data e hora, "
              "notificações e sugestões, exporta seus dados e restaura os padrões (sem apagar seus registros).",
    "memor": "Em **Preferências e memória** você salva informações úteis (horários, categorias favoritas...). "
             "Só fica guardado o que você mesmo cadastrar, e você pode apagar tudo quando quiser.",
    "prefer": "Em **Preferências e memória** você salva informações úteis (horários, categorias favoritas...). "
              "Só fica guardado o que você mesmo cadastrar, e você pode apagar tudo quando quiser.",
    "automa": "Em **Automações** você cria regras (avisar atrasadas, prazos próximos, resumo diário, "
              "sugerir prioritárias), ativa, desativa, exclui e vê o histórico de execuções.",
}

SIM = {"sim", "s", "confirmo", "confirmar", "pode", "ok", "isso"}
NAO = {"nao", "n", "cancelar", "cancela", "deixa", "negativo"}


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, mantendo o mesmo comprimento do texto em NFC."""
    decomposto = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in decomposto if unicodedata.category(c) != "Mn")
    return sem_acento.lower()


def _formatar_tarefa(t: dict[str, Any], hoje: date) -> str:
    prazo = date.fromisoformat(t["prazo"]).strftime("%d/%m") if t["prazo"] else "sem prazo"
    marca = " ⚠️ atrasada" if repositorio.esta_atrasada(t, hoje) else ""
    feito = "✅ " if t["status"] == "concluida" else ""
    return f"• {feito}#{t['id']} {t['titulo']} — {prazo}, prioridade {planejador.NOME_PRIORIDADE[t['prioridade']]}{marca}"


def _extrair_data(texto_norm: str, hoje: date) -> tuple[str | None, tuple[int, int] | None]:
    """Procura 'hoje', 'amanhã' ou 'dd/mm[/aaaa]'. Devolve (data ISO, trecho encontrado)."""
    m = re.search(r"\b(?:para |ate |em |no dia )?(hoje|amanha|depois de amanha)\b", texto_norm)
    if m:
        dias = {"hoje": 0, "amanha": 1, "depois de amanha": 2}[m.group(1)]
        return (hoje + timedelta(days=dias)).isoformat(), m.span()
    m = re.search(r"\b(?:para |ate |em |no dia )?(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b", texto_norm)
    if m:
        ano = int(m.group(3)) if m.group(3) else hoje.year
        try:
            d = date(ano, int(m.group(2)), int(m.group(1)))
        except ValueError:
            raise v.ErroValidacao("A data informada não existe.") from None
        if not m.group(3) and d < hoje:
            d = date(ano + 1, d.month, d.day)
        return d.isoformat(), m.span()
    return None, None


class ProvedorRegras:
    """Interpreta comandos com expressões regulares. Não inventa dados."""

    nome = "regras"

    def responder(self, mensagem: str, estado: EstadoChat, hoje: date | None = None) -> Resposta:
        hoje = hoje or _hoje()
        original = unicodedata.normalize("NFC", (mensagem or "").strip())
        if not original:
            return Resposta("Digite uma mensagem. Se quiser, escreva **ajuda**.")
        if len(original) > LIMITE_MENSAGEM:
            return Resposta(f"A mensagem é muito longa (máximo de {LIMITE_MENSAGEM} caracteres).")
        texto = normalizar(original)
        palavras = re.sub(r"[^\w\s]", " ", texto).split()

        # 1) Confirmação de ação pendente
        if estado.pendente is not None:
            if palavras and palavras[0] in SIM and len(palavras) <= 3:
                return self._executar_pendente(estado)
            if palavras and palavras[0] in NAO and len(palavras) <= 3:
                estado.pendente = None
                return Resposta("Tudo bem, cancelei. Nada foi alterado.")
            estado.pendente = None
            aviso = "A ação que aguardava confirmação foi cancelada (nada foi alterado).\n\n"
            resposta = self.responder(original, estado, hoje)
            return Resposta(aviso + resposta.texto, resposta.aguardando_confirmacao)

        try:
            return self._interpretar(original, texto, estado, hoje)
        except v.ErroValidacao as erro:
            return Resposta(f"Não consegui fazer isso: {erro}")

    # ------------------------------------------------------------------
    def _interpretar(self, original: str, texto: str, estado: EstadoChat, hoje: date) -> Resposta:
        if re.fullmatch(r"(oi|ola|bom dia|boa tarde|boa noite|e ai)[!. ]*", texto):
            return Resposta("Olá! Posso consultar suas tarefas, metas e agenda, criar itens ou dar sugestões. "
                            "Escreva **ajuda** para ver exemplos.")

        m = re.match(r"(ajuda|como usar|como funciona|como)\b\s*(.*)", texto)
        if m or texto in ("?", "o que voce faz", "o que voce faz?"):
            topico = m.group(2) if m else ""
            for chave, explicacao in AJUDA_TOPICOS.items():
                if chave in topico:
                    return Resposta(explicacao)
            return Resposta(AJUDA_GERAL)

        # Criar tarefa
        m = re.match(r"(criar|crie|nova|adicionar|adicione|cadastrar|cadastre)\s+(uma\s+)?tarefa\s*:?\s*(.*)", texto)
        if m:
            return self._preparar_criar_tarefa(original, texto, m.start(3), estado, hoje)

        # Criar anotação
        m = re.match(r"(anotar|anote|nova anotacao|criar anotacao)\s*:?\s*(.*)", texto)
        if m:
            corpo = original[m.start(2):].strip()
            if not corpo:
                return Resposta("Diga o que devo anotar. Exemplo: **anotar Ideias: comprar caderno**")
            titulo, _, conteudo = corpo.partition(":")
            titulo, conteudo = titulo.strip(), conteudo.strip()
            v.texto_obrigatorio(titulo, "Título", v.LIMITE_TITULO)
            estado.pendente = AcaoPendente(f"criar a anotação “{titulo}”", "criar_anotacao",
                                           {"titulo": titulo, "conteudo": conteudo})
            return Resposta(f"Confirma criar a anotação **{titulo}**? Responda **sim** ou **não**.", True)

        # Concluir / excluir por número
        m = re.match(r"(concluir|conclua|finalizar|marcar como feita)\s+(a\s+)?tarefa\s+#?(\d+)", texto)
        if m:
            tarefa = repositorio.obter_tarefa(int(m.group(3)))
            if not tarefa:
                return Resposta(f"Não encontrei a tarefa #{m.group(3)}. Escreva **tarefas** para ver os números.")
            if tarefa["status"] == "concluida":
                return Resposta(f"A tarefa #{tarefa['id']} já está concluída.")
            estado.pendente = AcaoPendente(f"concluir a tarefa “{tarefa['titulo']}”", "concluir_tarefa",
                                           {"id_": tarefa["id"]})
            return Resposta(f"Confirma marcar **#{tarefa['id']} {tarefa['titulo']}** como concluída? "
                            "Responda **sim** ou **não**.", True)

        m = re.match(r"(excluir|exclua|apagar|apague|remover|remova|deletar)\s+(a\s+|o\s+)?"
                     r"(tarefa|meta|compromisso|anotacao)\s+#?(\d+)", texto)
        if m:
            return self._preparar_exclusao(m.group(3), int(m.group(4)), estado)
        if re.match(r"(excluir|apagar|remover|deletar)\b", texto):
            return Resposta("Para excluir, diga o tipo e o número. Exemplo: **excluir tarefa 3**. "
                            "Escreva **tarefas** para ver os números.")

        # Progresso de meta
        m = re.match(r"(?:atualizar\s+)?meta\s+#?(\d+)\s+(?:progresso\s+|para\s+|em\s+)?(\d{1,3})\s*%?", texto)
        if m:
            meta = repositorio.obter_meta(int(m.group(1)))
            if not meta:
                return Resposta(f"Não encontrei a meta #{m.group(1)}.")
            progresso = v.inteiro(m.group(2), "Progresso", 0, 100)
            estado.pendente = AcaoPendente(f"mudar o progresso da meta “{meta['titulo']}” para {progresso}%",
                                           "atualizar_meta", {"id_": meta["id"], "progresso": progresso})
            return Resposta(f"Confirma mudar o progresso de **{meta['titulo']}** de {meta['progresso']}% "
                            f"para {progresso}%? Responda **sim** ou **não**.", True)

        m = re.match(r"(pesquisar|pesquise|buscar|busque|procurar|procure|encontrar)\s+(por\s+)?(.*)", texto)
        if m:
            termo = original[m.start(3):].strip()
            resultados = pesquisa.pesquisar(termo)
            if pesquisa.total(resultados) == 0:
                return Resposta(f"Não encontrei nada com “{termo}”.")
            partes = []
            for tipo, itens in resultados.items():
                if itens:
                    nomes = ", ".join(f"#{i['id']} {i['titulo']}" for i in itens[:5])
                    partes.append(f"• **{pesquisa.TIPOS[tipo]}** ({len(itens)}): {nomes}")
            return Resposta(f"Resultados para “{termo}”:\n" + "\n".join(partes))

        # Consultas
        if re.search(r"\b(sugest(oes|ao)|o que (devo|eu devo) fazer|por onde (comeco|comecar)|prioridades?)\b", texto):
            lista = sugestoes.gerar(hoje)
            if not lista:
                return Resposta("Não tenho sugestões agora (elas podem estar desativadas nas Configurações).")
            return Resposta("Minhas sugestões, com base nos seus dados:\n" +
                            "\n".join(f"• {s.icone} {s.titulo} _({s.motivo})_" for s in lista))
        if re.search(r"\bresumo\b", texto):
            return Resposta("Resumo do dia: " + automacoes.resumo_do_dia(hoje))
        if re.search(r"\b(planejar|planeje|plano|planejamento)\b", texto):
            plano = planejador.plano_do_dia(hoje)
            if not plano.itens:
                return Resposta("Não há tarefas nem compromissos para planejar hoje.")
            linhas = [f"• {i.inicio}–{i.fim} {'📅' if i.tipo == 'compromisso' else '✔️'} {i.titulo}"
                      for i in plano.itens]
            extra = f"\n\n{len(plano.nao_couberam)} tarefa(s) não couberam no horário de hoje." if plano.nao_couberam else ""
            return Resposta("Sequência sugerida para hoje (veja os motivos no **Planejador**):\n"
                            + "\n".join(linhas) + extra)
        if re.search(r"\btarefas?\b", texto):
            return self._listar_tarefas(texto, hoje)
        if re.search(r"\bmetas?\b", texto):
            metas = repositorio.listar_metas()
            if not metas:
                return Resposta("Você ainda não tem metas cadastradas. Crie a primeira na página **Metas**.")
            linhas = [f"• #{m['id']} {m['titulo']} — {m['progresso']}%" +
                      (f", prazo {date.fromisoformat(m['prazo']).strftime('%d/%m/%Y')}" if m["prazo"] else "")
                      for m in metas[:15]]
            return Resposta("Suas metas:\n" + "\n".join(linhas))
        if re.search(r"\b(agenda|compromissos?|reunio(es|ao))\b", texto):
            return self._listar_agenda(texto, hoje)

        return Resposta("Desculpe, não entendi esse comando. Eu funciono com regras simples, "
                        "não com inteligência artificial. Escreva **ajuda** para ver o que sei fazer.")

    # ------------------------------------------------------------------
    def _preparar_criar_tarefa(self, original: str, texto: str, inicio: int, estado: EstadoChat,
                               hoje: date) -> Resposta:
        resto_norm = texto[inicio:]
        resto = original[inicio:]
        prioridade = "media"
        m = re.search(r"\s*(com\s+)?prioridade\s+(alta|media|baixa)\b", resto_norm)
        if m:
            prioridade = m.group(2)
            resto_norm = resto_norm[:m.start()] + resto_norm[m.end():]
            resto = resto[:m.start()] + resto[m.end():]
        prazo, trecho = _extrair_data(resto_norm, hoje)
        if trecho:
            resto = resto[:trecho[0]] + resto[trecho[1]:]
        titulo = re.sub(r"\s+", " ", resto).strip(" :-,")
        if not titulo:
            return Resposta("Qual é o título da tarefa? Exemplo: **criar tarefa Estudar Python amanhã**")
        v.texto_obrigatorio(titulo, "Título")
        argumentos = {"titulo": titulo, "prioridade": prioridade, "prazo": prazo}
        prazo_txt = date.fromisoformat(prazo).strftime("%d/%m/%Y") if prazo else "sem prazo"
        estado.pendente = AcaoPendente(f"criar a tarefa “{titulo}”", "criar_tarefa", argumentos)
        return Resposta(f"Confirma criar a tarefa **{titulo}** ({prazo_txt}, prioridade "
                        f"{planejador.NOME_PRIORIDADE[prioridade]})? Responda **sim** ou **não**.", True)

    def _preparar_exclusao(self, tipo: str, id_: int, estado: EstadoChat) -> Resposta:
        busca = {"tarefa": repositorio.obter_tarefa, "meta": repositorio.obter_meta,
                 "compromisso": repositorio.obter_compromisso, "anotacao": repositorio.obter_anotacao}
        nome = {"tarefa": "a tarefa", "meta": "a meta", "compromisso": "o compromisso", "anotacao": "a anotação"}
        item = busca[tipo](id_)
        if not item:
            return Resposta(f"Não encontrei {nome[tipo]} #{id_}.")
        estado.pendente = AcaoPendente(f"excluir {nome[tipo]} “{item['titulo']}”", f"excluir_{tipo}", {"id_": id_})
        return Resposta(f"⚠️ Confirma **excluir** {nome[tipo]} **#{id_} {item['titulo']}**? "
                        "Essa ação não pode ser desfeita. Responda **sim** ou **não**.", True)

    def _executar_pendente(self, estado: EstadoChat) -> Resposta:
        acao = estado.pendente
        estado.pendente = None
        assert acao is not None
        operacao = OPERACOES.get(acao.operacao)
        if operacao is None:  # nunca deve acontecer: lista fechada
            return Resposta("Operação não permitida.")
        try:
            operacao(**acao.argumentos)
        except v.ErroValidacao as erro:
            return Resposta(f"Não foi possível {acao.descricao}: {erro}")
        return Resposta(f"Pronto! Consegui {acao.descricao}. ✅")

    def _listar_tarefas(self, texto: str, hoje: date) -> Resposta:
        if "atrasad" in texto:
            filtro, nome = "atrasadas", "atrasadas"
        elif "conclu" in texto or "feitas" in texto:
            filtro, nome = "concluidas", "concluídas"
        elif "hoje" in texto:
            filtro, nome = "hoje", "para hoje"
        elif "todas" in texto:
            filtro, nome = "todas", ""
        else:
            filtro, nome = "pendentes", "pendentes"
        tarefas = repositorio.listar_tarefas(filtro, hoje=hoje)
        if not tarefas:
            return Resposta(f"Você não tem tarefas {nome}.".replace("  ", " "))
        linhas = [_formatar_tarefa(t, hoje) for t in tarefas[:15]]
        extra = f"\n…e mais {len(tarefas) - 15}." if len(tarefas) > 15 else ""
        return Resposta(f"Tarefas {nome} ({len(tarefas)}):\n".replace("  ", " ") + "\n".join(linhas) + extra)

    def _listar_agenda(self, texto: str, hoje: date) -> Resposta:
        if "amanha" in texto:
            inicio = fim = hoje + timedelta(days=1)
            nome = "amanhã"
        elif "semana" in texto or "proxim" in texto:
            inicio, fim = hoje, hoje + timedelta(days=7)
            nome = "nos próximos 7 dias"
        else:
            inicio = fim = hoje
            nome = "hoje"
        itens = repositorio.listar_compromissos(inicio, fim)
        if not itens:
            return Resposta(f"Nenhum compromisso {nome}.")
        linhas = [f"• #{c['id']} {date.fromisoformat(c['data']).strftime('%d/%m')} {c['hora_inicio']}–{c['hora_fim']} "
                  f"{c['titulo']}" + (f" ({c['local']})" if c["local"] else "") for c in itens]
        return Resposta(f"Compromissos {nome}:\n" + "\n".join(linhas))
