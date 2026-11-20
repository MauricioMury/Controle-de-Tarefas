# Roadmap — Histórico de etapas concluídas

Evidências das etapas concluídas do Controle de Tarefas, movidas de `roadmap.md` ao encerrar cada etapa.

Versões anteriores a este roadmap (V4 e V5) estão documentadas em `ai-context/mapa_projetoV4.md` e `ai-context/mapa_projetoV5.md`.

---

## Etapa 0 — Decisões iniciais

- Status: CONCLUÍDO
- Início: 2026-11-12 07:10
- Término: 2026-11-12 07:18 (aprovado por Mauricio)

### Tarefa 0.1 — Evoluir este projeto ou criar um novo

- Status: CONCLUÍDO
- Início: 2026-11-12 07:10 · Término: 2026-11-12 07:18 · Duração: 8 min
- Resultado: decidido **evoluir este projeto**. Só Mauricio usa o sistema e a stack Flask + Jinja2 + SQLite é mantida. Os quatro pedidos cabem na base atual; um projeto novo só se justificaria com troca de stack, app mobile/API ou muitos usuários.
- Testes: não se aplica (decisão).

### Tarefa 0.2 — Papel de cada data no Calendário

- Status: CONCLUÍDO
- Início: 2026-11-12 07:10 · Término: 2026-11-12 07:18 · Duração: 8 min
- Pedido original: tarefa posicionada no Calendário pela data de criação, com status de agenda pela Meta e data de conclusão.
- Ponto levantado pelo Claude: posicionar só pela criação tira do Calendário a visão do que vence em cada dia, e o arrastar e soltar altera a Meta.
- Resultado: aprovado o seletor **"Ver por: Meta | Criação"**, com as três datas no cartão nos dois modos. A coluna `tarefa.created_at` já existe e está preenchida nas 475 tarefas (UTC), sem necessidade de migração.
- Testes: não se aplica (decisão).

### Tarefa 0.3 — Regras das notificações

- Status: CONCLUÍDO
- Início: 2026-11-12 07:10 · Término: 2026-11-12 07:18 · Duração: 8 min
- Resultado: no cadastro da tarefa, o usuário escolhe o canal (e-mail, WhatsApp ou ambos) e até duas datas de lembrete (uso típico: um dia antes e no dia). Disparo por tarefa agendada no servidor. Credenciais do Gmail e do CallMeBot válidas segundo Mauricio, a testar na Tarefa 4.4.
- Descobertas: as notificações funcionaram até maio/2026 (6 tarefas com lembrete, todas marcadas como enviadas); não existe coluna de canal por tarefa em nenhum banco antigo; os campos de lembrete saíram das telas, e a edição de tarefa hoje apaga os lembretes existentes.
- Pendência movida para "Pendências externas": plano do PythonAnywhere.
- Testes: não se aplica (decisão).

---

## Etapa 1 — Minhas Tarefas: itens por página

- Status: CONCLUÍDO
- Início: 2026-11-12 07:24
- Término: 2026-11-20 06:12 (aprovado por Mauricio)
- Versão: 5.0.1

### Diagnóstico (2026-11-12)

- `get_filtros_ativos()` guarda `page` na sessão. O formulário "Itens por página" (`templates/lista_tarefas.html`) e o formulário de filtros não reiniciam a página. Exemplo: na página 3 com 10 itens, ao trocar para 100, a lista continua na página 3 de 1 e aparece vazia.
- `page` e `per_page` não são validados: `page` fora do intervalo devolve lista vazia, e `per_page=0` gera divisão por zero.
- A paginação é feita em memória (`query.all()` + `sorted`). Para 475 tarefas não é um problema, mas dá para passar para `order_by` + `limit/offset`.

### Tarefa 1.1 — Corrigir a paginação

