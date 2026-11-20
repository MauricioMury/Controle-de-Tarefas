# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Preferências do usuário (de `ai-context/shared/instrucoes.md`)

- Responder sempre em português.
- Antes de criar arquivos novos, apresentar as etapas da implementação. Antes de alterar arquivos existentes, pedir autorização. Sugestões de melhoria podem ser feitas, mas não aplicadas sem aprovação.
- Com a aprovação, editar o arquivo diretamente. Não pedir ao usuário que cole código: as edições fazem parte do controle de versão dele.
- Dar opinião própria e discordar quando a proposta prejudicar o projeto.
- O usuário é desenvolvedor C# e Python.

## Comandos

Ambiente Windows / PowerShell, usando sempre a `.venv` do projeto:

```powershell
pip install -r requirements.txt                       # dependências (requirements-01.txt é legado)
.\.venv\Scripts\python.exe app.py                     # roda em http://0.0.0.0:5050 com debug=True

# todos os testes (unittest; não há pytest nem linter configurados)
.\.venv\Scripts\python.exe -m unittest tests_e2e_crud tests_e2e_security tests_e2e_visual

# um único teste
.\.venv\Scripts\python.exe -m unittest tests_e2e_crud.V5EtapasCrudTestCase.test_editar_tarefa_altera_prioridade
```

O `tests_e2e_visual` sobe um servidor real em `127.0.0.1:5050`, a mesma porta do app. Pare o `python app.py` antes de rodar esse teste.

O `.env` (fora do git) precisa ter `SECRET_KEY`, senão o app não inicia. Também usa `APP_ENV` e `SESSION_COOKIE_SECURE`. Para notificações, as variáveis são `NOTIF_EMAIL_REMETENTE` e `NOTIF_EMAIL_SENHA_APP`.

## Banco de dados e ambientes

- O arquivo do banco é escolhido pelo `APP_ENV` em [app.py](app.py): com `APP_ENV=Desenvolvimento` usa `instance/tarefas-desenvolvimento.db`; com qualquer outro valor (o padrão é `Producao`) usa `instance/tarefas.db`. O `.env` local usa `Desenvolvimento`. Para usar dados de produção localmente, copie o banco para o arquivo de desenvolvimento.
- `instance/` está no `.gitignore`. Ali ficam cópias de bancos reais (inclusive de produção) e a pasta `instance/Backups/`. Nunca versionar.
- `init_db()` só é chamado no `if __name__ == '__main__'`. A ordem é: `run_local_migrations()` (sqlite3 puro, idempotente, só se o arquivo existir), depois `db.create_all()`, depois as categorias padrão para usuários sem categoria. Num deploy WSGI isso não roda sozinho; é preciso inicializar/migrar manualmente.
- **Não há Alembic.** `db.create_all()` cria tabelas novas, mas nunca altera tabelas existentes. Qualquer coluna nova num modelo existente precisa de um `_ensure_column(...)` correspondente em [local_migrations.py](local_migrations.py), senão quebra em bancos já existentes, como o de produção. O SQLite não altera `CHECK`/`UNIQUE`. Mudar os valores permitidos de `Etapa.status` ou de `HistoricoEtapa.acao` exige mudar o modelo e o DDL em `_ensure_v5_etapas_tables`, e recriar a tabela nos bancos existentes.
- A migração também converte senhas em texto puro para hash Werkzeug e preenche `tenant_id` (um tenant por usuário) em dados legados.
- `PRAGMA foreign_keys=ON` é ativado em toda conexão SQLite (listener em [app.py](app.py)).

## Arquitetura

App Flask único, sem blueprints e sem camada de service/repository:

- [app.py](app.py) cria o app, carrega a config do `.env`, configura CSRF (Flask-WTF), Flask-Login, headers de segurança/CSP e o context processor. Depois chama `register_auth_routes(app, criar_categorias_padrao)` e `register_routes(app)`.
- [routes/auth.py](routes/auth.py) cuida de login, registro, logout e perfil. O login bloqueia a conta por 20 minutos após 10 falhas (`failed_login_attempts`/`locked_until`). O registro cria um `Tenant` próprio para cada usuário.
- [routes/routes.py](routes/routes.py) concentra as rotas de negócio, registradas dentro de `register_routes(app)`. Os nomes dos endpoints são os nomes das funções (ex.: `url_for('lista_tarefas')`). Os helpers de módulo no topo do arquivo contêm a lógica de negócio.
- [models.py](models.py) define Tenant → User → Categoria / Tarefa → Etapa → HistoricoEtapa.
- `templates/` contém Jinja2 + Bootstrap 5 via CDN. A CSP em `app.py` só permite `cdn.jsdelivr.net`, `cdnjs.cloudflare.com` e Google Fonts. Um CDN novo precisa ser liberado ali.

