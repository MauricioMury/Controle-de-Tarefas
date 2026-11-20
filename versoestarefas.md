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

Nada ainda.

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