- Status: CONCLUÍDO
- Início: 2026-11-12 07:24 · Término: 2026-11-20 06:12 (teste visual aprovado por Mauricio)
- Escopo: ao trocar itens por página ou aplicar um filtro, voltar para a página 1; limitar `per_page` aos valores da tela (5, 10, 20, 50, 100); ajustar `page` ao intervalo válido; ordenar e paginar na consulta.
- Resultado: `routes/routes.py`: constantes `OPCOES_POR_PAGINA`, `POR_PAGINA_PADRAO` e `PARAMETROS_FILTRO_LISTA`. `get_filtros_ativos()` recusa `per_page` fora das opções (volta a 10) e `page` < 1. `lista_tarefas` volta para a página 1 quando a URL traz filtro ou `per_page` sem `page`, limita a página à última existente e a grava na sessão. A paginação passou para `order_by(data_meta, hora_inicio, id)` + `offset/limit` com `count()` no banco, no lugar de `query.all()` + `sorted` em memória. Template sem alteração.
- Testes: `ListaTarefasPaginacaoTestCase` em `tests_e2e_crud.py` (6 testes, 25 tarefas): trocar itens por página estando na página 3; filtro volta à página 1; página 99 mostra a última; `per_page` 0, -5, 7, abc e 100000 usam o padrão; página mantida ao voltar sem parâmetros; lista vazia. Contra o código antigo: 7 falhas e 1 erro (`per_page=0` → divisão por zero). Com a correção: suíte completa `python -m unittest tests_e2e_crud tests_e2e_security tests_e2e_visual` → 17 testes OK.
- Teste visual aprovado por Mauricio em 2026-11-20: em Minhas Tarefas, ir até uma página alta, trocar itens por página (5 → 100 e 100 → 5), aplicar e limpar filtros, editar uma tarefa e conferir que volta para a mesma página.

### Tarefa 1.2 — Indicadores do Início sem os filtros de Minhas Tarefas

- Status: CONCLUÍDO
- Início: 2026-11-20 06:06 · Término: 2026-11-20 06:12 · Duração: 6 min (teste visual aprovado por Mauricio)
- Motivo (relatado por Mauricio em 2026-11-20): o Início mostra os números com os filtros de Minhas Tarefas aplicados.
- Diagnóstico: `templates/index.html` calcula os indicadores abrindo `/lista_tarefas` em segundo plano (6 `fetch`) e lendo "Total: N tarefas" no HTML. Cada chamada herda os filtros da sessão (números errados) e grava os seus próprios filtros, de modo que a última chamada a terminar define os filtros que Mauricio encontra em Minhas Tarefas. O card "Hoje" usa a data em UTC (`toISOString`), que erra depois das 21:00 em São Paulo.
- Escopo: indicadores calculados em `index()` numa consulta só, filtrada por `tenant_id`/`user_id`, sem ler nem gravar a sessão; "Hoje" pela data de São Paulo; remover os `fetch` do template.
- Resultado: `routes/routes.py`: `FUSO_SAO_PAULO` (UTC−3 fixo, sem depender do pacote `tzdata` no Windows), `hoje_sao_paulo()` e `indicadores_dashboard()` (uma consulta com `count` + `sum(case)`); `index()` passa `indicadores` ao template. `templates/index.html`: cards preenchidos pelo servidor; removido o bloco `extra_js` com os 6 `fetch`. Mantidas as regras antigas de cada card (Alta Prioridade = "Muito Importante" em qualquer status; Hoje = meta de hoje em qualquer status).
- Testes: `DashboardIndicadoresTestCase` em `tests_e2e_crud.py` (4 testes): números com 6 tarefas próprias e 3 de outro usuário ignoradas; filtros de Minhas Tarefas na sessão não alteram os números; abrir o Início não altera os filtros gravados na sessão; "Hoje" às 22:30 de São Paulo (01:30 UTC do dia seguinte) é o dia de São Paulo. Contra o template antigo: 3 falhas. Suíte completa → 21 testes OK (2026-11-20 06:08).
- Conferência com o banco de desenvolvimento (cópia de produção), usuário Mauricio: Total 476, Pendentes 48, Concluídas 427, Alta Prioridade 329, Hoje 2.
- Teste visual aprovado por Mauricio em 2026-11-20: filtrar Minhas Tarefas (ex.: categoria + status), abrir o Início e conferir os números acima; voltar a Minhas Tarefas e conferir que os filtros continuam os mesmos.

---