### Isolamento multi-tenant (crítico)

Toda consulta precisa filtrar por `tenant_id` **e** `user_id` do usuário logado. Use os helpers existentes (`get_current_tenant_id`, `get_local_user_id`, `buscar_tarefa_ou_404`, `buscar_etapa_ou_404`, `buscar_categoria_ou_404`, `categorias_do_usuario`) em vez de `Model.query.get(id)`. Etapas também precisam pertencer à tarefa informada. O [tests_e2e_security.py](tests_e2e_security.py) cobre IDOR; inclua casos novos nele ao criar rotas.

### Regras de domínio que não são óbvias

- `Tarefa` tem `categoria_id` (FK) **e** `categoria_legado` (coluna `categoria`, NOT NULL), que deve receber o nome da categoria em `montar_tarefa`/`aplicar_dados_tarefa`.
- Etapas: o status vai de `Criada` → `Iniciada` ⇄ `Pausada` → `Concluida`. Toda mudança passa por `alterar_status_etapa`/`registrar_historico_etapa`, que grava `HistoricoEtapa`. O progresso da tarefa é calculado a partir das etapas, sem coluna própria.
- `UNIQUE(tarefa_id, ordem)`: `reordenar_etapas` primeiro grava ordens negativas temporárias, dá flush e só então aplica as finais. Siga esse padrão em qualquer reordenação.
- Rotas de etapa respondem HTML ou JSON conforme `quer_resposta_json()` (requisição JSON, `?format=json` ou header Accept).
- Filtros da lista de tarefas ficam na sessão (`get_filtros_ativos`, `redirect_com_filtros`).
- `datetime.utcnow()` gera `DeprecationWarning` (problema conhecido, pendente de correção).

### Notificações

[notificacoes.py](notificacoes.py) (e-mail via SMTP, WhatsApp via CallMeBot) **não é importado por nenhum módulo hoje**, e o context processor fixa `notifications_enabled: False`. Os campos `notif_*` de `Tarefa` são gravados pelos formulários, mas nada dispara o envio, apesar do que diz o README.

### Testes

Os testes não importam `app.py`. Usam `create_test_app()` de [tests_e2e_crud.py](tests_e2e_crud.py) (reaproveitado pelo teste visual), com SQLite temporário e `WTF_CSRF_ENABLED=False`. Ao adicionar config, hook ou variável de context processor em `app.py`, replique em `create_test_app()` se os templates ou rotas dependerem disso (ex.: `app_version`).

## Versionamento e deploy

- Versionamento semântico, registrado em [versoestarefas.md](versoestarefas.md) (não existe CHANGELOG.md). Toda mudança de comportamento ganha um item em **Não lançado**, com a etapa do roadmap. No PR para a `main`, a seção recebe número e data, e `APP_VERSION` em [app.py](app.py) (exibido no rodapé de `base.html`) é atualizado para o mesmo valor. Tag `vX.Y.Z` na `main`; `git push` é sempre do Mauricio.
- Branch de trabalho `Desenvolvimento` → PR para `main` → no PythonAnywhere, `git pull` da `main` e reload da Web App (`todastarefas.com.br`).
- Produção: `APP_ENV=Producao`, `SESSION_COOKIE_SECURE=True`, banco `instance/tarefas.db`, `.env` criado manualmente no servidor.

## Documentação em `ai-context/`

- [ai-context/local/roadmap.md](ai-context/local/roadmap.md) traz as etapas ativas e pendentes, com regras de status (`PENDENTE`/`ANDAMENTO`/`CONCLUÍDO`) e datas `AAAA-MM-DD HH:MM` (America/Sao_Paulo; consulte o relógio antes de preencher). Etapa concluída vai inteira para `roadmap-historico.md`.
- [ai-context/mapa_projetoV5.md](ai-context/mapa_projetoV5.md) traz o escopo e as decisões da versão atual (V5: etapas). A V4 fica como histórico.
- [ai-context/local/context.md](ai-context/local/context.md) descreve uma arquitetura-alvo futura (FastAPI, Alembic, PostgreSQL, React, Controller→Service→Repository). Essa não é a stack atual. Mauricio decidiu em 2026-11-12 manter Flask + templates + SQLite. Não introduzir essas tecnologias sem pedido explícito. As regras de segurança desse arquivo continuam valendo: ORM fora das migrações, nunca ignorar `tenant_id`/`user_id`, sem segredos no código ou no frontend. As pastas `.agents/` e `.codex/` foram removidas de propósito; não restaurar.
- Os `.md` estão em UTF-8 sem BOM. No PowerShell 5.1, leia com `Get-Content -Encoding UTF8`, senão os acentos aparecem corrompidos. Uma seção do README já está com acentuação corrompida por isso.
