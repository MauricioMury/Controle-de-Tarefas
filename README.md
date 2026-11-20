# Controle de tarefas

Workspace: `02-CONTROLETAREFAS`

## Visao geral

O **Controle de tarefas** e uma aplicacao web em Python/Flask para organizar tarefas pessoais por usuario. O sistema permite cadastrar tarefas, dividir tarefas em etapas de execucao, classificar por categoria e prioridade, acompanhar status, consultar calendario, aplicar filtros persistentes e configurar notificacoes.

Este repositorio corresponde ao workspace local `02-ControleTarefas`, e o nome funcional do sistema e **Controle de tarefas**.

## Funcionalidades principais

- Autenticacao de usuarios com login, logout e cadastro.
- Dashboard inicial com visao resumida das tarefas.
- Cadastro, edicao, duplicacao, conclusao e exclusao de tarefas.
- Etapas de execucao vinculadas a tarefas, com ordem, status proprio, progresso e historico.
- Lista de tarefas com busca, filtros, paginacao e persistencia de filtros por sessao.
- Cadastro e manutencao de categorias por usuario.
- Calendario visual de tarefas e etapas planejadas.
- Entrada rapida para movimentacao e organizacao de tarefas.
- Perfil do usuario com configuracao de notificacoes.
- Notificacoes por e-mail e WhatsApp, quando configuradas.
- Protecoes basicas de seguranca via CSRF, cookies de sessao e headers HTTP.

## Stack tecnica

- Python
- Flask
- Flask-Login
- Flask-SQLAlchemy
- Flask-WTF
- SQLite
- Jinja2
- Bootstrap
- python-dotenv
- requests

As dependencias do projeto estao declaradas em `requirements.txt`.

## Estrutura do projeto

```text
.
|-- app.py                  # Aplicacao Flask principal e inicializacao do app
|-- models.py               # Modelos SQLAlchemy: Tenant, User, Categoria, Tarefa, Etapa e HistoricoEtapa
|-- local_migrations.py     # Migracoes locais idempotentes para SQLite
|-- notificacoes.py         # Envio e montagem de notificacoes por e-mail e WhatsApp
|-- requirements.txt        # Dependencias Python
|-- .env                    # Variaveis de ambiente locais
|-- instance/               # Banco SQLite local gerado pela aplicacao
|-- routes/                 # Rotas de autenticacao e rotas principais
|-- templates/              # Templates HTML da interface
|-- ai-context/             # Contexto tecnico e roadmap do projeto
|-- tests_e2e_crud.py       # Testes locais do fluxo funcional da V5
|-- tests_e2e_security.py   # Testes locais de seguranca/IDOR da V5
|-- tests_e2e_visual.py     # Testes locais de servidor HTTP e HTML renderizado da V5
```

## Modelos principais

### Tenant

Representa o escopo logico de isolamento dos dados.

### User

Representa o usuario do sistema. Armazena credenciais, configuracoes de notificacao por e-mail e WhatsApp, alem dos relacionamentos com tarefas e categorias.

### Tarefa

Representa uma tarefa pessoal. Inclui descricao, comentario, datas, horarios, prioridade, recorrencia, categoria, status e ate duas datas de notificacao por tarefa.

### Etapa

Representa uma acao necessaria para executar uma tarefa. Cada etapa possui titulo, descricao, ordem, data planejada, horario, status proprio e conclusao real.

### HistoricoEtapa

Registra acoes relevantes de uma etapa, como criacao, edicao, inicio, pausa, retomada, conclusao e reordenacao.

### Categoria

Representa categorias personalizadas por usuario, com nome e cor associada para organizacao visual.

## Rotas principais

- `/login` - login do usuario.
- `/register` - cadastro de usuario.
- `/logout` - encerramento da sessao.
- `/` - dashboard.
- `/perfil` - configuracoes do usuario e notificacoes.
- `/cadastro_tarefa` - criacao de tarefa.
- `/lista_tarefas` - listagem, busca, filtros e paginacao.
- `/editar_tarefa/<id>` - edicao de tarefa.
- `/duplicar_tarefa/<id>` - duplicacao de tarefa.
- `/deletar_tarefa/<id>` - exclusao de tarefa.
- `/marcar_concluida/<id>` - conclusao de tarefa.
- `/tarefas/<id>/etapas` - listagem de etapas da tarefa.
- `/tarefas/<id>/etapas/nova` - criacao de etapa.
- `/etapas/<id>/editar` - edicao de etapa.
- `/etapas/<id>/iniciar` - iniciar etapa.
- `/etapas/<id>/pausar` - pausar etapa.
- `/etapas/<id>/retomar` - retomar etapa.
- `/etapas/<id>/concluir` - concluir etapa.
- `/etapas/<id>/deletar` - exclusao de etapa.
- `/etapas/<id>/historico` - historico da etapa.
- `/tarefas/<id>/etapas/reordenar` - reordenacao de etapas.
- `/categorias` - listagem de categorias.
- `/cadastro_categoria` - criacao de categoria.
- `/editar_categoria/<id>` - edicao de categoria.
- `/deletar_categoria/<id>` - exclusao de categoria.
- `/calendario` - calendario visual.
- `/entrada_rapida` - entrada rapida de tarefas.
- `/mover_tarefa/<id>` - movimentacao de tarefa.

