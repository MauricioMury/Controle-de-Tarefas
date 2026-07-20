# Mapa do Projeto - Controle de Tarefas

**Versao:** 5.0
**Data:** 19 - Julho 2026
**Tecnologias:** Flask 3.0, SQLite, Bootstrap 5, Python 3.11+, Syne + DM Sans (Google Fonts)

---

## O que vai ter na V5?

A V5 adiciona a funcionalidade de **etapas de execucao da tarefa**.

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

Cada etapa tera:

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
├── lista_etapas.html              # Planejado V5
├── cadastro_etapa.html            # Planejado V5
├── editar_etapa.html              # Planejado V5
└── historico_etapa.html           # Planejado V5
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
- **V5:** a tarefa podera receber etapas apos a criacao ou durante a edicao, conforme decisao de interface.
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
- **V5 planejado:** exibir resumo de progresso da tarefa, quantidade de etapas concluidas e atalho para abrir as etapas.

#### Edicao de Tarefa
- **Rota:** `/editar_tarefa/<id>`
- **V5 planejado:** exibir bloco de etapas vinculadas, sem transformar o formulario principal em uma tela pesada.

#### Exclusao de Tarefa
- **Rota:** `/deletar_tarefa/<id>` (POST)
- **V5 planejado:** excluir etapas e historicos vinculados por cascade controlado pelo ORM.

#### Marcar como Concluida
- **Rota:** `/marcar_concluida/<id>` (POST)
- **V5 decisao pendente:** definir se a tarefa so podera ser concluida quando todas as etapas estiverem concluidas.

#### Duplicar Tarefa
- **Rota:** `/duplicar_tarefa/<id>`
- **V5 decisao pendente:** definir se a duplicacao copia tambem as etapas como `Criada` ou se copia apenas os campos da tarefa.

---

### 2.3 Gestao de Etapas

#### Planejado V5

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

#### Planejado V5

- A tarefa principal podera ocupar o periodo geral do trabalho.
- As etapas aparecerao individualmente no calendario pela data planejada ou pelo periodo de execucao.

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

Nomes sugeridos em portugues sem acento:

