# Mapa do Projeto - Controle de Tarefas

**Versao:** 5.0
**Data:** 20 - Julho 2026
**Tecnologias:** Flask 3.0, SQLite, Bootstrap 5, Python 3.11+, Syne + DM Sans (Google Fonts)

---

## O que a V5 entregou?

A V5 adicionou a funcionalidade de **etapas de execucao da tarefa**.

Decisao conceitual importante: nao trataremos como "subtarefas". A tarefa principal representa o resultado esperado, enquanto as etapas representam as acoes necessarias para chegar nesse resultado.

Exemplo:

```text
Tarefa: Implantar novo servidor
Data prevista: 20/07/2026
Status: Em andamento
Progresso: 50%

Etapas:
1. Preparar servidor - Concluida
2. Instalar sistema operacional - Concluida
3. Instalar agente de seguranca - Em andamento
4. Validar funcionamento - Pendente
```

Cada etapa possui:

- titulo;
- descricao;
- ordem de execucao;
- status proprio;
- data planejada;
- hora de inicio;
- hora de fim;
- data/hora de conclusao;
- historico de acoes.

Statuses previstos para etapa:

- `Criada`: existe, mas ainda nao foi iniciada.
- `Iniciada`: esta em execucao.
- `Pausada`: foi pausada.
- `Concluida`: foi finalizada.

Regras de escopo da V5:

- Nao havera responsavel por etapa nesta versao.
- Nao havera peso por etapa nesta versao.
- Nao havera etapa obrigatoria/opcional nesta versao.
- Nao havera dependencia entre etapas nesta versao.
- O progresso da tarefa sera calculado automaticamente pelo total de etapas concluidas.
- O historico de etapa registrara acoes relevantes, usuario, data/hora e descricao.
- Os metadados do banco devem ficar em portugues sem acento.

---

## Indice

### [1. Estrutura do Projeto](#1-estrutura-do-projeto)
### [2. Funcionalidades Implementadas](#2-funcionalidades-implementadas)
### [3. Banco de Dados](#3-banco-de-dados)
### [4. Rotas da Aplicacao](#4-rotas-da-aplicacao)
### [5. Interface do Usuario (V5)](#5-interface-do-usuario-v5)
### [6. Guia de Instalacao](#6-guia-de-instalacao)
### [7. Seguranca](#7-seguranca)
### [8. Manutencao e Desenvolvimento](#8-manutencao-e-desenvolvimento)
### [9. Roadmap para esta feature](#9-roadmap-para-esta-feature)

---

## 1. Estrutura do Projeto

### 1.1 Arquivos Principais

```text
controle_tarefas/
├── app.py                         # Aplicacao Flask principal
├── models.py                      # Modelos de banco de dados
├── routes/
│   ├── auth.py                    # Rotas de autenticacao
│   └── routes.py                  # Rotas principais do MVP local
├── templates/
├── requirements.txt
├── pytest.ini
├── instance/
│   └── tarefas.db                 # Banco SQLite local
├── ai-context/
│   ├── mapa_projetoV4.md
│   └── mapa_projetoV5.md          # Este arquivo
└── README.md
```

### 1.2 Diretorio templates/

```text
templates/
├── base.html
├── login.html
├── register.html
├── index.html
├── cadastro_tarefa.html
├── editar_tarefa.html
├── lista_tarefas.html
├── cadastro_categoria.html
├── editar_categoria.html
├── lista_categorias.html
├── lista_etapas.html              # Implementado V5
├── cadastro_etapa.html            # Implementado V5
├── editar_etapa.html              # Implementado V5
└── historico_etapa.html           # Implementado V5
```

**Hierarquia de Templates:**

```text
base.html (tema dark/light, navbar com toggle, footer)
├── register.html
└── [templates autenticados]
    ├── index.html
    ├── cadastro_tarefa.html
    ├── editar_tarefa.html
    ├── lista_tarefas.html
    ├── cadastro_categoria.html
    ├── editar_categoria.html
    ├── lista_categorias.html
    ├── lista_etapas.html          (etapas da tarefa)
    ├── cadastro_etapa.html        (nova etapa vinculada a tarefa)
    ├── editar_etapa.html          (edicao/status da etapa)
    └── historico_etapa.html       (acoes registradas da etapa)

login.html (standalone - toggle proprio, nao estende base.html)
```

---

## 2. Funcionalidades Implementadas

### 2.1 Autenticacao

#### Login
- Rota: `/login`
- Metodo: GET, POST
- Validacoes: usuario existe, senha correta, sessao Flask-Login
- Interface standalone com toggle dark/light proprio

