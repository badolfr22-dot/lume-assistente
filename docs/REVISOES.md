# Revisões técnicas (acessibilidade, segurança e desempenho)

Registro das revisões das etapas 3, 15, 16 e 17 do roteiro. Todos os números abaixo
foram medidos de verdade em 22/10/2026 (Windows 11, Python 3.15.0, Streamlit 1.66.1).

---

## 1. Acessibilidade e usabilidade (etapa 15)

| Item verificado | Como foi verificado | Resultado |
|---|---|---|
| Contraste texto × fundo | `tests/test_acessibilidade.py` calcula a razão WCAG de 13 pares de cores nos temas claro e escuro | 26/26 pares ≥ 4,5:1 (nível AA) |
| Campos e botões identificados | Teste percorre as 12 telas e exige rótulo em todos os campos e texto em todos os botões | 12/12 telas aprovadas |
| Botões só com ícone | Botões "Concluir", "Subir" e "Descer" passaram a ter texto, não só ícone | Corrigido |
| Navegação por teclado | Componentes nativos do Streamlit (Tab/Enter) + contorno de foco visível (`:focus-visible`) | Implementado |
| Mensagens de erro | Erros de validação dizem o campo e o que fazer (ex.: "Data inválida em “Prazo”. Use o formato DD/MM/AAAA.") | Testado |
| Confirmação visual | Mensagem de sucesso + aviso flutuante (toast) após salvar, concluir ou excluir | Testado |
| Estados vazios | Toda lista vazia mostra o que fazer a seguir | Testado nas 12 telas |
| Telas pequenas | Conferido no navegador a 375 px de largura, sem rolagem horizontal | Testado |
| Formulários | Campos obrigatórios marcados com `*`, limite de caracteres e textos de ajuda | Implementado |

**Problemas encontrados no navegador e corrigidos**
- No celular, o título da página ficava escondido atrás da barra superior do Streamlit → espaço do topo aumentado.
- No tema escuro, os botões de filtro inativos e os campos de data/seleção ficavam claros e ilegíveis → CSS ajustado.
- No chat, listas apareciam numa linha só → quebras de linha preservadas.
- Planejador à noite mostrava todas as tarefas como "não couberam" sem explicar → aviso explicativo + opção de planejar o dia inteiro.

**Limitação conhecida:** no emulador de celular do navegador de testes, cliques simulados em
caixas de seleção e interruptores (inclusive os padrão do Streamlit) não mudavam o valor,
enquanto botões, campos de texto e o chat funcionaram. No modo computador os interruptores
funcionam. Falta confirmar num celular de verdade (veja o README, seção "Acessar pelo celular").

---

## 2. Auditoria de segurança (etapa 16)

| Ponto | Situação |
|---|---|
| Validação dos dados | Todas as entradas passam por `assistente/validacao.py` (obrigatório, tamanho, datas, horários, opções, números, remoção de caracteres de controle) |
| SQL injection | 100% das consultas usam parâmetros `?`. Nomes de tabela/coluna vêm só de listas fixas. Um teste varre o código procurando SQL montado com dados externos. Curingas `%` e `_` do LIKE são escapados |
| HTML/script injection (XSS) | Texto do usuário é escapado com `html.escape` antes de entrar em HTML. Teste com `<script>` confirma |
| Segredos e chaves | Nenhuma chave no código (teste automático). Configurações sensíveis só por variável de ambiente; `.env` e `.streamlit/secrets.toml` no `.gitignore`; `.env.example` sem valores secretos |
| Memória controlada | Recusa textos que pareçam senha, token, chave de API, CPF ou cartão |
| Rotas/operações sensíveis | O app é de uso pessoal. Em publicação, a variável `ASSISTENTE_SENHA_ACESSO` ativa uma tela de senha (comparação em tempo constante, bloqueio de 60 s após 5 erros). Exclusões pedem confirmação |
| Tratamento de erros | Erros do banco viram mensagens amigáveis; detalhes técnicos só no log. Produção usa `showErrorDetails = "none"` |
| Dados pessoais | Ficam só em `dados/assistente.db` no computador. Estatísticas de uso do Streamlit desligadas (`gatherUsageStats = false`). Servidor ouve só `localhost` por padrão. Proteção XSRF ativa |
| Comandos externos | O código do app não usa `subprocess`, `os.system`, `eval`, `exec` nem `pickle`. Automações só criam avisos internos |
| CSV exportado | Valores que começam com `=`, `+`, `-` ou `@` recebem `'` na frente para não virarem fórmula no Excel |
| Dependências | `pip-audit`: **No known vulnerabilities found**. `pip list --outdated`: nenhum pacote desatualizado |

**Decisões que dependem de você (não alteradas sem autorização)**
- Publicar o app online exige HTTPS e, idealmente, um login de verdade (ex.: `st.login` com um provedor OIDC). A senha simples é proteção básica para uma pessoa só.
- O app foi feito para **um usuário**. Se várias pessoas forem usar, cada uma precisaria do seu próprio banco.

---

## 3. Desempenho e estabilidade (etapa 17)

Reproduza com:

```bash
.venv\Scripts\python.exe scripts\medir_desempenho.py
```

