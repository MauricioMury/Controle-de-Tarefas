# Roadmap — Controle de Tarefas

Data de revisão: 2026-11-20

Este arquivo contém as regras, a visão geral, as decisões vigentes, a etapa ativa e as pendentes. Evidências de etapas concluídas ficam em `ai-context/local/roadmap-historico.md`, lido somente quando necessário.

## Objetivo

Evoluir o Controle de Tarefas (em produção em `todastarefas.com.br`) corrigindo a usabilidade de Minhas Tarefas e da navegação entre telas, religando as notificações por e-mail e WhatsApp e separando a data de criação das datas de meta e de conclusão.

## Princípios de execução

- As etapas devem ser executadas na ordem apresentada.
- Uma etapa só pode ser encerrada quando todos os critérios de saída forem atendidos.
- Mudanças pequenas, testáveis e registradas.
- Nenhuma funcionalidade fora do escopo sem nova etapa aprovada.
- Nenhum arquivo do projeto é alterado sem autorização de Mauricio (`ai-context/shared/instrucoes.md`).

## Regras de acompanhamento

Status permitidos: `PENDENTE`, `ANDAMENTO`, `CONCLUÍDO`.

1. Toda tarefa começa como `PENDENTE`.
2. Antes do início do trabalho, a tarefa muda para `ANDAMENTO`, com data e hora de início.
3. Uma tarefa só muda para `CONCLUÍDO` quando a implementação estiver completa e os testes necessários tiverem passado.
4. Uma etapa só é concluída quando todas as suas tarefas estiverem `CONCLUÍDO`.
5. A data de início da etapa é a da primeira tarefa em `ANDAMENTO`; a de término, a da aprovação da última tarefa.
6. Datas no fuso `America/Sao_Paulo`, formato `AAAA-MM-DD HH:MM`. Consultar o relógio do sistema antes de preencher qualquer horário.
7. Falha em teste impede a conclusão até ser corrigida e reexecutada com sucesso.
8. Cada tarefa registra início, término, duração, testes, resultado e evidências.
9. Etapa concluída vai para `roadmap-historico.md` (texto completo); aqui fica só o resumo apontando para o histórico.
10. Ao terminar cada tarefa, avisar Mauricio antes de iniciar a próxima.
11. Versionamento semântico em `versoestarefas.md` (raiz). Toda tarefa que muda o comportamento do app registra um item em **Não lançado**. Ao fechar a etapa, a coluna "Versão" da tabela recebe a versão prevista. Ela é confirmada no PR para a `main`, junto com `APP_VERSION` em `app.py`.

## Visão das etapas

| Ordem | Etapa | Objetivo | Status | Versão |
| --- | --- | --- | --- | --- |
| 0 | Decisões iniciais | Evoluir este projeto; papel das datas; regras das notificações | CONCLUÍDO | — |
| 1 | Minhas Tarefas: itens por página | Paginação correta e Início sem os filtros de Minhas Tarefas | CONCLUÍDO | 5.0.1 |
| 2 | Navegação entre telas | Voltar à tela de origem após salvar e manter os filtros do Calendário | CONCLUÍDO | 5.0.2 |
| 3 | Data de criação | Exibir "Criada em" e seletor "Ver por: Meta / Criação" no Calendário | PENDENTE | 5.1.0 (prevista) |
| 4 | Notificações | Religar o cadastro de lembretes na tarefa e o disparo por e-mail e WhatsApp | PENDENTE | 5.2.0 (prevista) |
| 5 | Qualidade e dados | Corrigir status com acentuação corrompida e o `DeprecationWarning` de `datetime.utcnow()` | PENDENTE | 5.2.1 (prevista) |

## Decisões vigentes