#### Registro
- Rota: `/register`
- Validacoes: username unico, senhas coincidem, hash automatico
- Cria categorias padrao automaticamente para o novo usuario

#### Logout
- Rota: `/logout`

---

### 2.2 Gestao de Tarefas

#### Cadastro de Tarefa
- **Rota:** `/cadastro_tarefa`
- **Campos atuais:** tarefa, comentario, data meta, data realizado, hora inicio, hora fim, prioridade, recorrencia e categoria
- **V5:** a tarefa recebe etapas apos a criacao, pela tela propria de etapas.
- **Validacao atual:** hora fim maior que hora inicio quando ambos existirem.

#### Lista de Tarefas
- **Rota:** `/lista_tarefas`
- **Features atuais:**
  - paginacao;
  - busca por texto;
  - filtros por categoria, prioridade, status e data;
  - filtros persistentes;
  - indicador visual de filtros ativos;
  - ordenacao por data e hora;
  - tabela responsiva Bootstrap.
- **V5 implementado:** exibe resumo de progresso, quantidade de etapas concluidas e atalho para abrir as etapas.

#### Edicao de Tarefa
- **Rota:** `/editar_tarefa/<id>`
- **V5 implementado:** mantem a edicao da tarefa leve e direciona a gestao de etapas para telas proprias.

#### Exclusao de Tarefa
- **Rota:** `/deletar_tarefa/<id>` (POST)
- **V5 implementado:** a exclusao de tarefa remove etapas e historicos vinculados por cascade ORM; a exclusao fisica de uma etapa remove seus historicos nesta versao.

#### Marcar como Concluida
- **Rota:** `/marcar_concluida/<id>` (POST)
- **V5 adiado:** a tarefa ainda pode ser marcada como concluida independentemente das etapas. Bloqueio por progresso fica fora desta versao.

#### Duplicar Tarefa
- **Rota:** `/duplicar_tarefa/<id>`
- **V5 implementado:** a duplicacao copia os dados da tarefa e recria as etapas da origem como `Criada`, sem historico antigo, sem `concluida_em` e com `data_planejada` igual a `data_meta` da nova tarefa.

---

### 2.3 Gestao de Etapas

#### Implementado na V5

- Criar etapa vinculada a uma tarefa.
- Editar titulo, descricao, ordem, data planejada, hora inicio, hora fim e status.
- Pausar e retomar etapa.
- Concluir etapa.
- Reordenar etapas.
- Registrar historico automatico das acoes de status.
- Calcular progresso da tarefa com base nas etapas concluidas.

#### Exemplo de exibicao da tarefa na lista

```text
Implantar novo servidor
Progresso: 50%
2 de 4 etapas concluidas
Prazo: 20/07/2026
```

#### Exemplo de exibicao ao abrir a tarefa

```text
[Concluida] Preparar servidor
[Concluida] Instalar sistema operacional
[Iniciada]  Instalar agente de seguranca
[Criada]    Validar funcionamento
```

---

### 2.4 Gestao de Categorias

#### CRUD Completo
- `/categorias` - lista categorias do usuario
- `/cadastro_categoria` - criar nova categoria com nome e cor
- `/editar_categoria/<id>` - editar nome e cor
- `/deletar_categoria/<id>` - deletar, bloqueado se em uso

#### Cores Disponiveis
`primary`, `success`, `danger`, `warning`, `info`, `secondary`, `dark`, `light`

---

### 2.5 Calendario

#### Implementado na V5

- A tarefa principal aparece no calendario pela data meta.
- As etapas aparecem individualmente no calendario pela data planejada.
- O calendario diferencia tarefas e etapas por filtro de tipo e badge visual.

Exemplo:

```text
16/07 ate 20/07 - Implantar novo servidor

16/07 - Preparar servidor
17/07 - Instalar sistema operacional
18/07 - Instalar agente de seguranca
20/07 - Validar funcionamento
```

---

## 3. Banco de Dados

### 3.1 Modelo User

```python
class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tarefas  = db.relationship("Tarefa", backref="usuario", cascade="all, delete-orphan")
```

### 3.2 Modelo Tarefa

Modelo atual, a confirmar no codigo antes da implementacao:

