# Versões — Controle de Tarefas

Registro das versões publicadas em produção (`todastarefas.com.br`), no formato [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e com [Versionamento Semântico](https://semver.org/lang/pt-BR/).

Os detalhes de implementação e os testes de cada item ficam em `ai-context/local/roadmap-historico.md`, na etapa indicada.

## Regras

- Formato `MAIOR.MENOR.CORREÇÃO`:
  - **MAIOR**: quebra de compatibilidade. Exemplos: troca de stack, ou migração de banco que exija ação manual além de rodar o app.
  - **MENOR**: funcionalidade nova compatível, inclusive coluna nova adicionada por `local_migrations.py`.
  - **CORREÇÃO**: correção de defeito sem funcionalidade nova.
- Durante o desenvolvimento, os itens entram em **Não lançado**. No PR `Desenvolvimento` → `main`, essa seção recebe o número e a data, e `APP_VERSION` em `app.py` é atualizado para o mesmo número.
- Depois do merge, a `main` recebe a tag `vX.Y.Z`. O `git push --tags` é do Mauricio.
- Seções por versão: **Adicionado**, **Alterado**, **Corrigido**, **Removido**. Cada item indica a etapa do roadmap.
- Depois do reload no PythonAnywhere, confira no rodapé do site se a versão exibida é a publicada.

---

## [Não lançado]

---

## [5.1.1] — 2026-11-20

### Corrigido

- Tarefa com status e recorrência de acentuação corrompida (ex.: `ConcluÃ\xadda`) não aparecia no filtro "Concluída". Migração automática corrige os valores gravados assim. (Etapa 5)
- Iniciar e concluir etapa preenchem a hora de início e a hora de fim com a hora de São Paulo; antes, gravavam a hora UTC (3 h à frente). (Etapa 5)

### Alterado

- Datas internas em UTC geradas sem `datetime.utcnow()`, obsoleto no Python 3.12; mesmo formato gravado no banco. (Etapa 5)

---

## [5.1.0] — 2026-11-20

### Adicionado

- Data de criação da tarefa, no horário de São Paulo, em Minhas Tarefas, na edição e nos cartões do Calendário. (Etapa 3)
- Data de início (opcional) com a hora de início; cada hora passa a pertencer à sua data: Hora Início à data de início e Hora Fim à data realizado. A data meta fica sem hora. Tarefas pendentes sem data de início mostram o aviso "Sem data de início". Migração automática: coluna `data_inicio` e `hora_inicio` opcional (reconstrução da tabela `tarefa`; fazer backup antes). (Etapa 3)
- Atraso em relação à meta: "com X dias de atraso" nas tarefas concluídas depois da meta (Minhas Tarefas e Calendário) e "atrasada há X dias" nas pendentes em Minhas Tarefas. (Etapa 3)
- Calendário: seletor "Ver por: Meta | Início | Criação", guardado na URL junto com os filtros. No modo Início, arrastar muda a data de início (sem passar da meta); no modo Criação, arrastar fica desativado. (Etapa 3)
- A data de início não pode ser posterior à meta, nem no formulário nem ao arrastar no Calendário. (Etapa 3)

### Corrigido

- Concluir tarefa grava a data e a hora de São Paulo; antes, depois das 21:00 gravava o dia seguinte (UTC). (Etapa 3)

---

## [5.0.2] — 2026-11-20

### Corrigido

- Navegação: cadastrar, editar, duplicar, concluir e excluir tarefa (e editar etapa) voltam para a tela de origem, como o Calendário, em vez de sempre irem para Minhas Tarefas. Só caminhos internos são aceitos como retorno. (Etapa 2)
- Calendário: filtros, mês e dia selecionado ficam na URL e são restaurados ao voltar, ao atualizar a página ou pelo botão Voltar do navegador. (Etapa 2)
- Duplicar tarefa não deixa mais Minhas Tarefas filtrada pela prioridade da tarefa duplicada. (Etapa 2)
- Edição de tarefa com erro de validação (ex.: hora fim antes da hora início) mostra a mensagem na tela em vez de cair em erro. (Etapa 2)

---

## [5.0.1] — 2026-11-20

### Adicionado

- Versão da aplicação (`APP_VERSION`) exibida no rodapé, substituindo o texto fixo "V4".

### Corrigido

- Minhas Tarefas: trocar itens por página ou aplicar filtro volta para a página 1, em vez de mostrar uma lista vazia; página além do total mostra a última; itens por página só aceita 5, 10, 20, 50 ou 100 (antes, `per_page=0` gerava erro). Paginação feita no banco. (Etapa 1)
- Início: os indicadores (Total, Pendentes, Concluídas, Alta Prioridade, Hoje) ignoravam parte das tarefas por herdar os filtros de Minhas Tarefas, e abrir o Início trocava esses filtros. Agora são calculados no servidor, sem tocar nos filtros, e "Hoje" usa a data de São Paulo, não mais a de UTC. (Etapa 1)

---

## [5.0.0] — 2026-07-28

Primeira versão em produção (`todastarefas.com.br`). Marco inicial do versionamento semântico; corresponde à "V5" de `ai-context/mapa_projetoV5.md`.

### Adicionado

- Etapas de execução vinculadas a tarefas: ordem, status próprio (Criada, Iniciada, Pausada, Concluída), progresso da tarefa e histórico de ações.
- Duplicação de tarefa copiando as etapas.
- Etapas no Calendário pela data planejada.
- Testes locais de CRUD, segurança (IDOR) e renderização.

### Corrigido

- Renderização do cadastro de tarefa quando há erro de validação.