```python
class Etapa(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    tarefa_id      = db.Column(db.Integer, db.ForeignKey("tarefa.id"), nullable=False)
    titulo         = db.Column(db.String(200), nullable=False)
    descricao      = db.Column(db.Text, nullable=True)
    ordem          = db.Column(db.Integer, nullable=False)
    data_planejada = db.Column(db.Date, nullable=True)
    hora_inicio    = db.Column(db.Time, nullable=True)
    hora_fim       = db.Column(db.Time, nullable=True)
    status         = db.Column(db.String(20), nullable=False, default="Criada")
    concluida_em   = db.Column(db.DateTime, nullable=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 3.5 Modelo HistoricoEtapa

```python
class HistoricoEtapa(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    tarefa_id   = db.Column(db.Integer, db.ForeignKey("tarefa.id"), nullable=False)
    etapa_id    = db.Column(db.Integer, db.ForeignKey("etapa.id"), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    acao        = db.Column(db.String(50), nullable=False)
    descricao   = db.Column(db.Text, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
```

### 3.6 Relacionamentos

```text
User (1) -> (N) Tarefa
User (1) -> (N) Categoria
User (1) -> (N) Etapa
User (1) -> (N) HistoricoEtapa

Tarefa (1) -> (N) Etapa
Tarefa (1) -> (N) HistoricoEtapa
Etapa (1) -> (N) HistoricoEtapa
Categoria (1) -> (N) Tarefa
```

Regras de integridade:

- Toda etapa deve pertencer a uma tarefa do mesmo usuario.
- Todo historico deve pertencer a uma etapa e tarefa do mesmo usuario.
- Ao excluir uma tarefa, as etapas e historicos vinculados devem ser tratados de forma explicita e validada.
- `ordem` deve ser unica por tarefa.

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

### 4.3 Rotas Protegidas Planejadas para V5

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

Adicionar informacoes compactas:

- barra ou texto de progresso;
- quantidade de etapas concluidas;
- botao/atalho para etapas;
- filtro por status da tarefa continua existindo;
- filtro por status de etapa pode ser adicionado somente se a query continuar simples e performatica.

### 5.3 Tela de Etapas

A tela de etapas deve priorizar operacao rapida:

- lista ordenada por `ordem`;
- status visivel;
- data planejada;
- botoes de acao por status;
- link para historico;
- formulario simples para nova etapa.

### 5.4 Historico de Etapa

Exibir linha do tempo simples:

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
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Acesse: `http://127.0.0.1:5050`

---

## 7. Seguranca

| Vulnerabilidade | Protecao / Decisao |
|-----------------|--------------------|
| SQL Injection | SQLAlchemy ORM |
| XSS | Jinja2 auto-escape |
| CSRF | Manter validacao existente; avaliar Flask-WTF em etapa tecnica separada |
| Broken Access Control | Toda consulta de etapa deve filtrar por `user_id` da tarefa |
| IDOR | Nunca buscar etapa apenas pelo `id`; validar propriedade pela tarefa e usuario |
| Mass Assignment | Mapear campos aceitos manualmente no backend |
| Perda de historico | Registrar acoes de status em `HistoricoEtapa` |

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
| V5-2 - Definir modelo de dados | [PENDENTE] | Criar desenho final de `Etapa` e `HistoricoEtapa`. | Campos, constraints, defaults e relacionamentos aprovados. | Comparar proposta deste documento com o codigo real. |
| V5-3 - Preparar migracao local | [PENDENTE] | Criar backup e atualizar SQLite sem perder tarefas existentes. | Backup em `instance/` e validacao de integridade do banco. | Planejar script/migracao local com rollback manual. |
| V5-4 - Implementar models ORM | [PENDENTE] | Adicionar models e relacionamentos no SQLAlchemy. | `models.py` compilando e app iniciando. | Implementar somente apos aprovacao. |
| V5-5 - Implementar regras de negocio | [PENDENTE] | Centralizar criacao, edicao, status, progresso e historico. | Funcoes pequenas e reutilizaveis, sem regra espalhada nos templates. | Definir helpers ou service leve conforme codigo atual. |
| V5-6 - Implementar rotas | [PENDENTE] | Criar rotas protegidas de etapas e historico. | Rotas retornando 200/redirect esperado com usuario autenticado. | Implementar CRUD e acoes de status. |
| V5-7 - Implementar interface | [PENDENTE] | Adicionar telas e componentes visuais de etapas. | Templates renderizados sem quebrar layout V4/V5. | Criar telas de lista, cadastro, edicao e historico. |
| V5-8 - Integrar progresso na lista | [PENDENTE] | Mostrar progresso resumido em `lista_tarefas`. | Progresso correto: etapas concluidas / total de etapas. | Ajustar query/contexto da listagem. |
| V5-9 - Integrar calendario | [PENDENTE] | Exibir etapas no calendario sem confundir com tarefa principal. | Calendario mostra tarefa e etapas com leitura clara. | Definir visual e filtro para etapas. |
| V5-10 - Validar seguranca | [PENDENTE] | Bloquear acesso cruzado entre usuarios. | Testes de tentativa de acesso a etapa de outro usuario. | Criar cenarios de IDOR e permissao. |
| V5-11 - Criar testes minimos | [PENDENTE] | Cobrir fluxo principal da feature. | Testes de model, rotas, status, progresso e historico. | Adicionar testes locais sem CI/CD. |
| V5-12 - Validacao funcional e visual | [PENDENTE] | Confirmar fluxo no navegador/local. | Evidencia por test client e conferencia visual. | Rodar app local e validar telas principais. |
| V5-13 - Atualizar documentacao final | [PENDENTE] | Registrar o que foi realmente implementado. | Este arquivo atualizado com status e evidencias reais. | Atualizar apos implementacao validada. |

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

A feature so deve ser marcada como concluida quando:

- o banco possuir tabelas `etapa` e `historico_etapa` com integridade validada;
- toda etapa estiver vinculada a uma tarefa existente;
- toda consulta de etapa validar o usuario dono da tarefa;
- a ordem das etapas for preservada por tarefa;
- mudancas de status gerarem historico;
- progresso da tarefa for calculado corretamente;
- a listagem de tarefas mostrar progresso sem quebrar filtros e paginacao;
- as telas novas renderizarem no tema atual;
- houver teste local minimo do fluxo principal;
- houver validacao manual ou via test client das rotas principais.

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

### 9.6 Riscos Tecnicos

| Risco | Severidade | Mitigacao |
|-------|------------|-----------|
| IDOR em rotas de etapa | Alta | Buscar etapa sempre via tarefa do usuario autenticado. |
| Quebra do SQLite local | Alta | Backup antes de qualquer migracao. |
| Regra de progresso duplicada | Media | Centralizar calculo em helper unico. |
| Layout da lista ficar poluido | Media | Exibir progresso compacto e levar detalhes para tela propria. |
| Historico incompleto | Media | Registrar automaticamente toda transicao de status. |
| Overengineering | Media | Nao implementar responsavel, peso e dependencia nesta V5. |

---

## Historico de Versoes

| Versao | Data | Destaques |
|--------|------|-----------|
| V1 | Jan 2026 | CRUD de tarefas, autenticacao basica |
| V2 | Jan 2026 | Filtros, paginacao, categorias fixas |
| V3 | Fev 2026 | Categorias dinamicas, comentarios, filtros persistentes |
| V4 | Mar 2026 | Tema dark/light, redesign completo, filtro de busca por texto |
| V5 | Jul 2026 | Planejamento de etapas de execucao, historico de etapas e progresso automatico |

---

**Ultima atualizacao:** 19/07/2026
**Versao do documento:** 5.0
**Mantido por:** Mauricio