- **Evoluir este projeto**, sem projeto novo nem troca de stack: Flask + Jinja2 + SQLite (Mauricio, 2026-11-12).
- **Usuário único**: só Mauricio usa o sistema. Os outros 3 usuários do banco não exigem cuidado de multiusuário além do isolamento já existente.
- Calendário com seletor **"Ver por: Meta | Criação"**; o cartão mostra as três datas nos dois modos (Mauricio, 2026-11-12).
- Notificações por tarefa: canal escolhido em cada tarefa (e-mail, WhatsApp ou ambos) e até dois lembretes (uso típico: um dia antes e no dia) (Mauricio, 2026-11-12).
- Produção: PythonAnywhere, branch `main`, `APP_ENV=Producao`, `SESSION_COOKIE_SECURE=True`, banco `instance/tarefas.db`. Trabalho na branch `Desenvolvimento` → PR para `main`.
- Local: `APP_ENV=Desenvolvimento`, banco `instance/tarefas-desenvolvimento.db` (em 2026-11-12, cópia do banco de produção: 4 usuários, 475 tarefas).
- Sem Alembic: colunas novas exigem `_ensure_column` em `local_migrations.py`. Backup do banco antes de aplicar em produção.
- Toda rota nova filtra por `tenant_id` e `user_id`, com caso correspondente em `tests_e2e_security.py`.
- `git push` é sempre do Mauricio.
- Versionamento semântico a partir de 2026-11-12: produção atual = **5.0.0**; registro em `versoestarefas.md`, versão no código em `APP_VERSION` (`app.py`) exibida no rodapé, tag `vX.Y.Z` na `main` (Mauricio, 2026-11-12).
- Pastas `.agents/` e `.codex/` removidas por Mauricio em 2026-11-12; não restaurar.

---

## Etapa 0 — Decisões iniciais

CONCLUÍDO em 2026-11-12 07:18. Evidências em `roadmap-historico.md`.

---

## Etapa 1 — Minhas Tarefas: itens por página

CONCLUÍDO em 2026-11-20 06:12 (versão 5.0.1). Evidências em `roadmap-historico.md`.

---

## Etapa 2 — Navegação entre telas

CONCLUÍDO em 2026-11-20 08:04 (versão 5.0.2). Evidências em `roadmap-historico.md`.

---

## Etapa 3 — Data de criação

- Status: PENDENTE

### Contexto (2026-11-12)

- A coluna `tarefa.created_at` já existe e está preenchida nas 475 tarefas (desde 2026-02-01, gravada em UTC). Não há data nova a criar nem migração de dados.

### Tarefa 3.1 — Exibir "Criada em"

- Status: PENDENTE
- Escopo: mostrar a data de criação (convertida de UTC para `America/Sao_Paulo`) no Calendário, em Minhas Tarefas e na edição. Somente leitura. A duplicação gera uma nova data de criação.
- Testes: data exibida no fuso correto (tarefa criada às 23:30 em São Paulo aparece no dia certo, e não no dia seguinte em UTC).

### Tarefa 3.2 — Seletor "Ver por: Meta | Criação" no Calendário

- Status: PENDENTE
- Escopo: no modo **Meta** (padrão, comportamento atual), a tarefa fica no dia da meta. No modo **Criação**, fica no dia em que foi criada. Nos dois modos o cartão mostra "Criada em", o status de agenda (Atrasada / Hoje / Faltam X dias, calculado pela Meta) e, se concluída, a data de conclusão no lugar do status de agenda. Etapas continuam pela data planejada.
- Arrastar e soltar: no modo Meta continua mudando a Meta; no modo Criação fica desativado, porque a data de criação não deve ser alterada.
- O modo escolhido é preservado junto com os filtros (Tarefa 2.2).
- Testes: teste visual de Mauricio nos dois modos.

---

## Etapa 4 — Notificações

- Status: PENDENTE

### Diagnóstico (2026-11-12)

- As notificações funcionaram até maio/2026: as 6 tarefas com lembrete no banco (a última em 2026-05-21) estão marcadas como enviadas por e-mail e WhatsApp.
- Hoje o cadastro e a edição de tarefa **não têm mais os campos de lembrete**, mas `dados_tarefa_form()` continua lendo `notif_datetime_1/2`. **Efeito colateral: editar uma tarefa que tem lembrete apaga os lembretes dela.**
- O banco não tem coluna de canal por tarefa, em nenhum dos bancos antigos (`instance/` e `instance/Backups/`). Hoje o canal é decidido só pelo perfil (e-mail e/ou WhatsApp configurados).
- `notificacoes.py` (e-mail via SMTP Gmail, WhatsApp via CallMeBot) existe, mas não é importado por nenhum módulo; o app fixa `notifications_enabled: False`.
- Só o usuário Mauricio tem e-mail e WhatsApp configurados no perfil. A senha de app do Gmail e a apikey do CallMeBot continuam válidas, segundo Mauricio, mas precisam ser testadas.

