# Lume — Assistente pessoal digital de produtividade

Assistente pessoal feito em **Python + Streamlit + SQLite** para organizar tarefas, metas, agenda e
anotações, com painel interativo, sugestões automáticas, planejador do dia, chat por regras locais,
lembretes, automações e configurações. Funciona no navegador do computador e se adapta a telas de celular.

Funciona de dois jeitos:

- **Uso pessoal (padrão):** roda no seu computador, com SQLite, sem login, de graça e sem enviar dados para fora.
- **Online, para várias pessoas:** cada pessoa cria sua conta e só vê os próprios dados. Usa PostgreSQL.
  O passo a passo para publicar está em **[docs/PUBLICACAO.md](docs/PUBLICACAO.md)** (nada é publicado sozinho).

---

## 1. Objetivo e funcionalidades

| Área | O que faz |
|---|---|
| **Painel** | Resumo do dia, indicadores (pendentes, concluídas hoje, atrasadas, compromissos), barras de progresso, tarefas pendentes/concluídas, agenda dos próximos 7 dias, metas, anotações rápidas e **Sugestões inteligentes** |
| **Tarefas** | Criar, editar, concluir, reabrir e excluir. Prioridade, prazo, categoria, status e duração estimada. Filtros: pendentes, atrasadas, para hoje, concluídas, todas + filtro por categoria |
| **Metas** | Prazo, descrição, recorrência e progresso de 0 a 100% |
| **Agenda** | Compromissos com data, início, fim, local e descrição. Aviso de conflito de horário |
| **Anotações** | Criar, editar, pesquisar e excluir, com etiquetas |
| **Pesquisa** | Busca global por palavra em tudo, resultados separados por tipo, filtros por tipo e período, botão **Abrir** |
| **Planejador do dia** | Ordena por atraso, prazo, prioridade e duração; encaixa as tarefas entre os compromissos; explica cada posição; permite subir/descer itens e ajustar a duração. Nunca conclui tarefas nem altera compromissos |
| **Conversa** | Chat por **regras locais** (não é inteligência artificial). Consulta, cria, conclui e exclui itens **sempre pedindo confirmação** |
| **Notificações** | Lembretes com data e hora, avisos de prazo e de compromisso, lidas/não lidas, sem duplicar |
| **Automações** | Regras configuráveis (avisar atrasadas, prazos próximos, resumo diário, sugerir prioritárias), ativar/desativar/excluir, executar agora, histórico |
| **Preferências e memória** | Informações que **você** decide guardar (horários, categorias favoritas...). Recusa senhas, tokens, CPF e cartões. Botão para limpar tudo |
| **Configurações** | Nome do assistente, seu nome, tema claro/escuro, formatos de data e hora, notificações, sugestões, exportar dados (JSON/CSV), dados de exemplo removíveis, restaurar padrões |
| **Contas (modo online)** | Cadastro com aviso de privacidade e código de convite opcional, login, sair, trocar nome e senha, excluir a conta com todos os dados. Senhas guardadas só como hash `scrypt`; bloqueio de 5 min após 5 senhas erradas |

## 2. Tecnologias e bibliotecas

- **Python 3.15** (testado com 3.15.0)
- **Streamlit 1.66.1** — interface web (instala junto pandas, pyarrow, numpy etc.)
- **SQLite** — banco de dados local (já vem com o Python)
- **PostgreSQL + psycopg 3.3.6** — banco online, usado só no modo publicado (testado com PostgreSQL 18.4)
- **pytest 9.1.1** — testes automatizados
- **pip-audit 2.10.1** — verificação de vulnerabilidades das dependências

Todas são gratuitas e de código aberto.

## 3. Estrutura de pastas

