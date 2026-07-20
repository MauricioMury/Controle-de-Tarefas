# Controle de Tarefas - Project Context

Início do projeto: 2026-06-19

## Índice

- [Nome](#nome)
- [Descrição](#descrição)
- [Arquivos críticos do projeto Controle de Tarefas](#arquivos-críticos-do-projeto-controle-de-tarefas)
- [Objetivos](#objetivos)
- [Arquitetura](#arquitetura)
  - [Backend](#backend)
  - [Frontend](#frontend)
- [Segurança](#segurança)
  - [Autenticação](#autenticação)
  - [Senhas](#senhas)
  - [Controle de Acesso](#controle-de-acesso)
  - [Login](#login)
  - [Registro de usuário](#registro-de-usuário)
  - [Multi-Tenant](#multi-tenant)
  - [Uploads](#uploads)
  - [Sanitização](#sanitização)
  - [Vulnerabilidades a Monitorar](#vulnerabilidades-a-monitorar)
- [Banco de Dados](#banco-de-dados)
- [Observabilidade](#observabilidade)
- [Qualidade de Código](#qualidade-de-código)
- [Estrutura de Testes](#estrutura-de-testes)
- [Roadmap](#roadmap)
- [Correção de Rumo, para rodar como MVP local](#correção-de-rumo-para-rodar-como-mvp-local)
  - [Status da Correção de Rumo](#status-da-correção-de-rumo)
  - [Direção Técnica Atual](#direção-técnica-atual)
  - [Roadmap do MVP local baseado nas telas atuais](#roadmap-do-mvp-local-baseado-nas-telas-atuais)
  - [MVP-1 - Estabilizar ambiente local](#mvp-1---estabilizar-ambiente-local)
  - [MVP-2 - Consolidar modelo e banco SQLite](#mvp-2---consolidar-modelo-e-banco-sqlite)
  - [MVP-3 - Retirar rotas do `app.py` e mover para `routes.py`](#mvp-3---retirar-rotas-do-apppy-e-mover-para-routespy)
  - [MVP-4 - Separar lógica de negócio sem overengineering](#mvp-4---separar-lógica-de-negócio-sem-overengineering)
  - [MVP-5 - Validar fluxo principal do usuário](#mvp-5---validar-fluxo-principal-do-usuário)
  - [MVP-6 - Testes locais mínimos](#mvp-6---testes-locais-mínimos)
  - [MVP-7 - Ajustes visuais e usabilidade](#mvp-7---ajustes-visuais-e-usabilidade)
- [Etapas de Correção de Rumo](#etapas-de-correção-de-rumo)
  - [1 - Cadastros, Listagens, Dashboard e Calandário](#1---cadastros-listagens-dashboard-e-calandário)
  - [2 - Remover segredos hardcoded do código](#2---remover-segredos-hardcoded-do-código)
  - [3 - Modularizar o backend sem mudar comportamento](#etapa-3-modularizar-backend)
  - [4 - Organizar o acesso ao banco](#etapa-4-organizar-acesso-banco)
  - [5 - Melhorar o dashboard](#5---melhorar-o-dashboard)
  - [6 - Criar testes locais mínimos](#6---criar-testes-locais-mínimos)
  - [7 - Atualizar documentação e roadmap](#7---atualizar-documentação-e-roadmap)
  - [8 - Preparar para publicação futura, sem implementar agora](#8---preparar-para-publicação-futura-sem-implementar-agora)
- [Em 25/06/2026](#em-25062026)
- [Restrições Absolutas](#restrições-absolutas)

---

## Nome

Controle de Tarefas

---

## Descrição

Controle de Tarefas é um Web Application de gerenciamento de tarefas, multi-tenant.

O sistema permite que usuários armazenem e gerenciem tarefas de forma segura, mantendo isolamento completo entre tenants.

Vamos ter uma interface web moderna e responsiva, com foco em segurança, simplicidade e confiabilidade.

Vamos ter um backend robusto e seguro, seguindo as melhores práticas de desenvolvimento secure-by-design.

Vamos ter um processo de desenvolvimento iterativo, com entregas frequentes e feedback constante para garantir que o produto atenda às necessidades dos usuários e mantenha os mais altos padrões de segurança.

Vamos priorizar a segurança em todas as etapas do desenvolvimento, desde a arquitetura até a implementação e testes, para garantir que o Controle de Tarefas seja um gerenciador de tarefas confiável e seguro para todos os usuários.

Vamos seguir um roadmap claro, com funcionalidades bem definidas e entregas planejadas, para garantir um desenvolvimento organizado e eficiente do Controle de Tarefas.

# Arquivos críticos do projeto Controle de Tarefas

- `local/context.md` – resumo do escopo, requisitos de segurança e arquitetura.
- `local/agent.md` – detalhes sobre o agente de IA, suas habilidades e limitações.
- `local/code-review-skill.md` – critérios e processos para revisão de código.
- `shared/instrucoes.md` – diretrizes de comportamento e operação que a IA deve seguir rigorosamente.
- `shared/knowledgebase.md` – informações relevantes para o projeto, como conceitos de segurança, melhores práticas e referências.
- `README.md` – visão geral do projeto e instruções de setup.

---

# Objetivos

Principais objetivos:

* Segurança
* Simplicidade
* Confiabilidade
* Auditabilidade
* Escalabilidade futura

---

# Arquitetura

## Backend

Tecnologias:

* Python 3.13+
* FastAPI
* SQLAlchemy 2.x
* Alembic
* SQLite

Padrão arquitetural:

Controller → Service → Persistence

Fluxo:

Request
→ Controller
→ Service
→ Repository
→ Database

---

## Frontend

Tecnologias:

* React 19
* TypeScript
* Vite
* TailwindCSS v4
* Motion
* Recharts

Princípios:

* Componentes reutilizáveis
* Baixo acoplamento
* Separação UI e lógica
* Serviços centralizados
* Sem acesso direto a APIs externas

Fluxo:

Component
→ Hook
→ Service
→ API Client

---

# Segurança

Prioridade máxima.

---

## Autenticação

JWT Authentication

Requisitos:

* Access Token
* Refresh Token
* Expiração configurável
* Revogação futura prevista

---

## Senhas

Hash obrigatório:

* bcrypt

Nunca:

* MD5
* SHA1
* SHA256 puro

---

## Controle de Acesso

Cada usuário acessa apenas:
* seu tenant
* seus cofres
* suas credenciais

# Login 
* Nunca permitir login com e-mail inexistente.
* A senha deve ter pelo menos 12 caracteres, incluindo letras maiúsculas, minúsculas, números e símbolos.
* A página de criação de senha deve mostrar um indicador de força da senha.
* A página deve mostrar quando a senha atender a cada critério de complexidade.
* A página deve mostrar quando na confirmação de senha, se elas estão conincidentes.
* Deverá haver um mecanismo de recuperação de senha, que envie um link de redefinição para o e-mail do usuário, com token de expiração curta, e que permita criar uma nova senha seguindo os mesmos critérios de complexidade.
* Bloquear conta após 10 tentativas de login falhadas, avisando que será reativada após 20 minutos.
* 

# Registro de usuário
Requisitos:
* Nunca registar usuário com e-mail já existente.
* Ao se registrar o sistema deve enviar um e-mail de confirmação, com um link mágico para ativar a conta, e colocar o usário dentro do sistema, já que atendeu a todos os critérios de identificação, e o link deve conter um token de expiração curta.

Toda consulta deve aplicar:

tenant_id
user_id

---

## Multi-Tenant

Modelo:

Shared Database
Shared Schema

Isolamento lógico obrigatório.

Toda entidade deve conter:

* tenant_id

---

## Uploads

Todo upload deve:

* Validar MIME Type
* Validar extensão
* Validar tamanho
* Validar conteúdo real
* Bloquear arquivos executáveis

---

## Sanitização

Validar:

* Entradas HTTP
* Campos de formulário
* Importações
* Exportações

---

## Vulnerabilidades a Monitorar

* SQL Injection
* Formula Injection
* XSS
* CSRF
* SSRF
* Path Traversal
* Upload Inseguro
* Broken Access Control
* IDOR
* Session Fixation
* Privilege Escalation

---

# Banco de Dados

ORM obrigatório:

* SQLAlchemy

Migrações:

* Alembic

Nunca:

* SQL manual nunca


---

# Observabilidade

Logs obrigatórios para:

* Login
* Logout
* Falhas de autenticação
* Alteração de senha
* Criação de credenciais
* Exclusão de credenciais
* Alterações administrativas

Nunca registrar:

* Senhas
* Tokens
* Secrets
* Dados criptográficos

---

# Qualidade de Código

Priorizar:

* Legibilidade
* Simplicidade
* Segurança
* Testabilidade
* Manutenibilidade

Evitar:

* Código duplicado
* Dependências desnecessárias
* Acoplamento excessivo
* Funções longas
* Classes longas

---

# Estrutura de Testes

Obrigatória:

* tests_e2e_llm.py
* tests_e2e_crud.py
* tests_e2e_security.py
* tests_e2e_alembic.py

---

# Roadmap

O Roadmap sofreu uma "Correção de Rumo", verifique depois do "Roadmap"

| Fase | Nome | Duração (sprints) | Principais entregas | Objetivo principal | Status |
|------|------|-------------------|---------------------|--------------------|--------|

| **1** | **Fundação & Arquitetura** | 2‑3 | 
• Repositório Git inicializado ✅
• Estrutura de pastas (backend, frontend, docs) 
• Configuração de CI/CD básica (GitHub Actions) 
• Definição de contratos de API (OpenAPI/Swagger) 
• Modelo de dados inicial (SQLAlchemy + migrações Alembic) 
• Boilerplate React + Vite + Tailwind | Garantir que a base do projeto esteja estável, versionada e com padrões de código definidos. 
| Concluído |

| **2** | **Autenticação & Segurança Básica** | 2‑3 | 

Implementação de JWT (access + refresh)	
Endpoints /auth/register e /auth/login	
Hash de senhas com bcrypt	
Middleware de validação de token e controle de tenant	
Política de CORS e headers de segurança	
Bloqueio de conta após 10 tentativas falhas (20 min)	
Revogação de tokens (endpoint /auth/logout + verificação no middleware)	
Testes unitários de fluxo de autenticação	
Testes de segurança adicionais (lockout e revogação)	
Migrações Alembic para os novos campos e tabela de tokens revogados	
| Concluído |

| **3** | **Gerenciamento de Credenciais (CRUD)** | 3‑4 | 
• Endpoints para criar, ler, atualizar e excluir credenciais 
• Modelos de domínio com `tenant_id` e `user_id` 
• Validação de entrada (pydantic) 
• Criptografia de senhas armazenadas (AES‑GCM) 
• UI de listagem e detalhe de credenciais 
• Testes de integração (FastAPI TestClient) | 
• Disponibilizar a funcionalidade central do cofre de senhas, com isolamento multi‑tenant. ✅

| Concluída |

| **4** | **Recuperação & Reset de Senha** | 2‑3 | 
• Endpoint de “forgot password” que gera token de curto prazo 
• E‑mail de recuperação (SMTP mock + template) <br>
• Página de redefinição com validação de força de senha <br>
• Testes de fluxo completo de recuperação | 
• Permitir que usuários recuperem acesso de forma segura, seguindo as políticas de complexidade. 
| Pendente |

| **5** | **Upload Seguro de Arquivos** | 2‑3 | 
• API de upload com validação de MIME, extensão, tamanho e conteúdo <br>
• Armazenamento em diretório protegido (ou bucket S3 local) <br>
• Integração UI para anexar fotos às credenciais <br>
• Testes de segurança (verificação de arquivos executáveis) 
|Suportar anexos (fotos, documentos) sem abrir vetores de ataque.|
| Pendente |

| **6** | **Auditoria & Log** | 2 | • Estrutura de logs centralizada (JSON + Loguru) <br>• Registro de ações críticas (login, criação/edição de credenciais, upload) <br>• Dashboard de auditoria (lista filtrável) <br>• Testes de integridade de logs | Garantir rastreabilidade e facilitar investigações de segurança. | Pendente |

| **7** | **Teste de Performance & Escalabilidade** | 1‑2 | • Benchmark de endpoints críticos (locust) <br>• Estratégia de cache (Redis) para tokens e consultas frequentes <br>• Documentação de limites de taxa (rate‑limiting) | Verificar que o sistema aguenta carga crescente e preparar para futuro multi‑tenant em escala. | Pendente |

| **8** | **Polimento UI/UX & Responsividade** | 2‑3 | • Refatoração de componentes React (hooks reutilizáveis) <br>• Animações com **Motion** e gráficos com **Recharts** <br>• Testes de acessibilidade (axe) <br>• Suporte a temas claros/escuros | Entregar uma experiência de usuário moderna, intuitiva e acessível. | Pendente |

| **9** | **Hardening & Pen‑Testing** | 2 | • Revisão de dependências (npm audit, pip-audit) <br>• Testes de penetração internos (OWASP ZAP) <br>• Aplicação de patches de segurança (CSP, HSTS, Referrer‑Policy) | Eliminar vulnerabilidades conhecidas antes do lançamento. | Pendente |

| **10** | **Release & Deploy** | 1‑2 | • Pipeline de CI/CD completo (build, test, lint, deploy) <br>• Deploy em ambiente de staging (Docker + Docker‑Compose) <br>• Estratégia de rollout gradual (blue‑green) <br>• Documentação de release notes | Disponibilizar a primeira versão estável para usuários finais. | Pendente |

---

# Correção de Rumo, para rodar como MVP local

O projeto deve ser tratado, neste momento, como um **Controle de Tarefas Local**:

→ Flask local  
→ SQLite local  
→ Persistência local para consulta e análise  
→ Dashboard local para visualização rápida  
→ Modularização   
→ Preparado para segurança futura, mas sem login agora  

O objetivo atual não é publicar o sistema na internet, nem implementar autenticação, multi-tenant, JWT, React ou GitHub Actions. O objetivo atual é ter uma ferramenta local, organizada, confiável e fácil de evoluir.

Segurança, login, multi-tenant, publicação externa, CI/CD e troca futura para FastAPI/SQLAlchemy/Alembic ficam como requisitos futuros. Eles devem influenciar a organização do código, mas não devem bloquear a evolução do MVP local.

## Status da Correção de Rumo

Última atualização do status: 2026-07-19.

Legenda:

- [CONCLUIDO]: tarefa implementada e evidenciada no código ou na documentação.
- [PARCIAL]: tarefa iniciada, mas ainda incompleta ou com ressalvas técnicas.
- [PENDENTE]: tarefa ainda não implementada.
- [VALIDAR]: há implementação aparente, mas falta validação funcional ou visual.
- [FUTURO]: item mantido como direção futura, mas não deve bloquear o MVP local.

| Item | Status | Evidência atual | Próxima ação |
|------|--------|-----------------|--------------|
| [CONCLUIDO] MVP-1 - Estabilizar ambiente local | [CONCLUIDO] | `requirements.txt`, `README.md`, SQLite local, porta `5050`, `notificacoes.py` e `SECRET_KEY` obrigatório definidos. | Manter validação de ambiente antes de novas mudanças estruturais. |
| [CONCLUIDO] MVP-2 - Consolidar modelo e banco SQLite | [CONCLUIDO] | `instance/tarefas.db`, backups em `instance/`, `categoria_id`, coluna legada `categoria`, `foreign_keys=1` e `foreign_key_check_count=0` validados. | Manter backup antes de qualquer nova migração de banco. |
| [CONCLUIDO] MVP-3 - Retirar rotas do `app.py` e mover para `routes.py` | [CONCLUIDO] com ressalva | Rotas principais em `routes/routes.py` e autenticação/perfil em `routes/auth.py`. | Manter monitoramento para não voltar regra de negócio para `app.py`. |
| [CONCLUIDO] MVP-4 - Separar lógica de negócio sem overengineering | [CONCLUIDO] | Helpers de parsing, categoria e montagem/aplicação de tarefa concentraram validações reutilizadas em `routes/routes.py`. | Evitar nova camada service/repository até haver repetição real maior. |
| [CONCLUIDO] MVP-5 - Validar fluxo principal do usuário | [CONCLUIDO] | Fluxo validado com Flask test client: login, telas principais, categoria, tarefa, filtro, edição, calendário, duplicação, movimentação, conclusão, entrada rápida e exclusão. | Manter validação manual visual como apoio no MVP-7. |
| [PENDENTE] MVP-6 - Testes locais mínimos | [PENDENTE] | Não há testes locais mínimos identificados no projeto. | Criar testes para integridade do banco, `categoria_id`, bloqueio de exclusão de categoria em uso e renderização das rotas principais. |
| [CONCLUIDO] MVP-7 - Ajustes visuais e usabilidade | [CONCLUIDO] com ressalva | Ajustados espaçamentos mobile, botões de formulário, ações de tabela, largura mínima de tabelas, contraste de badge claro e painéis internos sem card dentro de card. Rotas principais renderizadas com sucesso. | Fazer conferência visual manual em `http://127.0.0.1:5050` quando o servidor local estiver aberto. |
| [PARCIAL] Etapa 1 - Cadastros, Listagens, Dashboard e Calendário | [PARCIAL] | Templates e rotas existem para cadastros, listagens, dashboard inicial e calendário. | Validar dados reais vindos do SQLite e corrigir divergências de categoria/status. |
| [CONCLUIDO] Etapa 2 - Remover segredos hardcoded | [CONCLUIDO] | `SECRET_KEY` lê `.env` ou ambiente e não possui fallback dinâmico no código. | Criar `.env` local antes de iniciar a aplicação em ambiente novo. |
| [CONCLUIDO] Etapa 3 - Modularizar backend sem mudar comportamento | [CONCLUIDO] com ressalva | `app.py`, `models.py`, `routes/routes.py` e `routes/auth.py` separados. | Não expandir arquitetura antes de estabilizar testes e fluxo principal. |
| [PARCIAL] Etapa 4 - Organizar acesso ao banco | [PARCIAL] | O projeto usa SQLAlchemy ORM nos fluxos principais. | Confirmar se ainda existe SQL manual relevante em scripts auxiliares e se ele é apenas migração local controlada. |
| [PARCIAL] Etapa 5 - Melhorar dashboard | [PARCIAL] | Dashboard inicial existe e lista de tarefas tem paginação/filtros. | Confirmar se ainda faz sentido criar `/api/dashboard/summary` no MVP Flask atual. |
| [PENDENTE] Etapa 6 - Criar testes locais mínimos | [PENDENTE] | Não há suíte de testes local identificada. | Criar testes mínimos antes de novas refatorações estruturais. |
| [PARCIAL] Etapa 7 - Atualizar documentação e roadmap | [PARCIAL] | `context.md` recebeu índice e status da correção de rumo. | Corrigir inconsistências antigas do documento, especialmente trechos herdados de PostgreSQL, FastAPI, React e password manager. |
| [PARCIAL] Etapa 8 - Preparar para publicação futura sem implementar agora | [PARCIAL] | Headers de segurança, CSRF e separação básica já existem. | Manter como requisito futuro sem bloquear o MVP local; evitar novas dependências agora. |

### Direção Técnica Atual

- Manter Flask por enquanto.
- Manter HTML/templates por enquanto.
- Não implementar autenticação neste ciclo.
- Não depender de Git/GitHub neste ciclo.
- Remover segredos hardcoded do código.
- Organizar o projeto para permitir evolução futura sem reescrita completa.

### Roadmap do MVP local baseado nas telas atuais

Referências visuais usadas:

- `references/Captura de tela 2026-07-11 Inicio.png`
- `references/Captura de tela 2026-07-11 MinhasTarefa.png`
- `references/Captura de tela 2026-07-11 NovaTarefa.png`
- `references/Captura de tela 2026-07-11 Categorias.png`
- `references/Captura de tela 2026-07-11 Calendario.png`
- `references/Captura de tela 2026-07-11 EntradaRapida.png`

Objetivo do MVP local:

Ter um Controle de Tarefas local, executando em Flask + SQLite, com navegação estável pelas telas de Início, Nova Tarefa, Minhas Tarefas, Categorias, Calendário e Entrada Rápida. O foco é uso pessoal/local, persistência confiável, consulta rápida e código organizado para evolução futura.

Escopo funcional mínimo:

1. Início
   - Exibir KPIs de total, pendentes, concluídas, alta prioridade e tarefas de hoje.
   - Manter atalhos para Nova Tarefa, Minhas Tarefas, Pendentes e Categorias.
   - Garantir que os números venham do banco SQLite local.

2. Minhas Tarefas
   - Listar tarefas com data, hora, prioridade, categoria, status e ações.
   - Manter filtros por busca, categoria, prioridade, status e data.
   - Manter paginação e seleção de quantidade por página.
   - Garantir que a categoria exibida venha de `categoria.nome`, via relacionamento com `tarefa.categoria_id`.

3. Nova Tarefa
   - Cadastrar tarefa com título, comentário, data meta, data realizada, hora início, hora fim, prioridade, recorrência, categoria e notificações.
   - Salvar `categoria_id`, não texto de categoria.
   - Validar que a categoria selecionada existe antes de salvar.

4. Categorias
   - Listar, criar, editar e excluir categorias.
   - Bloquear exclusão de categoria vinculada a tarefas.
   - Usar `categoria.id` como chave de relacionamento e `categoria.nome` apenas para exibição.

5. Calendário
   - Exibir KPIs do mês, gráfico por dia da semana, filtros e calendário mensal.
   - Mostrar tarefas do dia selecionado com categoria, prioridade e status.
   - Manter movimentação de tarefa por data sem quebrar o relacionamento de categoria.

6. Entrada Rápida
   - Permitir criação rápida de tarefa por texto livre.
   - Usar categoria padrão `Rápida` quando existir; caso contrário, usar a primeira categoria disponível.
   - Enviar `categoria_id` no formulário oculto.

Roadmap técnico para rodar como MVP local:

### MVP-1 - Estabilizar ambiente local [CONCLUIDO]

- Criar/atualizar lista mínima de dependências do Flask local.
- Garantir que o app rode com um único comando documentado.
- Definir porta local padrão.
- Confirmar existência dos arquivos obrigatórios importados pelo app, incluindo módulos auxiliares como notificações.
- Manter `.env` local para `SECRET_KEY` e parâmetros sensíveis.

### MVP-2 - Consolidar modelo e banco SQLite [CONCLUIDO]

- Manter `instance/tarefas.db` como banco local do MVP.
- Garantir backup antes de qualquer migração.
- Manter relacionamento `tarefa.categoria_id -> categoria.id`.
- Preservar a coluna textual antiga `tarefa.categoria` apenas como legado temporário.
- Validar `PRAGMA foreign_key_check` depois de mudanças estruturais.
- Ativar foreign keys do SQLite na inicialização da aplicação.

### MVP-3 - Retirar rotas do `app.py` e mover para `routes.py` [CONCLUIDO]

- Deixar `app.py` responsável apenas por criar/configurar a aplicação, inicializar extensões, registrar rotas e iniciar o servidor local.
- Criar `routes.py` para concentrar as rotas atuais.
- Mover para `routes.py` as rotas de:
  - autenticação local existente, se permanecer temporariamente;
  - perfil;
  - categorias;
  - tarefas;
  - calendário;
  - entrada rápida;
  - ações auxiliares como duplicar, mover, concluir e deletar tarefas.
- Manter os nomes das rotas atuais para não quebrar `url_for` nos templates.
- Não alterar comportamento durante essa extração; primeiro mover, depois refatorar.

### MVP-4 - Separar lógica de negócio sem overengineering [CONCLUIDO]

- Criar helpers pequenos apenas onde houver repetição real.
- Concentrar validações de tarefa e categoria em funções reutilizáveis.
- Evitar criar camadas complexas antes do MVP local estar rodando bem.
- Preparar futura separação em services/repositories, mas sem bloquear a entrega local.

### MVP-5 - Validar fluxo principal do usuário [CONCLUIDO]

- Login local, se mantido neste ciclo.
- Abrir tela Início.
- Criar categoria.
- Criar tarefa usando categoria.
- Listar tarefa filtrando por categoria.
- Editar tarefa e trocar categoria.
- Ver tarefa no calendário.
- Criar tarefa pela entrada rápida.
- Concluir, duplicar, mover e excluir tarefa.

### MVP-6 - Testes locais mínimos [PENDENTE]

- Criar teste de integridade do banco: contagem de tarefas e join com categorias.
- Criar teste de criação de tarefa com `categoria_id`.
- Criar teste de bloqueio de exclusão de categoria em uso.
- Criar teste de renderização das principais rotas com usuário local autenticado ou contexto controlado.
- Não transformar isso em CI/CD agora.

### MVP-7 - Ajustes visuais e usabilidade [CONCLUIDO]

- Padronizar espaçamentos entre telas.
- Garantir que filtros e botões fiquem legíveis em resolução menor.
- Revisar contraste dos badges de categoria.
- Manter a experiência atual dark/local sem redesenhar o sistema inteiro.

Critério de pronto do MVP local:

- O sistema inicia localmente sem erro de importação.
- O banco SQLite abre e responde.
- Todas as telas das referências carregam.
- CRUD de tarefas funciona.
- CRUD de categorias funciona.
- Categoria da tarefa é salva por `categoria_id`.
- Listagem e calendário exibem `categoria.nome`.
- Entrada rápida cria tarefa válida.
- Existe backup antes de mudanças de banco.
- Há pelo menos validação local mínima documentada.

# Etapas de Correção de Rumo

As etapas devem seguir esta ordem:

### 1 - Cadastros, Listagens, Dashboard e Calandário
- Se basear no código atual dos arquivos da pasta tmplates.
- O banco de dados estará na pasta "instance".
- Gerar models de acordo com as tabelas do banco de dados.
- .

### 2 - Remover segredos hardcoded do código 
- Tornar `.env` obrigatório para credenciais e parâmetros sensíveis.
- Remover senha hardcoded como fallback em `db_config.py`.
- Validar o `docker-compose.yml` atual para PostgreSQL.
- Avaliar depois se o `docker-compose.yml` também deve subir a aplicação Flask, além do banco.

<a id="etapa-3-modularizar-backend"></a>

### 3 - Modularizar o backend sem mudar comportamento ✅

- Separar o `app.py` em módulos menores.
- Criar camada de configuração.
- Criar camada de conexão com banco.
- Criar camada de repository para SQL e persistência.
- Criar camada de service para coleta, normalização e orquestração.
- Criar camada de routes para endpoints e páginas.
- Manter as mesmas rotas funcionando durante a refatoração.

Estrutura inicial sugerida:

```text
app/
├── __init__.py
├── config.py
├── database.py
├── routes/
│   ├── pages.py
│   └── alerts.py
├── services/
│   └── alert_service.py
└── repositories/
    └── alert_repository.py
```

<a id="etapa-4-organizar-acesso-banco"></a>

### 4 - Organizar o acesso ao banco ✅

- Remover SQL espalhado do `app.py`.
- Concentrar comandos SQL em repositories.
- Manter PostgreSQL.
- Manter `psycopg2` nesta etapa.
- Deixar SQLAlchemy/Alembic como evolução futura, quando a estrutura estiver estável.

### 5 - Melhorar o dashboard

- Criar endpoint JSON próprio para estatísticas.
- Separar página visual de dados da API.
- Manter `/dashboard` como página HTML.
- Criar `/api/dashboard/summary` para dados consolidados.
- Criar, se necessário, endpoints adicionais para tabelas e filtros.
- ✅Feito. Adicionei paginação na tabela do dashboard com seleção de 10, 25 ou 50 registros.

# Em 25/06/2026
Ok. O estado atual ficou assim:
Banco limpo, estrutura preservada.
Flask funcionando.
Dashboard respondendo.
Persistência corrigida para salvar os alertas reais da API.
/fetch_alerts validado com retorno 200.
Dashboard zerado e pronto para nova busca por data.
Amanhã podemos continuar a partir da validação da busca por intervalo de data e conferência da quantidade de WB-* retornados/salvos.


### 6 - Criar testes locais mínimos

- Criar testes simples para validar parsing/processamento dos dados.
- Criar teste de inserção usando amostra controlada.
- Criar teste de retorno dos endpoints principais.
- Não transformar isso ainda em pipeline de CI/CD.

### 7 - Atualizar documentação e roadmap

- Registrar que o projeto atual é local-first.
- Remover Git/GitHub Actions como dependência atual.
- Registrar Docker como base operacional local.
- Registrar autenticação, publicação externa, multi-tenant, FastAPI, SQLAlchemy e Alembic como etapas futuras.

### 8 - Preparar para publicação futura, sem implementar agora

- Evitar segredos no código.
- Evitar acoplamento forte entre rotas, banco e dashboard.
- Manter camadas bem separadas.
- Deixar espaço para autenticação futura.
- Deixar espaço para migração futura para FastAPI/SQLAlchemy, se necessário.

# Restrições Absolutas

Nunca:

* Armazenar segredos em frontend.
* Expor credenciais em logs.
* Ignorar tenant_id.
* Ignorar user_id.
* Ignorar autenticação.
* Ignorar autorização.
* Utilizar acesso direto ao banco sem ORM.

Ao chegar sua leitura aqui informe: "Li e compreendi o arquivo context.md."