### Tarefa 4.1 — Canal por tarefa (modelo e migração)

- Status: PENDENTE
- Escopo: coluna `tarefa.notif_canal` (`email`, `whatsapp`, `ambos`), NOT NULL com padrão `ambos`, via `_ensure_column` em `local_migrations.py` e no modelo. Tarefas existentes ficam com `ambos`, o que equivale ao comportamento antigo.
- Testes: migração idempotente (rodar duas vezes), banco antigo sem a coluna recebe o padrão.

### Tarefa 4.2 — Lembretes no cadastro, edição e duplicação

- Status: PENDENTE
- Escopo: seção "Notificações" em `cadastro_tarefa.html` e `editar_tarefa.html` com o canal (E-mail / WhatsApp / Ambos) e os lembretes 1 e 2 (data e hora). Atalhos opcionais "1 dia antes" e "No dia" calculados a partir da Meta e da hora de início. Avisar na tela quando o canal escolhido não estiver configurado no perfil. Mudar a data de um lembrete reinicia o "enviado" daquele lembrete (já existe em `aplicar_dados_tarefa`). Duplicar copia o canal, mas não as datas de lembrete.
- Corrige o efeito colateral de a edição apagar os lembretes.
- Testes: cadastro e edição gravam canal e lembretes; editar sem mexer nos lembretes os preserva; lembrete com data alterada volta a "não enviado".

### Tarefa 4.3 — Script de disparo

- Status: PENDENTE
- Escopo: comando (ex.: `python enviar_notificacoes.py`) que busca tarefas pendentes com lembrete vencido e não enviado, envia pelos canais da tarefa usando `notificacoes.py` e marca `notif_*_enviada_*` por canal. Em caso de falha, reenvia só no canal que falhou. Tarefa concluída não notifica. Logs sem e-mail, número ou apikey.
- Testes: unitários com envio simulado (sem SMTP/HTTP real): marca enviado, não reenvia, respeita o canal da tarefa, falha num canal não marca o outro, tarefa concluída é ignorada.

### Tarefa 4.4 — Teste real de envio e agendamento no PythonAnywhere

- Status: PENDENTE
- Escopo: primeiro, testar localmente o envio real para Mauricio (e-mail e WhatsApp) com as credenciais atuais. Depois, configurar `NOTIF_EMAIL_REMETENTE` e `NOTIF_EMAIL_SENHA_APP` no `.env` do servidor, agendar o script no PythonAnywhere e ligar `notifications_enabled`.
- A verificar: o plano do PythonAnywhere. Tarefa agendada roda no máximo de hora em hora, então o lembrete pode atrasar até 59 min. Se a precisão de minutos importar, usar uma *always-on task* (planos pagos).
- A apikey do WhatsApp fica em texto aberto em `user.whatsapp_apikey`. Com usuário único, aceitável; registrar a decisão.
- Testes: envio real aprovado por Mauricio, local e em produção.

---

## Etapa 5 — Qualidade e dados

- Status: PENDENTE

### Tarefa 5.1 — Status com acentuação corrompida

- Status: PENDENTE
- Contexto: no banco de produção há 1 tarefa com o status `Concluída` gravado com codificação corrompida (427 corretas, 47 Pendente). Ela não aparece no filtro "Concluída".
- Escopo: migração idempotente em `local_migrations.py` normalizando o status; aplicar em produção com backup antes.

### Tarefa 5.2 — `datetime.utcnow()` obsoleto

- Status: PENDENTE
- Escopo: trocar por datas com fuso (`datetime.now(timezone.utc)`), mantendo o formato gravado no SQLite.
- Testes: suíte sem `DeprecationWarning`.

---

## Pendências externas

- Plano do PythonAnywhere (frequência de tarefas agendadas / *always-on task*): Mauricio confirma antes da Tarefa 4.4.