```
projetinho/
├── app.py                      # Ponto de entrada: streamlit run app.py
├── assistente/                 # Código do aplicativo
│   ├── config.py               # Configuração por variáveis de ambiente (dev/produção)
│   ├── db.py                   # Acesso centralizado ao SQLite e criação das tabelas
│   ├── validacao.py            # Validação dos dados digitados
│   ├── tempo.py                # Datas, horários e formatos
│   ├── repositorio.py          # CRUD de tarefas, metas, compromissos e anotações + indicadores
│   ├── sugestoes.py            # Sugestões inteligentes (regras locais)
│   ├── pesquisa.py             # Pesquisa global
│   ├── planejador.py           # Planejador diário
│   ├── chat.py / ia.py         # Chat por regras + ponto de extensão para IA opcional futura
│   ├── preferencias.py         # Memória controlada
│   ├── configuracoes.py        # Configurações do app
│   ├── notificacoes.py         # Lembretes e notificações
│   ├── automacoes.py           # Automações e histórico
│   ├── exportacao.py           # Exportar dados (JSON/CSV)
│   ├── demo.py                 # Dados de exemplo (marcados e removíveis)
│   ├── usuarios.py             # Contas: cadastro, login, senha, exclusão
│   ├── acesso.py               # Senha única opcional (modo sem contas)
│   ├── saude.py                # Verificação de saúde
│   └── ui/                     # Interface: estilos, componentes, navegação e páginas
├── scripts/
│   ├── backup.py               # Backup e restauração do banco (SQLite)
│   ├── preparar_publicacao.py  # Monta a pasta publicacao/ só com arquivos seguros
│   ├── redefinir_senha.py      # Administrador: senha temporária para uma conta
│   ├── verificar_saude.py      # Health check
│   └── medir_desempenho.py     # Medições de desempenho
├── tests/                      # Testes automatizados (pytest)
├── docs/REVISOES.md            # Revisões de acessibilidade, segurança e desempenho
├── docs/PUBLICACAO.md          # Guia para publicar (GitHub + Streamlit Cloud + Neon)
├── .streamlit/config.toml      # Configuração do Streamlit (desenvolvimento)
├── .streamlit/config.producao.toml  # Referência para produção
├── requirements.txt            # Dependência principal (versão fixa)
├── requirements-dev.txt        # + ferramentas de teste e auditoria
├── requirements-lock.txt       # Todas as versões testadas (ambiente idêntico)
├── .env.example                # Exemplo de variáveis de ambiente (sem segredos)
├── pytest.ini
└── dados/assistente.db         # Seu banco (criado na primeira execução; não publicar)
```

## 4. Requisitos

- Windows 10 ou 11
- Python 3.15 instalado (o comando `py` deve funcionar no PowerShell)
- Cerca de 400 MB livres para o ambiente virtual
- Internet só para instalar as bibliotecas na primeira vez

## 5. Instalação passo a passo (Windows / PowerShell)

Abra o PowerShell **na pasta do projeto** e rode um comando por vez:

```bash
py -m venv .venv
```

```bash
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

> Se quiser exatamente as mesmas versões testadas, use `requirements-lock.txt` no lugar de `requirements-dev.txt`
> (e instale `pytest` à parte, se for rodar os testes).

Não é preciso "ativar" o ambiente virtual: os comandos acima chamam o Python do `.venv` diretamente,
o que evita o erro de política de execução de scripts do PowerShell.

## 6. Iniciar a aplicação

```bash
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Depois abra **http://localhost:8501** no navegador. Para parar, pressione `Ctrl + C` no PowerShell.

### Acessar pelo celular (mesma rede Wi-Fi)

1. No computador, rode:

   ```bash
   .\.venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0
   ```

2. Descubra o IP do computador com `ipconfig` (linha "Endereço IPv4", algo como `192.168.0.15`).
3. No celular, abra `http://SEU-IP:8501`.
4. Se o Windows perguntar sobre o Firewall, permita **apenas em redes privadas**.

Atenção: assim, qualquer pessoa na mesma rede consegue abrir o app. Para proteger, defina uma senha
antes (veja a seção 11) e use isso só em redes de confiança. O layout para celular foi conferido no
navegador em 375 px de largura; ainda **não foi testado num aparelho real** (veja a seção 12).

## 7. Banco de dados

- Arquivo: `dados/assistente.db` (SQLite), criado automaticamente na primeira execução.
- As tabelas são criadas com `CREATE TABLE IF NOT EXISTS`: iniciar o app **nunca apaga dados**.
- Para usar outro arquivo, defina `ASSISTENTE_BANCO` (veja `.env.example`).
- Tabelas: `usuarios`, `tarefas`, `metas`, `compromissos`, `anotacoes`, `configuracoes`, `preferencias`,
  `plano_dia`, `lembretes`, `notificacoes`, `automacoes`, `automacoes_historico`, `schema_versao`.
  Todo registro tem `usuario_id`; no uso pessoal o dono é sempre o usuário local (id 1).
- **Migração automática:** um banco da versão anterior (sem contas) é convertido sozinho na primeira abertura,
  sem perder nada. Antes disso, uma cópia é salva em `dados/backups-migracao/`.
- **Online:** defina `ASSISTENTE_DATABASE_URL` com a connection string do PostgreSQL (veja `docs/PUBLICACAO.md`).

## 8. Como usar cada funcionalidade