## Configuracao local

1. Crie e ative um ambiente virtual Python.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instale as dependencias.

```powershell
pip install -r requirements.txt
```

3. Configure o arquivo `.env`.

Exemplo minimo:

```env
SECRET_KEY=sua-chave-secreta-local
SESSION_COOKIE_SECURE=False
APP_ENV=Desenvolvimento
```

4. Execute a aplicacao.

```powershell
python app.py
```

Com `APP_ENV=Desenvolvimento`, a aplicacao usa SQLite em `instance/tarefas-desenvolvimento.db`. Sem esse valor, usa `instance/tarefas.db`.

## Banco de dados

O banco e criado com SQLAlchemy a partir dos modelos definidos em `models.py`. A aplicacao usa SQLite localmente e cria as tabelas necessarias na inicializacao quando aplicavel.

O arquivo de banco fica dentro de `instance/` e nao deve ser tratado como codigo-fonte.

Antes de mudancas estruturais, crie backup do banco em `instance/`. A V5 usa migracao local idempotente em `local_migrations.py` para criar `etapa` e `historico_etapa`.

## Validacao local

Execute os testes locais com a `.venv` do projeto:

```powershell
.\.venv\Scripts\python.exe -m unittest tests_e2e_crud tests_e2e_security tests_e2e_visual
```

Os testes usam apps Flask de teste e bancos SQLite temporarios; nao devem alterar `instance\tarefas-desenvolvimento.db`.

## Notificacoes

O sistema possui suporte a notificacoes por:

- e-mail;
- WhatsApp via configuracao externa.

As notificacoes sao verificadas durante requisicoes autenticadas. Cada tarefa pode ter ate duas datas de notificacao, com controle separado de envio por canal.

## Documentacao complementar

A pasta `ai-context/` contem contexto tecnico, roadmap do projeto e registros de funcionalidades. Ela deve ser consultada antes de alteracoes estruturais no sistema.

Arquivos uteis:

- `ai-context/local/context.md`
- `ai-context/mapa_projetoV5.md`
- `ai-context/mapa_projetoV4.md`

## Observacoes de manutencao

- Alteracoes em modelos podem exigir migracao manual do SQLite.
- Rotas protegidas dependem de autenticacao com Flask-Login.
- Formularios usam protecao CSRF via Flask-WTF.
- As configuracoes sensiveis devem ficar em `.env`, nunca hardcoded no codigo.
- Antes de mudar regras de notificacao, validar tambem `notificacoes.py` e os campos correspondentes em `models.py`.
- Rotas de etapa devem sempre validar `tenant_id`, `user_id` e a tarefa dona para evitar IDOR.

# Github
git status --short --branch
git switch -c Desenvolvimento
.\.venv\Scripts\python.exe -m unittest tests_e2e_crud tests_e2e_security tests_e2e_visual
git add -A
git status --short
git diff --cached --name-only
git commit -m "Implementa V5 de etapas e validacoes locais"
git push -u origin Desenvolvimento

git fetch origin
git branch --show-current
git switch -c Desenvolvimento --track origin/Desenvolvimento

# Colocar em produção
- Plano Seguro
- Fazer merge do PR Desenvolvimento -> main.
- No PythonAnywhere, clonar/puxar a main.
git clone -b main https://github.com/MauricioMury/Controle-de-Tarefas.git Controle-de-Tarefas
- Criar virtualenv.
- Instalar requirements.txt.
- Criar .env manual no servidor.
- Inicializar/migrar SQLite.
- Configurar WSGI.
- Configurar /static/.
- Reload da Web App.

## Resumo Github - 28/07/2026
- Implementa telas e fluxo V5 de etapas vinculadas a tarefas.
- Adiciona histórico, progresso, duplicação e ordenação de etapas.
- Inclui validações locais de CRUD, segurança e renderização visual.

## Validação
- `python tests_e2e_crud.py` - 5 testes OK
- `python tests_e2e_security.py` - 4 testes OK
- `python tests_e2e_visual.py` - 2 testes OK

## Observações
- Foram observados `DeprecationWarning` relacionados a `datetime.utcnow()`, sem falha nos testes.

## Release de producao - 28/07/2026
- Deploy inicial validado em producao para uso pessoal em `todastarefas.com.br`.
- Tela `/calendario` validada manualmente apos reload da Web App.
- Banco de producao esperado: `instance/tarefas.db`, criado a partir do conteudo validado de `instance/tarefas-desenvolvimento.db`.
- Ambiente de producao esperado: `APP_ENV=Producao` e `SESSION_COOKIE_SECURE=True`.
- Escopo aceito: uso pessoal/baixo volume com SQLite.

# Proximos passos pos-producao
- Criar backup periodico do `instance/tarefas.db` no servidor.
- Corrigir `DeprecationWarning` relacionados a `datetime.utcnow()` usando datas timezone-aware.
- Revisar pequenos ajustes visuais observados no uso real, sem alterar regra de negocio.
- Manter qualquer melhoria pos-producao em etapa separada da V5 concluida.
