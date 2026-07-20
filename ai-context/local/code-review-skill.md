# Skill: Code Review

## Propósito

Realizar revisões técnicas de código garantindo que toda alteração esteja alinhada com os padrões arquiteturais, requisitos de segurança, objetivos de negócio e diretrizes técnicas do Financeiro AI Studio.

Esta skill deve ser aplicada sempre que houver:

* Pull Requests
* Revisões de código
* Refatorações
* Novas funcionalidades
* Correções de bugs
* Alterações arquiteturais
* Revisões de segurança

---

# Objetivos da Revisão

Toda revisão deve avaliar cinco dimensões obrigatórias:

1. Segurança
2. Arquitetura
3. Performance
4. Manutenibilidade
5. Aderência ao Projeto

Nenhuma dessas áreas deve ser ignorada.

---

# Formato da Revisão

A análise deve seguir obrigatoriamente a estrutura:

## Resumo Executivo

Breve avaliação geral da alteração.

Classificação:

* Aprovado
* Aprovado com ressalvas
* Requer ajustes
* Rejeitado

---

## Segurança

Identificar:

* SQL Injection
* Formula Injection
* XSS
* CSRF
* Path Traversal
* Upload inseguro
* Exposição de segredos
* Escalada de privilégios
* Autorização inadequada
* Vazamento de dados

Verificar:

* Uso correto de JWT
* Isolamento por usuário
* Validação de entrada
* Sanitização de dados
* Tratamento seguro de erros

Perguntas obrigatórias:

* Existe risco de acesso indevido?
* Existe risco de vazamento de informações?
* Existe risco de execução de conteúdo malicioso?

---

## Arquitetura

Verificar aderência à arquitetura oficial.

### Backend

Padrão esperado:

```text
API
→ Service
→ Repository / CRUD
→ Banco
```

Evitar:

* Lógica de negócio dentro de endpoints
* SQL espalhado pelo sistema
* Dependências circulares
* Acoplamento excessivo

### Frontend

Padrão esperado:

```text
View
→ Service
→ Adapter
→ API
```

Evitar:

* Chamadas HTTP dentro de componentes
* Lógica de negócio na interface
* Dependência direta de Firebase

Perguntas obrigatórias:

* A alteração respeita a arquitetura?
* Existe acoplamento desnecessário?
* Há quebra de separação de responsabilidades?

---

# Performance

Avaliar:

* Consultas ao banco
* Consumo de memória
* Complexidade de algoritmos
* Loops desnecessários
* Requisições redundantes
* Processamento excessivo

Verificar:

* Uso correto de índices
* Paginação quando aplicável
* Operações assíncronas
* Evitar N+1 queries

Perguntas obrigatórias:

* Existe gargalo evidente?
* A solução escala?
* O consumo de recursos é adequado?

---

# Manutenibilidade

Avaliar:

* Clareza do código
* Legibilidade
* Organização
* Reutilização
* Facilidade de testes

Evitar:

* Métodos gigantes
* Classes excessivamente complexas
* Duplicação de código
* Números mágicos
* Hardcodes

Verificar:

* Nomes claros
* Responsabilidades bem definidas
* Comentários relevantes
* Baixo acoplamento

Perguntas obrigatórias:

* Outro desenvolvedor entenderia rapidamente este código?
* A manutenção futura será simples?
* Existe oportunidade de refatoração?

---

# Aderência ao Projeto

Verificar conformidade com as decisões registradas no contexto do projeto.

## Banco de Dados

Permitido:

* PostgreSQL
* SQLAlchemy

Não permitido:

* Firestore como solução principal
* SQLite em produção

---

## Backend

Permitido:

* FastAPI
* SQLAlchemy Async
* Alembic

Verificar:

* Uso correto dos schemas
* Uso correto dos CRUDs
* Uso correto da autenticação

---

## Frontend

Permitido:

* React 19
* TypeScript
* Vite
* Adapter Pattern

Verificar:

* Uso do apiAdapter
* Uso do Service Layer

Evitar:

* Firebase direto
* Chamadas diretas ao Gemini

---

## IA

Obrigatório:

```text
Frontend
→ FastAPI
→ /llm
→ Gemini
```

Nunca:

```text
Frontend
→ Gemini
```

---

# Classificação de Problemas

## Crítico

Deve bloquear aprovação.

Exemplos:

* Vulnerabilidades
* Vazamento de segredos
* Falhas de autenticação
* Quebra arquitetural grave

---

## Alto

Deve ser corrigido antes do merge.

Exemplos:

* Problemas de performance
* Falta de validação
* Acoplamento excessivo

---

## Médio

Recomendado corrigir.

Exemplos:

* Código duplicado
* Estrutura inadequada
* Melhorias arquiteturais

---

## Baixo

Melhorias opcionais.

Exemplos:

* Legibilidade
* Organização
* Convenções

---

# Checklist Obrigatório

## Segurança

* [ ] Autenticação validada
* [ ] Autorização validada
* [ ] Inputs validados
* [ ] Dados sanitizados
* [ ] Sem exposição de segredos

## Arquitetura

* [ ] Respeita padrões do projeto
* [ ] Separação de responsabilidades correta
* [ ] Sem acoplamento indevido

## Performance

* [ ] Sem gargalos evidentes
* [ ] Consultas eficientes
* [ ] Operações assíncronas quando aplicável

## Manutenibilidade

* [ ] Código legível
* [ ] Código reutilizável
* [ ] Fácil de testar

## Projeto

* [ ] Compatível com FastAPI
* [ ] Compatível com PostgreSQL
* [ ] Compatível com SQLAlchemy
* [ ] Compatível com React/Vite
* [ ] Compatível com Adapter Pattern

---

# Critério de Aprovação

Uma alteração só pode ser considerada aprovada quando:

* Não introduz vulnerabilidades.
* Respeita a arquitetura oficial.
* Mantém desempenho adequado.
* Permite manutenção futura.
* Está alinhada ao contexto do Financeiro AI Studio.

Na presença de problemas críticos, a recomendação deve ser obrigatoriamente:

REJEITADO.