- **Primeiros passos:** em *Configurações → Dados de exemplo* você pode carregar exemplos para conhecer o app.
  Eles aparecem com "[Exemplo]" e são removidos com *Remover exemplos* (seus dados reais ficam).
- **Tarefas:** *Nova tarefa* → preencha o título (obrigatório) e o resto → *Adicionar tarefa*. Em cada tarefa:
  *Concluir*, *Editar*, *Excluir* (pede confirmação). Use os filtros no topo.
- **Metas:** *Nova meta*; para atualizar o progresso, mova o controle e clique em *Salvar*.
- **Agenda:** *Novo compromisso* com data, início e fim. Conflitos aparecem em amarelo.
- **Anotações:** crie pela página ou pelo painel; pesquise no campo de busca.
- **Pesquisa:** digite pelo menos 2 letras, escolha tipos e, se quiser, um período. *Abrir* leva ao item.
- **Planejador:** escolha o dia. Use *Subir/Descer* para mudar a ordem e *Duração* para ajustar o tempo.
  *Voltar à ordem automática* desfaz a ordem manual. Para mudar o horário do dia, salve em
  *Preferências e memória → Horários* os itens `inicio do dia` e `fim do dia` (formato HH:MM).
- **Conversa:** escreva `ajuda`. Exemplos: `tarefas atrasadas`, `criar tarefa Pagar luz amanhã prioridade alta`,
  `concluir tarefa 3`, `excluir tarefa 3`, `meta 2 progresso 60%`, `agenda amanhã`, `anotar Ideias: texto`,
  `pesquisar mercado`, `sugestões`, `resumo do dia`, `planejar meu dia`. Responda **sim** ou **não** às confirmações.
- **Notificações:** os avisos aparecem enquanto o app está aberto (verificação a cada minuto ou pelo botão
  *Verificar novos avisos agora*). Crie lembretes na aba *Lembretes*. Escolha os tipos em *Configurações*.
- **Automações:** *Nova automação* → escolha o tipo e os parâmetros. As ativas rodam uma vez por dia ao abrir
  o app; *Executar agora* roda na hora. O histórico mostra cada execução (ok, sem ação ou erro).
- **Preferências e memória:** salve, edite, exclua ou limpe tudo. Nada é guardado sem você digitar.
- **Configurações:** altere e clique em *Salvar configurações*. *Restaurar configurações padrão* não apaga seus registros.
- **Contas (modo online):** na tela inicial, *Criar conta* (nome, e-mail, senha com letras e números, código de
  convite se houver, e aceite do aviso de privacidade) ou *Entrar*. Em *Configurações → Minha conta*: trocar nome,
  trocar senha e excluir a conta. *Sair* fica na barra lateral.

## 9. Testes

```bash
.\.venv\Scripts\python.exe -m pytest
```

Os testes usam um banco temporário e **nunca tocam no seu banco real**. Eles cobrem: CRUD e validação,
persistência, filtros, indicadores, pesquisa, sugestões, planejador (ordenação e conflitos), chat,
preferências, configurações, notificações, automações, exportação, exemplos, segurança (SQL injection,
XSS, segredos), acessibilidade (contraste e rótulos), backup, health check e todas as 12 telas
(via `streamlit.testing`), além de contas, **isolamento entre usuários** (uma pessoa nunca vê, altera nem
apaga dados de outra), migração do banco antigo e a pasta de publicação.

Para rodar a mesma suíte contra um PostgreSQL de teste (descartável, as tabelas são esvaziadas):

```bash
$env:ASSISTENTE_TESTE_PG_URL = "postgresql://usuario@localhost:5432/banco_de_teste"
```

```bash
.\.venv\Scripts\python.exe -m pytest
```

Outras verificações:

```bash
.\.venv\Scripts\python.exe -m pip_audit
```

```bash
.\.venv\Scripts\python.exe scripts\medir_desempenho.py
```

```bash
.\.venv\Scripts\python.exe scripts\verificar_saude.py --url http://localhost:8501
```

## 10. Erros comuns

| Problema | Solução |
|---|---|
| `py` não é reconhecido | Instale o Python pelo site oficial ou pela Microsoft Store e reabra o PowerShell |
| "a execução de scripts foi desabilitada" ao ativar o venv | Não ative: use os comandos com `.\.venv\Scripts\python.exe` como neste README |
| `No module named streamlit` | Rode a instalação da seção 5 de novo |
| Porta 8501 ocupada | `.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502` |
| "O banco de dados está indisponível no momento" | Outro programa (ex.: sincronização do OneDrive) pode estar usando o arquivo. Aguarde e tente de novo; se persistir, feche e abra o app |
| O celular não abre o app | Confirme a mesma rede Wi-Fi, o `--server.address 0.0.0.0` e a permissão do Firewall |
| Página em branco depois de atualizar o código | Pare com `Ctrl + C` e inicie de novo |