O script cria um banco temporário com registros sintéticos de medição (apagados no final) e mede a
mediana de 7 execuções. O "painel" é a renderização completa da tela pelo `AppTest` do Streamlit.

### Antes das otimizações

| registros | indicadores | pendentes | pesquisa | sugestões | planejador | painel | memória |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 14,0 ms | 3,8 ms | 15,7 ms | 15,8 ms | 18,5 ms | 310 ms | 1,3 MB |
| 1000 | 21,1 ms | 12,3 ms | 23,1 ms | 32,4 ms | 33,9 ms | 417 ms | 1,7 MB |
| 5000 | 17,6 ms | 26,8 ms | 18,0 ms | 110,5 ms | 53,7 ms | 537 ms | 8,5 MB |

### Gargalos identificados
1. **Uma conexão SQLite nova a cada consulta** (~3 ms cada). Os indicadores fazem 4 consultas → 4 conexões.
2. **Sugestões com custo quadrático**: `t not in atrasadas` comparava dicionários numa lista.

### Depois das otimizações
- Conexão reaproveitada por thread (`assistente/db.py`), descartada automaticamente após erro operacional.
- Conjunto de ids nas sugestões (`assistente/sugestoes.py`).

| registros | indicadores | pendentes | pesquisa | sugestões | planejador | painel | memória |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0,1 ms | 0,0 ms | 0,4 ms | 0,2 ms | 0,2 ms | 222 ms | 1,3 MB |
| 1000 | 0,9 ms | 4,4 ms | 0,8 ms | 6,1 ms | 7,9 ms | 266 ms | 1,7 MB |
| 5000 | 4,0 ms | 24,6 ms | 3,1 ms | 34,8 ms | 33,8 ms | 319 ms | 8,5 MB |

Importação do Streamlit + app em processo novo: 1,28 a 1,45 s (3 medições).

### Outras medidas de estabilidade
- Verificação de avisos e automações limitada a 1 vez por minuto por sessão.
- Configurações lidas uma vez e guardadas na sessão até serem alteradas.
- Falhas temporárias do banco viram mensagem amigável; a próxima operação reabre a conexão (teste `test_recupera_apos_falha_temporaria_do_banco`).
- Erro no meio de uma gravação desfaz tudo (rollback, teste `test_erro_no_meio_da_operacao_desfaz_tudo`).
- Índices em `tarefas(status, prazo)`, `compromissos(data, hora_inicio)` e `notificacoes(lida, criada_em)`. A consulta de atrasadas usa varredura (`SCAN`) por causa do `!=`; com 5000 tarefas ela leva 24,6 ms, então não foi alterada.

### Observação sobre os testes de interface
Na primeira execução da suíte, um teste de tela estourou o limite de 30 s (primeira importação de
bibliotecas pesadas com a pasta no OneDrive). Nas execuções seguintes todos passaram em menos de 2 s
cada. O limite desses testes foi aumentado para 60 s.

---

## 4. Versão com contas e preparação para publicação (23/10/2026)

**O que mudou**
- Tabela `usuarios` e coluna `usuario_id` em todas as tabelas; toda consulta filtra pelo dono dos dados.
- Banco duplo: SQLite no uso pessoal, PostgreSQL online (`ASSISTENTE_DATABASE_URL`), mesmo código SQL.
- Cadastro/login com hash `scrypt`, bloqueio após 5 erros, mensagem única para e-mail ou senha errados,
  código de convite opcional, aviso de privacidade, troca de senha, exclusão da conta com todos os dados.
- Migração automática do banco antigo, com cópia de segurança antes (`dados/backups-migracao/`).
- Script que monta a pasta de publicação e recusa arquivos proibidos ou textos parecidos com segredos.
- A configuração também lê os "Secrets" do Streamlit (`st.secrets`), além das variáveis de ambiente.

**Testes executados de verdade**

| Banco | Resultado |
|---|---|
| SQLite temporário | 230 passed |
| PostgreSQL 18.4 (portátil, local, só para teste) | 225 passed, 5 skipped (específicos do SQLite) |

- Novos testes de isolamento: com duas contas, a segunda não vê, não abre pelo número, não altera e não apaga
  nada da primeira (tarefas, metas, agenda, anotações, preferências, configurações, lembretes, notificações,
  automações, histórico, plano do dia, pesquisa, indicadores, sugestões e exportação).
- Navegador: tela de entrada no celular (375 px), criação de conta de teste, painel e "Minha conta" com o
  PostgreSQL de teste.
- Migração conferida numa cópia do banco real antes de usar; o banco real foi migrado ao reabrir o app,
  com a tarefa existente preservada e o backup automático criado.
- `pip-audit`: nenhuma vulnerabilidade conhecida (incluindo psycopg 3.3.6).
- Sintaxe conferida para Python 3.11 e 3.12 (`ast.parse`); execução testada só no 3.15.

**Observação honesta:** uma execução completa da suíte não terminou em 10 minutos e foi interrompida; nas três
execuções seguintes (SQLite e PostgreSQL) tudo terminou entre 34 s e 97 s. A causa não foi reproduzida.