```python
class Tarefa(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    tarefa         = db.Column(db.String(200), nullable=False)
    comentario     = db.Column(db.Text, nullable=True)
    data_meta      = db.Column(db.Date, nullable=False)
    data_realizado = db.Column(db.Date, nullable=True)
    hora_inicio    = db.Column(db.Time, nullable=False)
    hora_fim       = db.Column(db.Time, nullable=True)
    prioridade     = db.Column(db.String(20), nullable=False)
    recorrencia    = db.Column(db.String(50), nullable=False)
    categoria_id   = db.Column(db.Integer, db.ForeignKey("categoria.id"), nullable=True)
    categoria      = db.Column(db.String(50), nullable=True)  # legado temporario
    status         = db.Column(db.String(20), default="Pendente")
    user_id        = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
```

### 3.3 Modelo Categoria

```python
class Categoria(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    nome       = db.Column(db.String(50), nullable=False)
    cor        = db.Column(db.String(20), default="info")
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### 3.4 Modelo Etapa

Modelo aprovado para a V5-2, com nomes em portugues sem acento e escopo explicito por `tenant_id` e `user_id`:

```python
class Etapa(db.Model):
    __table_args__ = (
        db.UniqueConstraint("tarefa_id", "ordem", name="uq_etapa_tarefa_ordem"),
        db.CheckConstraint(
            "status IN ('Criada', 'Iniciada', 'Pausada', 'Concluida')",
            name="ck_etapa_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tarefa_id = db.Column(db.Integer, db.ForeignKey("tarefa.id"), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ordem = db.Column(db.Integer, nullable=False)
    data_planejada = db.Column(db.Date, nullable=True)
    hora_inicio = db.Column(db.Time, nullable=True)
    hora_fim = db.Column(db.Time, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Criada")
    concluida_em = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

Decisoes da V5-2:

- `tenant_id` e `user_id` ficam na etapa para manter o mesmo padrao de isolamento de `Tarefa` e `Categoria`.
- `ordem` deve ser unica dentro da mesma tarefa.
- `status` deve aceitar apenas `Criada`, `Iniciada`, `Pausada` e `Concluida`.
- `data_planejada` representa a data prevista da etapa.
- `hora_inicio` e `hora_fim` representam a janela de execucao da etapa.
- `concluida_em` registra o momento real de conclusao.
- Nao entram nesta versao: responsavel, peso, dependencia e obrigatoriedade.
- O progresso da tarefa nao sera persistido em coluna nesta V5; sera calculado a partir das etapas.

### 3.5 Modelo HistoricoEtapa

```python
class HistoricoEtapa(db.Model):
    __table_args__ = (
        db.CheckConstraint(
            "acao IN ('criar', 'editar', 'iniciar', 'pausar', 'retomar', 'concluir', 'excluir', 'reordenar')",
            name="ck_historico_etapa_acao",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tarefa_id = db.Column(db.Integer, db.ForeignKey("tarefa.id"), nullable=False, index=True)
    etapa_id = db.Column(db.Integer, db.ForeignKey("etapa.id"), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    acao = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

Decisoes da V5-2:

- O historico registra o usuario que executou a acao, mas tambem guarda `tenant_id` para auditoria e filtros seguros.
- `acao` deve ser uma lista controlada, nao texto livre.
- `descricao` pode receber detalhes de contexto, mas nao deve registrar segredos, tokens ou dados sensiveis.
- Historico deve ser criado automaticamente nas mudancas relevantes de etapa.
- Na exclusao de etapa, a V5 deve preferir registrar a acao antes de remover a etapa. Se a exclusao fisica apagar tambem o historico por cascade, isso perde auditabilidade; por isso, a decisao final de exclusao fisica versus exclusao logica fica marcada como ponto de atencao para V5-5.

### 3.6 Relacionamentos

```text
Tenant (1) -> (N) User
Tenant (1) -> (N) Categoria
Tenant (1) -> (N) Tarefa
Tenant (1) -> (N) Etapa
Tenant (1) -> (N) HistoricoEtapa

User (1) -> (N) Categoria
User (1) -> (N) Tarefa
User (1) -> (N) Etapa
User (1) -> (N) HistoricoEtapa

Categoria (1) -> (N) Tarefa
Tarefa (1) -> (N) Etapa, ordenadas por `ordem`
Tarefa (1) -> (N) HistoricoEtapa
Etapa (1) -> (N) HistoricoEtapa
```

Regras de integridade:

- Toda etapa deve pertencer a uma tarefa do mesmo usuario.
- Todo historico deve pertencer a uma etapa e tarefa do mesmo usuario.
- Toda etapa e todo historico devem carregar o mesmo `tenant_id` e `user_id` da tarefa.
- Ao excluir uma tarefa, as etapas e historicos vinculados devem ser tratados de forma explicita e validada.
- `ordem` deve ser unica por tarefa.
- A busca por etapa nunca deve usar apenas `Etapa.id`; deve validar `tenant_id`, `user_id` e a tarefa vinculada.
- A busca por historico nunca deve usar apenas `HistoricoEtapa.id`; deve validar `tenant_id`, `user_id`, tarefa e etapa vinculadas.

---

## 4. Rotas da Aplicacao

### 4.1 Rotas Publicas

| Rota | Metodo | Descricao |
|------|--------|-----------|
| `/login` | GET, POST | Pagina de login |
| `/register` | GET, POST | Cadastro de usuario |

### 4.2 Rotas Protegidas Existentes

| Rota | Metodo | Descricao |
|------|--------|-----------|
| `/` | GET | Dashboard com stats |
| `/logout` | GET | Encerrar sessao |
| `/cadastro_tarefa` | GET, POST | Criar nova tarefa |
| `/lista_tarefas` | GET | Lista + filtros + busca |
| `/editar_tarefa/<id>` | GET, POST | Editar tarefa |
| `/deletar_tarefa/<id>` | POST | Deletar tarefa |
| `/marcar_concluida/<id>` | POST | Marcar como concluida |
| `/duplicar_tarefa/<id>` | GET | Duplicar tarefa |
| `/categorias` | GET | Lista de categorias |
| `/cadastro_categoria` | GET, POST | Nova categoria |
| `/editar_categoria/<id>` | GET, POST | Editar categoria |
| `/deletar_categoria/<id>` | POST | Deletar categoria |

### 4.3 Rotas Protegidas Implementadas na V5

| Rota | Metodo | Descricao |
|------|--------|-----------|
| `/tarefas/<id>/etapas` | GET | Listar etapas da tarefa |
| `/tarefas/<id>/etapas/nova` | GET, POST | Criar etapa para a tarefa |
| `/etapas/<id>/editar` | GET, POST | Editar etapa |
| `/etapas/<id>/iniciar` | POST | Marcar etapa como iniciada |
| `/etapas/<id>/pausar` | POST | Marcar etapa como pausada |
| `/etapas/<id>/retomar` | POST | Retomar etapa pausada |
| `/etapas/<id>/concluir` | POST | Marcar etapa como concluida |
| `/etapas/<id>/deletar` | POST | Excluir etapa |
| `/etapas/<id>/historico` | GET | Visualizar historico da etapa |
| `/tarefas/<id>/etapas/reordenar` | POST | Atualizar ordem das etapas |

---

## 5. Interface do Usuario (V5)

### 5.1 Sistema de Cores

Mantem o design system da V4, sem redesenhar a aplicacao inteira.

### 5.2 Listagem de Tarefas

Implementado:

- barra ou texto de progresso;
- quantidade de etapas concluidas;
- botao/atalho para etapas;
- filtro por status da tarefa continua existindo.

Filtro por status de etapa na lista de tarefas ficou fora da V5 para manter a query simples. O calendario recebeu filtro por tipo e status visual de etapas.

### 5.3 Tela de Etapas

A tela de etapas prioriza operacao rapida:

- lista ordenada por `ordem`;
- status visivel;
- data planejada;
- botoes de acao por status;
- link para historico;
- formulario simples para nova etapa.

### 5.4 Historico de Etapa

Exibe linha do tempo simples:

```text
16/07 09:00 - Joao iniciou a preparacao.
16/07 11:30 - Preparacao concluida.
17/07 14:20 - Etapa pausada por falta de acesso.
17/07 16:00 - Etapa retomada.
```

---

## 6. Guia de Instalacao

### 6.1 Requisitos

- Python 3.11+
- pip
- Ambiente virtual
- SQLite local
- `.env` com `SECRET_KEY`

### 6.2 Execucao Local

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
$env:APP_ENV="Desenvolvimento"
python app.py
```

Acesse: `http://127.0.0.1:5050`

### 6.3 Validacao Local

```powershell
.\.venv\Scripts\python.exe -m unittest tests_e2e_crud tests_e2e_security tests_e2e_visual
```

---

## 7. Seguranca

| Vulnerabilidade | Protecao / Decisao |
|-----------------|--------------------|
| SQL Injection | SQLAlchemy ORM |
| XSS | Jinja2 auto-escape |
| CSRF | Validacao existente preservada |
| Broken Access Control | Consultas de etapa filtram pela tarefa, `tenant_id` e `user_id` do usuario autenticado |
| IDOR | Validado em `tests_e2e_security.py`; etapa alheia nao pode ser listada, editada, alterada, excluida, reordenada nem aparecer no calendario |
| Mass Assignment | Mapear campos aceitos manualmente no backend |
| Perda de historico | Acoes de status sao registradas em `HistoricoEtapa`; exclusao fisica de etapa remove seu historico nesta versao |

Ponto critico: a feature de etapas cria uma nova superficie de IDOR. Toda rota de etapa precisa garantir que a etapa pertence a uma tarefa do usuario autenticado.

---

## 8. Manutencao e Desenvolvimento

### 8.1 Adicionar Novo Status de Etapa

1. Atualizar a lista central de status permitidos.
2. Ajustar validacao no backend.
3. Ajustar badges na interface.
4. Ajustar regras de transicao de status.
5. Criar/atualizar teste de transicao.

### 8.2 Adicionar Novo Filtro de Etapa

1. Adicionar campo visual no formulario.
2. Capturar parametro na rota.
3. Validar valor recebido contra lista permitida.
4. Aplicar filtro via ORM.
5. Preservar parametro na paginacao.
6. Testar com tarefa de outro usuario para evitar vazamento.

### 8.3 Regras de Transicao de Status

Transicoes sugeridas:

```text
Criada -> Iniciada
Iniciada -> Pausada
Pausada -> Iniciada
Iniciada -> Concluida
Pausada -> Concluida
```

Transicoes a bloquear:

```text
Concluida -> Iniciada
Concluida -> Pausada
```

Se for necessario reabrir etapa concluida, isso deve ser uma decisao explicita e registrada no historico.

---

## 9. Roadmap para esta feature

### 9.1 Legenda de Status

- `[PENDENTE]`: ainda nao implementado.
- `[EM_ANDAMENTO]`: iniciado, mas incompleto.
- `[VALIDAR]`: implementado aparentemente, pendente de teste funcional/visual.
- `[CONCLUIDO]`: implementado e evidenciado.
- `[ADIADO]`: removido do escopo da V5.

### 9.2 Visao Geral do Roadmap

| Fase | Status | Objetivo | Evidencia esperada | Proxima acao |
|------|--------|----------|--------------------|--------------|
| V5-1 - Confirmar modelo atual | [CONCLUIDO] | Ler `models.py`, rotas e banco atual antes de mexer na estrutura. | Confirmado em 20/07/2026: `models.py` possui `Tenant`, `User`, `Categoria` e `Tarefa`; `Tarefa` usa `tenant_id`, `user_id`, `categoria_id` obrigatorio e `categoria_legado`; SQLite real possui tabelas `tenant`, `user`, `categoria` e `tarefa`, com 3 tenants, 3 usuarios, 28 categorias e 334 tarefas; ainda nao existem `etapa` nem `historico_etapa`. | Iniciar V5-2: aprovar desenho final de `Etapa` e `HistoricoEtapa`. |
| V5-1A - Banco de desenvolvimento | [CONCLUIDO] | Separar banco de desenvolvimento do banco principal antes das mudancas estruturais. | Confirmado em 20/07/2026: `.env` usa `APP_ENV=Desenvolvimento`; `app.py` seleciona `tarefas-desenvolvimento.db`; `init_db()` roda migracoes no banco selecionado; banco de desenvolvimento validado com `foreign_keys=1`, `foreign_key_check=0`, 3 tenants, 3 usuarios, 28 categorias e 334 tarefas. | Usar somente `tarefas-desenvolvimento.db` durante a implementacao da V5. |
| V5-2 - Definir modelo de dados | [CONCLUIDO] | Criar desenho final de `Etapa` e `HistoricoEtapa`. | Confirmado em 20/07/2026: `Etapa` e `HistoricoEtapa` terao `tenant_id`, `user_id`, `tarefa_id`, constraints de status/acao, ordem unica por tarefa e escopo seguro; progresso nao sera persistido, sera calculado pelas etapas concluidas. | Iniciar V5-3: preparar migracao local no banco de desenvolvimento. |
| V5-3 - Preparar migracao local | [CONCLUIDO] | Criar backup e atualizar SQLite sem perder tarefas existentes. | Confirmado em 20/07/2026: backup criado em `instance/tarefas-desenvolvimento-backup-pre-v5-etapas-20260720-062333.db`; `local_migrations.py` cria `etapa` e `historico_etapa` de forma idempotente; `tarefas-desenvolvimento.db` validado com `foreign_keys=1`, `foreign_key_check=0`, 3 tenants, 3 usuarios, 28 categorias, 334 tarefas, 0 etapas e 0 historicos. | Iniciar V5-4: implementar models ORM correspondentes ao schema criado. |

| V5-4 - Implementar models ORM | [CONCLUIDO] | Adicionar models e relacionamentos no SQLAlchemy. | Confirmado em 20/07/2026: `models.py` possui `Etapa` e `HistoricoEtapa` alinhados ao schema SQLite; app importa em `APP_ENV=Desenvolvimento`; `db.create_all()` executa sem erro; teste transacional criou etapa/historico, validou relacionamento com `Tarefa.etapas` e fez rollback mantendo 0 etapas e 0 historicos. | Iniciar V5-5: implementar regras de negocio para criacao, status, progresso e historico. |

| V5-5 - Implementar regras de negocio | [CONCLUIDO] | Centralizar criacao, edicao, status, progresso e historico. | Confirmado em 20/07/2026: `routes/routes.py` possui helpers para buscar etapa com escopo seguro, criar/editar etapa, alterar status com transicoes controladas, registrar historico, calcular progresso e reordenar etapas; testes transacionais validaram progresso 50%, historico automatico, bloqueio de transicao `Concluida -> Iniciada`, troca de ordem sem violar constraint e rollback mantendo 0 etapas e 0 historicos. | Iniciar V5-6: criar rotas protegidas de etapas e historico. |

| V5-6 - Implementar rotas | [CONCLUIDO] | Criar rotas protegidas de etapas e historico. | Confirmado em 20/07/2026: rotas protegidas criadas para listar, criar, editar, iniciar, pausar, retomar, concluir, deletar, visualizar historico e reordenar etapas; Flask test client validou GET/POST JSON autenticado, progresso 50%, historico com 5 eventos, bloqueio de transicao invalida, reordenacao, delecao e redirecionamento sem login para `/login?next=...`; banco terminou com 0 etapas, 0 historicos e `foreign_key_check=0`. | Iniciar V5-7: criar templates e interface visual das etapas. |

| V5-7 - Implementar interface | [CONCLUIDO] | Adicionar telas e componentes visuais de etapas. | Confirmado em 20/07/2026: criados `lista_etapas.html`, `cadastro_etapa.html`, `editar_etapa.html` e `historico_etapa.html`; GETs de etapas renderizam HTML por padrao e preservam JSON com `format=json` ou `Accept: application/json`; lista de tarefas recebeu atalho para etapas; Flask test client validou lista, cadastro, edicao, historico e JSON com rollback, mantendo 0 etapas e 0 historicos. | Iniciar V5-8: integrar progresso resumido na lista de tarefas. |

| V5-8 - Integrar progresso na lista | [CONCLUIDO] | Mostrar progresso resumido em `lista_tarefas`. | Confirmado em 20/07/2026: `lista_tarefas` calcula progresso das tarefas da pagina via consulta agrupada em `Etapa`, sem N+1; template mostra `concluidas de total etapas`, barra percentual e estado `Sem etapas`; Flask test client validou tarefa temporaria com 1 de 2 etapas e barra 50%, com rollback mantendo 0 etapas e 0 historicos. | Iniciar V5-9: integrar etapas ao calendario. |

| V5-9 - Integrar calendario | [CONCLUIDO] | Exibir etapas no calendario sem confundir com tarefa principal. | Confirmado em 20/07/2026: `/calendario` envia `tarefas_json` e `etapas_json`; a interface combina tarefas e etapas apenas para visualizacao, mantem KPIs/grafico baseados em tarefas principais, diferencia etapas com card tracejado, badge `Etapa`, pontos marcados e filtro de tipo; etapas nao usam drag-and-drop de tarefa. Flask test client validou tarefa e etapa temporarias no calendario, Node validou sintaxe JS renderizada e rollback manteve 0 etapas e 0 historicos. | Iniciar V5-10: validar seguranca contra acesso cruzado entre usuarios. |
| V5-10 - Validar seguranca | [CONCLUIDO] | Bloquear acesso cruzado entre usuarios. | Confirmado em 20/07/2026: criado `tests_e2e_security.py` com banco SQLite temporario e dois usuarios/tenants; validado que usuario B recebe bloqueio ao tentar listar etapas da tarefa do usuario A, editar etapa alheia, iniciar etapa alheia, ver historico alheio, deletar etapa alheia e reordenar etapa alheia dentro de tarefa propria; calendario de B nao renderiza tarefa/etapa de A. Execucao: `.venv\Scripts\python.exe tests_e2e_security.py` passou com 4 testes. | Iniciar V5-11: criar testes minimos do fluxo principal da feature. |
| V5-11 - Criar testes minimos | [CONCLUIDO] | Cobrir fluxo principal da feature. | Confirmado em 20/07/2026: criado `tests_e2e_crud.py` com `unittest` e app Flask de teste proprio usando SQLite temporario; validado fluxo principal de etapas com criacao, edicao, transicoes `Criada -> Iniciada -> Pausada -> Iniciada -> Concluida`, bloqueio de transicao invalida, historico automatico, progresso 1 de 2 etapas/50%, renderizacao HTML de lista/cadastro/edicao/historico e reordenacao. `tests_e2e_security.py` tambem foi ajustado para usar app de teste proprio e nao tocar no banco real. Execucao: `.venv\Scripts\python.exe -m unittest tests_e2e_crud tests_e2e_security` passou com 7 testes. Banco de desenvolvimento restaurado/validado com `foreign_keys=1`, `foreign_key_check_count=0`, 3 tenants, 3 usuarios, 28 categorias, 334 tarefas, 0 etapas e 0 historicos. | Iniciar V5-12: validacao funcional e visual no servidor local. |
| V5-12 - Validacao funcional e visual | [CONCLUIDO] com ressalva | Confirmar fluxo no navegador/local. | Confirmado em 20/07/2026: criado `tests_e2e_visual.py` com servidor Werkzeug real em `127.0.0.1:5050`, app Flask de teste proprio e SQLite temporario; validado login HTTP, HTML renderizado de `/lista_tarefas`, `/tarefas/<id>/etapas`, `/tarefas/<id>/etapas/nova`, `/etapas/<id>/editar`, `/etapas/<id>/historico`, `/calendario` e JSON de `/tarefas/<id>/etapas?format=json`; verificados progresso 1 de 2/50%, badges/status de etapas, historico, filtro de tipo no calendario e ausencia de `Traceback`/`Internal Server Error`. Revalidado em 21/07/2026 com `.venv\Scripts\python.exe -m unittest tests_e2e_crud tests_e2e_security tests_e2e_visual`, passando com 11 testes. Banco de desenvolvimento preservado com `foreign_keys=1`, `foreign_key_check_count=0`, 3 tenants, 3 usuarios, 28 categorias, 334 tarefas, 0 etapas e 0 historicos. Ressalva: browser integrado indisponivel na validacao inicial (`agent.browsers.list()` retornou `[]`), portanto nao houve screenshot/manual browser real. | Iniciar V5-13: atualizar documentacao final da feature. |
| V5-13 - Atualizar documentacao final | [CONCLUIDO] | Registrar o que foi realmente implementado. | Confirmado em 20/07/2026: `README.md` atualizado com escopo V5, ambiente `.venv`, `APP_ENV=Desenvolvimento`, banco de desenvolvimento, modelos, rotas e comando de validacao; este `mapa_projetoV5.md` atualizado de planejamento para documentacao final da feature, com status, evidencias, ressalvas e decisoes adiadas. Revalidado em 21/07/2026 com `.venv\Scripts\python.exe -m unittest tests_e2e_crud tests_e2e_security tests_e2e_visual`, passando com 11 testes. Banco de desenvolvimento preservado com `foreign_keys=1`, `foreign_key_check_count=0`, 3 tenants, 3 usuarios, 28 categorias, 334 tarefas, 0 etapas e 0 historicos. | V5 encerrada; proximas melhorias devem abrir nova etapa/versao. |

### 9.3 Escopo Funcional da Primeira Entrega

A primeira entrega da V5 deve conter apenas o necessario para tornar etapas utilizaveis:

- criar etapa para uma tarefa;
- listar etapas da tarefa;
- editar etapa;
- alterar status da etapa;
- registrar historico automatico das mudancas de status;
- calcular progresso da tarefa;
- exibir progresso na listagem de tarefas;
- impedir acesso a etapas de outro usuario.

Fica fora da primeira entrega:

- responsavel por etapa;
- peso por etapa;
- dependencia entre etapas;
- etapa obrigatoria/opcional;
- colaboracao entre usuarios;
- API REST externa;
- integracao com Google Calendar;
- aplicativo mobile.

### 9.4 Criterios de Pronto

A feature foi marcada como concluida porque:

- o banco possuir tabelas `etapa` e `historico_etapa` com integridade validada;
- toda etapa estiver vinculada a uma tarefa existente;
- toda consulta de etapa validar o usuario dono da tarefa;
- a ordem das etapas for preservada por tarefa;
- mudancas de status gerarem historico;
- progresso da tarefa for calculado corretamente;
- a listagem de tarefas mostrar progresso sem quebrar filtros e paginacao;
- as telas novas renderizarem no tema atual;
- houver teste local minimo do fluxo principal;
- houve validacao via test client e servidor Werkzeug real das rotas principais.

Ressalva: o browser integrado ficou indisponivel nesta sessao, portanto a validacao visual foi feita por HTML renderizado e servidor local de teste, sem screenshot/manual browser real.

### 9.5 Ordem Recomendada de Implementacao

1. Confirmar modelo atual e estado do SQLite.
2. Aprovar desenho final de `Etapa` e `HistoricoEtapa`.
3. Fazer backup do banco local.
4. Criar models e atualizar banco.
5. Implementar helpers de validacao e progresso.
6. Implementar rotas CRUD de etapas.
7. Implementar historico automatico.
8. Criar templates de etapas.
9. Integrar progresso na lista de tarefas.
10. Integrar etapas ao calendario.
11. Criar testes minimos.
12. Validar visualmente no servidor local.
13. Atualizar status deste roadmap com evidencias.

### 9.6 Resultado Final da V5

A V5 entregou etapas de execucao vinculadas a tarefas, com CRUD, historico automatico, regras de transicao, reordenacao, progresso resumido na lista de tarefas, exibicao no calendario, duplicacao controlada das etapas junto com a tarefa e testes locais de fluxo, seguranca e renderizacao.

Decisoes adiadas para versao futura:

- bloquear conclusao da tarefa quando existirem etapas pendentes;
- responsavel por etapa;
- peso de etapa;
- dependencia entre etapas;
- filtro de status de etapa diretamente na lista de tarefas.

### 9.7 Riscos Tecnicos

| Risco | Severidade | Mitigacao |
|-------|------------|-----------|
| IDOR em rotas de etapa | Alta | Buscar etapa sempre via tarefa do usuario autenticado. |
| Quebra do SQLite local | Alta | Backup antes de qualquer migracao. |
| Regra de progresso duplicada | Media | Centralizar calculo em helper unico. |
| Layout da lista ficar poluido | Media | Exibir progresso compacto e levar detalhes para tela propria. |
| Historico incompleto | Media | Registrar automaticamente toda transicao de status. |
| Overengineering | Media | Nao implementar responsavel, peso e dependencia nesta V5. |

---

## 10. Pos-Producao

### 10.1 Release Inicial

Status: [CONCLUIDO]

Em 28/07/2026, o deploy inicial foi validado em producao para uso pessoal em `todastarefas.com.br`.

Evidencias:

- aplicacao carregou em producao apos configuracao do WSGI;
- rota `/calendario` abriu com usuario autenticado;
- calendario, menu lateral e cards de tarefas/prazos renderizaram com dados reais;
- banco esperado em producao: `instance/tarefas.db`;
- origem do conteudo de producao: `instance/tarefas-desenvolvimento.db` validado na V5;
- ambiente esperado: `APP_ENV=Producao` e `SESSION_COOKIE_SECURE=True`.

Decisao: SQLite esta aceito para o escopo atual de uso pessoal/baixo volume. PostgreSQL, pipeline de CI/CD e hardening de publicacao ampla ficam fora deste release inicial.

### 10.2 Proxima Etapa Separada

Status: [PENDENTE]

Objetivo: tratar ajustes pos-producao sem reabrir a V5 concluida.

Itens iniciais:

- definir rotina de backup do `instance/tarefas.db` no servidor;
- corrigir `DeprecationWarning` de `datetime.utcnow()` com datas timezone-aware;
- revisar pequenos ajustes visuais observados no uso real;
- validar novamente a suite local apos cada correcao;
- manter alteracoes pequenas, rastreaveis e sem mudanca desnecessaria de arquitetura.

---

## Historico de Versoes

| Versao | Data | Destaques |
|--------|------|-----------|
| V1 | Jan 2026 | CRUD de tarefas, autenticacao basica |
| V2 | Jan 2026 | Filtros, paginacao, categorias fixas |
| V3 | Fev 2026 | Categorias dinamicas, comentarios, filtros persistentes |
| V4 | Mar 2026 | Tema dark/light, redesign completo, filtro de busca por texto |
| V5 | Jul 2026 | Etapas de execucao implementadas, historico de etapas, progresso automatico e integracao com calendario |
| V5.1 | Jul 2026 | Etapa pos-producao aberta para backup, warnings de data e ajustes visuais pequenos |

---

**Ultima atualizacao:** 28/07/2026
**Versao do documento:** 5.1
**Mantido por:** Mauricio
