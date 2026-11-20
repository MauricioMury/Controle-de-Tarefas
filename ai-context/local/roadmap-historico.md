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

## Etapa 2 — Navegação entre telas

- Status: CONCLUÍDO
- Início: 2026-11-20 06:25
- Término: 2026-11-20 08:04 (aprovado por Mauricio)
- Versão: 5.0.2

### Diagnóstico (2026-11-12)

- Cadastrar, editar, duplicar, concluir e excluir tarefa sempre redirecionavam para `lista_tarefas` (`redirect_com_filtros('lista_tarefas')` em `routes/routes.py`), qualquer que fosse a tela de origem.
- Os filtros do Calendário (texto, categoria, status, tipo) existiam só em variáveis JavaScript de `templates/calendario.html` e se perdiam ao sair e voltar.
- O mesmo valia para as telas de etapa abertas pelo Calendário.
- Achado em 2026-11-12 (Etapa 1): Duplicar redirecionava para `cadastro_tarefa?prioridade=...`, e o `get_filtros_ativos()` chamado no cadastro gravava esse `prioridade` na sessão como filtro. Depois de duplicar, Minhas Tarefas ficava filtrada pela prioridade da tarefa duplicada.

### Tarefa 2.1 — Retorno à tela de origem

- Status: CONCLUÍDO
- Início: 2026-11-20 06:25 · Término: 2026-11-20 08:04 · Duração: 1 h 39 min (teste visual aprovado por Mauricio)
- Escopo: parâmetro `next` levado pelos links de Duplicar, Editar, Nova tarefa e Concluir (Calendário, Minhas Tarefas, Início, etapas) e repassado no formulário. Após salvar ou cancelar, redirecionar para ele, validado como URL interna para evitar *open redirect*. Sem `next`, mantém o comportamento anterior.
- Resultado: `routes/routes.py`: `url_retorno_segura()` (só caminho interno: começa com `/`, sem `//`, sem `\`, sem caracteres de controle, até 2000 caracteres), `destino_retorno()` (lê `next` do formulário ou da URL), `redirect_retorno()` (volta ao `next` ou, sem ele, a Minhas Tarefas com os filtros, como antes) e `filtros_da_sessao()` (lê os filtros sem gravar). Cadastrar, editar, duplicar (repassa o `next` ao cadastro), concluir e excluir tarefa usam `redirect_retorno`; salvar/excluir/mudar status de etapa usa o `next` em `resposta_etapa_salva`; a lista de etapas aberta com `next` mostra "Voltar" para a origem. Templates: campo oculto `next` e "Voltar" para a origem em `cadastro_tarefa.html`, `editar_tarefa.html` e `editar_etapa.html`; `lista_etapas.html` com "Voltar"; "Nova Tarefa" do Início volta ao Início.
- Corrigido junto: (a) cadastro e edição não passam mais os campos de pré-preenchimento da duplicação por `get_filtros_ativos()`, então duplicar não filtra mais Minhas Tarefas pela prioridade; (b) erro de validação na edição de tarefa (ex.: hora fim antes da hora início) renderizava a tela sem `filtros`/`progresso` e caía em erro; agora mostra a tela com a mensagem, como no cadastro (commit `dea4b1e`).
- Testes: `NavegacaoRetornoTestCase` em `tests_e2e_crud.py` (9 testes): validação de `next` (externo, `//`, `\`, `javascript:`, quebra de linha, vazio, longo); editar, duplicar + cadastrar, concluir, excluir e editar etapa voltam ao Calendário com os filtros; `next` externo é ignorado; sem `next` volta a Minhas Tarefas; duplicar não grava filtro de prioridade; lista de etapas com "Voltar"; erro de validação na edição renderiza. Contra o código antigo: 5 falhas e 2 erros. Suíte completa → 30 testes OK (2026-11-20 06:29).

### Tarefa 2.2 — Filtros do Calendário persistentes

- Status: CONCLUÍDO
- Início: 2026-11-20 06:25 · Término: 2026-11-20 08:04 · Duração: 1 h 39 min (teste visual aprovado por Mauricio)
- Escopo: guardar os filtros do Calendário e o mês em exibição para que voltar ao Calendário restaure a visão anterior, inclusive "Pendentes".
- Decisão de implementação: **URL** (`history.replaceState`), porque funciona com o `next`, com o botão Voltar do navegador e com favoritos. O modo "Ver por" (Etapa 3) usará o mesmo mecanismo.
- Resultado: `templates/calendario.html`: a URL do Calendário reflete `q` (busca), `cat`, `status`, `tipo`, `mes` (AAAA-MM) e `dia` (AAAA-MM-DD) a cada renderização; ao abrir, esses valores são lidos e validados (categoria e status só se existirem nas opções). Links de Editar, Duplicar, Editar etapa, Abrir etapas e dos cartões de prazo levam `next` com a URL atual; os formulários de Concluir e Deletar levam o campo oculto `next`.
- Testes: `node --check` no JavaScript do template (ok).
- Teste visual aprovado por Mauricio em 2026-11-20: Calendário → filtrar Pendentes, mudar de mês e escolher um dia → Duplicar → alterar a data → salvar → volta ao Calendário no mesmo mês e dia, com Pendentes. Repetido com Editar, Concluir, Deletar e Editar etapa; F5 com o Calendário filtrado mantém o filtro.

---

## Etapa 3 — Datas da tarefa

- Status: CONCLUÍDO
- Início: 2026-11-20 08:10
- Término: 2026-11-20 10:41 (aprovado por Mauricio)
- Versão: 5.1.0

### Contexto (2026-11-12, atualizado em 2026-11-20)

- A coluna `tarefa.created_at` já existe e está preenchida em todas as tarefas (desde 2026-02-01, gravada em UTC).
- Em 2026-11-20, Mauricio pediu uma data de início escolhida por ele e definiu a regra das datas (ver "Decisões vigentes").
- Banco de desenvolvimento: 429 concluídas, todas com data realizada; 388 com hora fim (376 delas concluídas); nenhuma com data de início.
- Achado: `marcar_concluida` grava `date.today()` do servidor (UTC); depois das 21:00 em São Paulo grava o dia seguinte. Corrigir na Tarefa 3.2.

### Tarefa 3.1 — Exibir "Criada em"

- Status: CONCLUÍDO
- Início: 2026-11-20 08:10 · Término: 2026-11-20 08:20 · Duração: 10 min (teste visual aprovado por Mauricio)
- Escopo: mostrar a data de criação (convertida de UTC para `America/Sao_Paulo`) no Calendário, em Minhas Tarefas e na edição. Somente leitura. A duplicação gera uma nova data de criação.
- Testes: data exibida no fuso correto (tarefa criada às 23:30 em São Paulo aparece no dia certo, e não no dia seguinte em UTC).
- Resultado: `routes/routes.py`: `para_sao_paulo()` (datetime sem fuso tratado como UTC → UTC−3) e `formatar_data_hora_sp()`, registrado como filtro Jinja `data_sp` em `register_routes` (vazio vira "—"); o JSON do Calendário ganhou `criada_em`. Templates: Minhas Tarefas mostra "Criada dd/mm/aaaa" abaixo da data meta; a edição mostra "Criada em dd/mm/aaaa hh:mm" no topo; o cartão de tarefa do Calendário mostra "Criada em ..." (etapas não). A duplicação já gerava nova data de criação (`default` do modelo).
- Testes: `CriadaEmTestCase` em `tests_e2e_crud.py` (6 testes): conversão 02:30 UTC → 19/11 23:30 (com e sem fuso), lista, edição e JSON do Calendário no dia de São Paulo, tarefa sem `created_at` não quebra, duplicação gera nova data. Contra o código antigo: 4 falhas e 1 erro. Suíte `tests_e2e_crud tests_e2e_security` → 34 testes OK (2026-11-20 08:12). `node --check` no JavaScript do Calendário: ok.
- Teste visual aprovado por Mauricio em 2026-11-20: "Criada" em Minhas Tarefas, "Criada em" na edição e nos cartões do Calendário.
- Decisão (Mauricio, 2026-11-20): a data de criação continua automática e não editável. Mauricio quer uma data nova, escolhida por ele: "data de início" (Tarefa 3.3, a definir).

### Tarefa 3.2 — Data de início e horas opcionais

- Status: CONCLUÍDO
- Início: 2026-11-20 08:42 · Término: 2026-11-20 09:03 · Duração: 21 min (teste visual aprovado por Mauricio)
- Escopo:
  - Modelo: `tarefa.data_inicio` (DATE, opcional) e `hora_inicio` passa a aceitar vazio.
  - Migração em `local_migrations.py`: `_ensure_column` para `data_inicio` e reconstrução da tabela `tarefa` para tirar o NOT NULL de `hora_inicio` (SQLite não altera restrição). Parte do DDL real de cada banco (os bancos antigos têm DDL diferentes), copia os dados, recria os índices e confere `foreign_key_check`. Idempotente. Backup antes de rodar em produção.
  - Cadastro e edição: "Data de início" + "Hora Início"; "Data Meta"; "Data Realizado" + "Hora Fim". Validação: realizado não antes do início; hora fim > hora início só no mesmo dia.
  - Exibição: Minhas Tarefas, edição e Calendário mostram a hora início só com data de início e a hora fim só com data realizada; aviso "sem data de início" nas tarefas pendentes sem ela.
  - Concluir: realizado = hoje em São Paulo; hora fim = agora, se vazia.
  - Duplicar: copia data e hora de início; não copia realizado nem hora fim.
  - Ordenação no mesmo dia: hora início, sem hora por último.
- Fora do escopo: Entrada rápida (`templates/entrada_rapida.html`). Ela não tem data de início e continua enviando a hora reconhecida no texto, que fica gravada e oculta. Mauricio não usa a tela hoje e vai rever a Entrada rápida inteira depois (decisão de 2026-11-20).
- Backup do banco de desenvolvimento antes da migração: `instance/Backups/tarefas-desenvolvimento-backup-pre-v5-1-data-inicio-20261120-0845.db`.
- Resultado:
  - `models.py`: `data_inicio` (opcional) e `hora_inicio` opcional.
  - `local_migrations.py`: `_ensure_column` de `data_inicio` e `_tornar_hora_inicio_opcional()` (reconstrução a partir do DDL do próprio banco; confere total de tarefas e `foreign_key_check`; desfaz tudo em caso de erro). Testada antes numa cópia do banco de desenvolvimento (477 tarefas idênticas, índices e FKs preservados, `integrity_check` ok); depois aplicada no banco de desenvolvimento pelo reload do servidor.
  - `routes/routes.py`: `dados_tarefa_form` com as regras novas (início não posterior à meta; realizado não anterior ao início; hora fim > hora início só no mesmo dia); `mover_tarefa` recusa meta anterior à data de início; `montar_tarefa`/`aplicar_dados_tarefa` com `data_inicio`; Concluir em São Paulo (data e hora fim, se vazia); Duplicar repassa data e hora de início; Minhas Tarefas ordena sem hora por último; JSON do Calendário com `data_inicio`/`data_realizado` e horas só com a data correspondente.
  - Templates: cadastro e edição com os pares Início/Hora Início, Meta, Realizado/Hora Fim; aviso "Tarefa sem data de início" na edição. Minhas Tarefas: colunas "Meta" e "Início / Fim", com o selo "Sem data de início" nas pendentes. Calendário: "Início dd/mm hh:mm", "Fim dd/mm hh:mm" e o selo "Sem data de início" no cartão da tarefa (etapas sem mudança).
- Testes: `DataInicioTestCase` (15 testes) e `MigracaoDataInicioTestCase` (3 testes) em `tests_e2e_crud.py`: cadastro com e sem início; início depois da meta recusado e no dia da meta aceito; arrastar a meta para antes do início recusado; realizado antes do início recusado; hora fim menor aceita em outro dia e recusada no mesmo dia; tarefa antiga sem início oculta a hora, mostra o aviso e mantém a hora na edição; editar sem mexer preserva a hora; Concluir às 22:30 de São Paulo grava o dia 19 e 22:30; Concluir preserva hora fim existente; Duplicar copia o início e não o realizado; ordem sem hora por último; migração de banco com DDL antigo (dados, índices, FK de etapa, integridade), idempotente, aceita tarefa sem hora. Contra o código antigo: 8 falhas e 7 erros. Ajustado `test_erro_de_validacao_na_edicao_renderiza_a_tela` para a regra do mesmo dia. Suíte `tests_e2e_crud tests_e2e_security` → 52 testes OK (2026-11-20 09:02). `node --check` no JavaScript do Calendário: ok.
- Teste visual aprovado por Mauricio em 2026-11-20 (incluindo início posterior à meta recusado): (1) Minhas Tarefas: pendentes antigas com "Sem data de início" e concluídas com "Fim"; (2) editar uma pendente antiga: aviso, hora antiga preenchida; informar data de início e salvar → aparece "Início" na lista e no Calendário; (3) cadastrar sem data de início e sem hora; (4) Concluir pelo botão → "Fim" com a data e hora atuais; (5) Duplicar uma concluída → a cópia vem com o início e sem realizado.

### Tarefa 3.3 — Atraso na conclusão

- Status: CONCLUÍDO
- Início: 2026-11-20 09:03 · Término: 2026-11-20 09:13 · Duração: 10 min (teste visual aprovado por Mauricio)
- Escopo: além de "Atrasada há X dias" (pendente), mostrar "Concluída com X dias de atraso" quando realizado > meta, no Calendário e em Minhas Tarefas.
- Resultado: `models.py`: `Tarefa.dias_atraso(hoje)` (concluída: realizado − meta; pendente: hoje − meta; 0 no prazo). `lista_tarefas` passa `hoje=hoje_sao_paulo()`. Minhas Tarefas, coluna Status: "com X dias de atraso" nas concluídas e "atrasada há X dias" nas pendentes (este último não existia na lista, só no painel de prazos do Calendário). Calendário: selo vermelho "Concluída com X dias de atraso" no cartão da tarefa.
- Testes: `AtrasoTestCase` em `tests_e2e_crud.py` (6 testes): cálculo do modelo (no prazo, pendente, concluída conta até o realizado); lista com 5 dias, singular "1 dia", sem atraso no prazo; pendente atrasada pela data de São Paulo; Calendário recebe meta e realizado. Contra o código antigo: 4 falhas e 1 erro. Suíte `tests_e2e_crud tests_e2e_security` → 58 testes OK (2026-11-20 09:04). `node --check` no JavaScript do Calendário: ok.
- Teste visual aprovado por Mauricio em 2026-11-20: Minhas Tarefas, filtro Concluída → tarefas entregues depois da meta com "com X dias de atraso"; filtro Pendente → atrasadas com "atrasada há X dias"; Calendário → no dia da meta de uma tarefa entregue com atraso, selo vermelho.

### Tarefa 3.4 — Seletor "Ver por: Meta | Início | Criação" no Calendário

- Status: CONCLUÍDO
- Início: 2026-11-20 09:13 · Término: 2026-11-20 10:41 · Duração: 1 h 28 min (inclui a espera pelo teste visual; aprovado por Mauricio)
- Escopo: no modo **Meta** (padrão, comportamento atual), a tarefa fica no dia da meta. No modo **Início**, no dia de início; sem data de início, fica no dia da meta com o aviso "sem data de início". No modo **Criação**, no dia em que foi criada. O cartão mostra as datas nos três modos. Etapas continuam pela data planejada.
- Arrastar e soltar: no modo Meta muda a Meta; no modo Início muda a data de início; no modo Criação fica desativado.
- O modo escolhido fica na URL junto com os filtros (Tarefa 2.2).
- Resultado:
  - `templates/calendario.html`: seletor `filtroVerPor` na barra de filtros (não é filtro: "Limpar" não o reinicia); estado `verPor` salvo na URL como `ver=inicio|criacao` (Meta é o padrão e não aparece na URL); `diaDoItem()` escolhe o dia de cada item (etapas sempre na data planejada; sem início → meta; sem criação → meta) e é usada no grid, na lista do dia e nos indicadores do mês e no gráfico por dia da semana. O painel de prazos continua pela Meta. Arrastar: Meta muda `data_meta`, Início muda `data_inicio`, Criação desativado.
  - `routes/routes.py`: JSON do Calendário com `data_criacao` (dia de São Paulo); `mover_tarefa` aceita `data_inicio` e recusa início depois da meta ("Adie a meta antes") ou depois da data realizado.
- Testes: `VerPorCalendarioTestCase` em `tests_e2e_crud.py` (7 testes): seletor e leitura da URL; `data_criacao` no dia de São Paulo; arrastar no modo Início muda só o início; início no dia da meta aceito; depois da meta e depois do realizado recusados; data inválida recusada. `tests_e2e_security.py`: `test_usuario_nao_move_tarefa_de_outro_usuario` (meta e início, 404). Contra o código antigo: 6 falhas. `diaDoItem()` exercitada no node nos três modos (tarefa com início, sem início e etapa). Suíte `tests_e2e_crud tests_e2e_security` → 66 testes OK (2026-11-20 09:15). `node --check`: ok.
- Teste visual aprovado por Mauricio em 2026-11-20: (1) Ver por Meta = comportamento atual; (2) Ver por Início: tarefas com início no dia de início, sem início no dia da meta com o selo; arrastar muda o início, e arrastar para depois da meta é recusado com aviso; (3) Ver por Criação: tarefas no dia em que foram criadas, sem arrastar; (4) escolher Início ou Criação, editar uma tarefa e salvar → volta no mesmo modo; F5 mantém o modo.

---
