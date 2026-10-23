# Como publicar o Lume na internet (gratuito)

Este guia coloca o app no ar para **outras pessoas** usarem, cada uma com sua conta.
Tudo é feito pelo navegador; não precisa instalar o git.

| Peça | Serviço sugerido | Para quê |
|---|---|---|
| Código | **GitHub** (github.com) | Guardar os arquivos do app |
| App no ar | **Streamlit Community Cloud** (share.streamlit.io) | Rodar o app e dar o link |
| Banco de dados | **Neon** (neon.com) | Guardar os dados das pessoas sem perder nada |

> **Atenção aos planos gratuitos.** Em outubro de 2026, o Neon informava no plano Free: 1 GB por projeto,
> 100 horas de computação por mês e pausa automática após 5 minutos sem uso. O Streamlit Community Cloud é
> gratuito para apps públicos e coloca o app para "dormir" quando fica sem visitas. **Esses limites podem mudar:
> confira nos sites antes de usar.**

Por que não usar só a hospedagem? O Streamlit Community Cloud **não garante** que arquivos gravados pelo app
continuem existindo (a própria documentação avisa). Por isso, na internet, o app usa um banco PostgreSQL
externo, e não o arquivo SQLite.

---

## Passo 1 — Gerar a pasta para publicar (no seu computador)

No PowerShell, dentro da pasta `projetinho`:

```bash
.\.venv\Scripts\python.exe scripts\preparar_publicacao.py
```

Isso cria a pasta `publicacao\` só com o código. O script **confere** que ela não tem seus dados, senhas,
`.env`, backups, nem o PDF. Se aparecer "ATENÇÃO, não publique", pare e me chame.

## Passo 2 — Criar o banco no Neon

1. Entre em **neon.com** e crie uma conta (pode usar a conta do GitHub).
2. Crie um **projeto** (nome: `lume`). Em *Region*, escolha a mais próxima do Brasil que aparecer.
3. Na tela do projeto, clique em **Connect** e copie a **connection string**. Ela começa com
   `postgresql://` e termina com `?sslmode=require`.
4. **Essa linha contém a senha do banco.** Não mande para ninguém, não cole em chat e não coloque em
   nenhum arquivo do GitHub. Ela vai só no painel de segredos do Passo 4.

As tabelas são criadas sozinhas na primeira vez que o app abrir.

## Passo 3 — Enviar o código para o GitHub

1. Entre em **github.com** → botão **New** (novo repositório).
2. Nome: `lume-assistente`. Pode ser **Private** (o Streamlit consegue ler repositórios privados com sua
   autorização) ou **Public** (o código fica visível; nenhum dado ou segredo vai junto).
3. Marque **não** adicionar README (o projeto já tem). Clique em **Create repository**.
4. Na página do repositório vazio, clique em **uploading an existing file**.
5. Abra a pasta `projetinho\publicacao` no Explorador de Arquivos, selecione **tudo o que está dentro dela**
   (inclusive as pastas `.streamlit` e `assistente`) e arraste para a página do GitHub.
6. Espere terminar o envio e clique em **Commit changes**.
7. Confira se aparecem na raiz do repositório: `app.py`, `requirements.txt`, `.streamlit/` e `assistente/`.

## Passo 4 — Colocar o app no ar (Streamlit Community Cloud)

1. Entre em **share.streamlit.io** com a sua conta do GitHub e autorize o acesso.
2. Clique em **Create app** → **Deploy a public app from GitHub** (ou a opção equivalente).
3. Escolha o repositório `lume-assistente`, branch `main`, arquivo principal `app.py`.
4. Abra **Advanced settings**:
   - **Python version:** escolha a mais nova disponível (o código foi verificado para 3.11 ou mais novo e
     testado de verdade no 3.15).
   - **Secrets:** cole o texto abaixo, trocando os valores entre aspas:

     ```toml
     ASSISTENTE_AMBIENTE = "producao"
     ASSISTENTE_CONTAS = "sim"
     ASSISTENTE_CODIGO_CONVITE = "invente-um-codigo-dificil"
     ASSISTENTE_DATABASE_URL = "cole-aqui-a-connection-string-do-neon"
     ```

5. Escolha o endereço do app (ex.: `lume-assistente`) e clique em **Deploy**.
6. Aguarde a instalação (alguns minutos). Se aparecer erro, abra **Manage app → logs** e me mande
   **só a mensagem de erro** (nunca a connection string).

## Passo 5 — Testar e convidar pessoas

1. Abra o link do app, vá em **Criar conta**, use o código de convite e crie **a sua** conta.
2. Cadastre uma tarefa, saia e entre de novo para conferir que ela continua lá.
3. Teste no celular (fora do Wi-Fi de casa também).
4. Para convidar alguém: mande o **link** e o **código de convite** por mensagem privada.
5. Para parar de aceitar cadastros, troque o código nos Secrets (app → **Settings → Secrets**).

## Problemas que já aconteceram (e a solução)

- **"O banco de dados online não está configurado":** o Secret `ASSISTENTE_DATABASE_URL` ainda tinha o texto de
  exemplo ou estava sem aspas. Corrija em *Manage app → ⋮ → Settings → Secrets*; o valor precisa estar
  **entre aspas**: `ASSISTENTE_DATABASE_URL = "postgresql://...?sslmode=require"`.
- **Botão "Save changes" desativado nos Secrets:** algum valor ficou sem aspas (o formato TOML fica inválido).
- **Salvou, mas o aviso continua:** use *⋮ → Reboot app* (a versão atual já relê os Secrets a cada acesso).
- **Não aparece a connection string no Neon:** confira se existe um projeto criado; ela fica em **Connect**.

## Manutenção

- **Atualizar o app:** rode o Passo 1 de novo e envie os arquivos alterados para o GitHub
  (**Add file → Upload files**, substituindo). O Streamlit atualiza o app sozinho.
- **Esqueceram a senha:** no seu computador, com a connection string só na sessão do PowerShell:

  ```bash
  $env:ASSISTENTE_DATABASE_URL = "cole-a-connection-string"
  ```

  ```bash
  .\.venv\Scripts\python.exe scripts\redefinir_senha.py email@da-pessoa.com
  ```

  Entregue a senha temporária em particular e peça que a pessoa troque em *Configurações → Minha conta*.
  Depois feche o PowerShell (a variável some junto).
- **Backup:** o Neon guarda histórico de restauração (no plano Free, 6 horas em out/2026). Cada pessoa pode
  baixar os próprios dados em *Configurações → Exportar meus dados*.
- **Saúde do app:** `scripts\verificar_saude.py --url https://SEU-APP.streamlit.app`.

## Segurança e LGPD (resumo)

- O app pede **aviso de privacidade** no cadastro, deixa cada pessoa **baixar** e **excluir** os próprios dados
  e guarda senhas só como hash `scrypt`.
- Como administrador, você tem acesso técnico ao banco: trate os dados como confidenciais e não acesse sem
  necessidade.
- Use um **código de convite** para que só pessoas conhecidas criem conta.
- Se for abrir para o público em geral, considere um termo de uso e uma política de privacidade completa
  (o aviso do app é um resumo).

## Limitações conhecidas desta versão online

- O login não fica salvo ao recarregar a página (F5): é preciso entrar de novo.
- Não há "esqueci minha senha" automático (precisa de envio de e-mail); o administrador redefine.
- Com o app "dormindo" (Streamlit) e o banco pausado (Neon), o primeiro acesso do dia pode demorar alguns segundos.
- Notificações aparecem só dentro do app (sem push no celular).