## 11. Segurança, dados pessoais e chaves de API

- Seus dados ficam em `dados/assistente.db`, no seu computador. **Não publique** essa pasta.
- Esta versão **não usa nenhuma chave de API** nem serviço pago.
- Variáveis sensíveis vão no arquivo `.env` (copie de `.env.example`), que não deve ser compartilhado.
- `ASSISTENTE_SENHA_ACESSO`: no modo sem contas, se definida, o app pede uma senha única ao abrir
  (útil para o acesso pelo celular na rede de casa).
- **Modo online:** cada pessoa tem conta; senhas guardadas só como hash `scrypt`; bloqueio após 5 tentativas
  erradas; aviso de privacidade (LGPD) no cadastro; exportação e exclusão dos próprios dados. A connection
  string do banco fica só no painel de segredos da hospedagem.
- A memória recusa senhas, tokens, chaves, CPF e números de cartão.
- O Streamlit está configurado para **não** enviar estatísticas de uso.
- Detalhes da auditoria: `docs/REVISOES.md`.

## 12. Limitações atuais e pendências

- **Celular:** layout conferido no navegador em 375 px, mas não num aparelho real. No emulador,
  caixas de seleção e interruptores não responderam a cliques simulados (botões e campos funcionaram).
- **Notificações** só aparecem com o app aberto no navegador. Avisos do sistema (Windows) ou push no celular
  exigiriam um serviço extra e não estão implementados.
- **Automações** rodam quando o app é aberto (uma vez por dia), não em horário fixo com o app fechado.
- **Chat** entende só os comandos documentados (regras). Uma IA opcional pode ser ligada no futuro em
  `assistente/ia.py`, sempre mantendo a confirmação antes de alterar dados.
- **Modo online:** o login não fica salvo ao recarregar a página (F5); não há "esqueci minha senha"
  automático (o administrador usa `scripts/redefinir_senha.py`). A publicação em si **ainda não foi feita**:
  depende das contas no GitHub, Streamlit e Neon (veja `docs/PUBLICACAO.md`). O código foi testado no Python
  3.15; a sintaxe foi conferida para 3.11+, mas a execução em outra versão só será vista na hospedagem.
- **Tema escuro** feito por CSS próprio: atualizações futuras do Streamlit podem exigir ajustes.

## 13. Backup e recuperação

Fazer backup (pode ser com o app aberto):

```bash
.\.venv\Scripts\python.exe scripts\backup.py
```

(Somente no uso pessoal com SQLite; online, veja `docs/PUBLICACAO.md`.) Isso cria `backups\assistente-AAAAMMDD-HHMMSS.db`. Guarde cópias fora do computador (pendrive, nuvem pessoal).

Restaurar (feche o app antes):

```bash
.\.venv\Scripts\python.exe scripts\backup.py --restaurar backups\NOME-DO-ARQUIVO.db
```

O banco atual é guardado antes como `backups\antes-de-restaurar-...db`, então nada se perde.
Você também pode exportar seus dados em *Configurações → Exportar meus dados* (JSON ou CSV).

## 14. Atualizações futuras e implantação online

**Atualizar o projeto:** faça backup, atualize o código, rode `pip install -r requirements-dev.txt` e
`pytest`. As tabelas novas são criadas automaticamente; a tabela `schema_versao` existe para futuras migrações.

**Publicar na internet:** siga **[docs/PUBLICACAO.md](docs/PUBLICACAO.md)**. Resumo:

1. `.\.venv\Scripts\python.exe scripts\preparar_publicacao.py` gera a pasta `publicacao\` só com arquivos seguros.
2. Crie o banco PostgreSQL gratuito (Neon) e copie a connection string.
3. Envie o conteúdo de `publicacao\` para um repositório no GitHub (pelo navegador).
4. No Streamlit Community Cloud, crie o app apontando para `app.py` e cole os Secrets
   (`ASSISTENTE_AMBIENTE`, `ASSISTENTE_CONTAS`, `ASSISTENTE_CODIGO_CONVITE`, `ASSISTENTE_DATABASE_URL`).
5. Teste criando sua conta e só então convide outras pessoas.

Os serviços gratuitos podem mudar limites e preços: confira nos sites antes de usar.
