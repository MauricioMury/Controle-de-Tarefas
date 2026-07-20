# Controle de tarefas

Workspace: `02-CONTROLETAREFAS

## Visao geral

O **Controle de tarefas** e uma aplicacao web em Python/Flask para organizar tarefas pessoais por usuario. O sistema permite cadastrar tarefas, classificar por categoria e prioridade, acompanhar status, consultar calendario, aplicar filtros persistentes e configurar notificacoes.

Este repositorio corresponde ao workspace local `03-LOGTAREFASPESSOAIS`, mas o nome funcional do sistema e **Controle de tarefas**.

## Funcionalidades principais

- Autenticacao de usuarios com login, logout e cadastro.
- Dashboard inicial com visao resumida das tarefas.
- Cadastro, edicao, duplicacao, conclusao e exclusao de tarefas.
- Lista de tarefas com busca, filtros, paginacao e persistencia de filtros por sessao.
- Cadastro e manutencao de categorias por usuario.
- Calendario visual de tarefas.
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
|-- app.py                  # Aplicacao Flask principal, rotas e regras de negocio
|-- models.py               # Modelos SQLAlchemy: User, Tarefa e Categoria
|-- notificacoes.py         # Envio e montagem de notificacoes por e-mail e WhatsApp
|-- requirements.txt        # Dependencias Python
|-- versao.py               # Registro simples de versao/observacao
|-- .env                    # Variaveis de ambiente locais
|-- instance/               # Banco SQLite local gerado pela aplicacao
|-- templates/              # Templates HTML da interface
|-- static/                 # Arquivos estaticos
|-- docs/                   # Documentacao, guias e scripts auxiliares
```

## Modelos principais

### User

Representa o usuario do sistema. Armazena credenciais, configuracoes de notificacao por e-mail e WhatsApp, alem dos relacionamentos com tarefas e categorias.

### Tarefa

Representa uma tarefa pessoal. Inclui descricao, comentario, datas, horarios, prioridade, recorrencia, categoria, status e ate duas datas de notificacao por tarefa.

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
python -m venv venv
.\venv\Scripts\Activate.ps1
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
```

4. Execute a aplicacao.

```powershell
python app.py
```

Por padrao, a aplicacao usa SQLite em `instance/tarefas.db`.

## Banco de dados

O banco e criado com SQLAlchemy a partir dos modelos definidos em `models.py`. A aplicacao usa SQLite localmente e cria as tabelas necessarias na inicializacao quando aplicavel.

O arquivo de banco fica dentro de `instance/` e nao deve ser tratado como codigo-fonte.

## Notificacoes

O sistema possui suporte a notificacoes por:

- e-mail;
- WhatsApp via configuracao externa.

As notificacoes sao verificadas durante requisicoes autenticadas. Cada tarefa pode ter ate duas datas de notificacao, com controle separado de envio por canal.

## Documentacao complementar

A pasta `docs/` contem historico tecnico, guias de atualizacao, scripts de migracao, contexto do projeto e registros de funcionalidades. Ela deve ser consultada antes de alteracoes estruturais no sistema.

Arquivos uteis:

- `docs/CONTEXTO_PROJETO01.md`
- `docs/mapa_projetoV4.md`
- `docs/RESUMO_NOTIFICACOES.md`
- `docs/GUIA_ATUALIZACAO_V4.md`

## Observacoes de manutencao

- Alteracoes em modelos podem exigir migracao manual do SQLite.
- Rotas protegidas dependem de autenticacao com Flask-Login.
- Formularios usam protecao CSRF via Flask-WTF.
- As configuracoes sensiveis devem ficar em `.env`, nunca hardcoded no codigo.
- Antes de mudar regras de notificacao, validar tambem `notificacoes.py` e os campos correspondentes em `models.py`.
