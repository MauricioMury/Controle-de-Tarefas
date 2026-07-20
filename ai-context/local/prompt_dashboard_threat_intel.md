# Prompt — Dashboard HTML de Inteligência de Ameaças (Trend Micro Workbench)

## Contexto do projeto

Você é um desenvolvedor Python sênior trabalhando em um projeto que consome a API do **Trend Micro Vision One (XDR Workbench)** e persiste os dados em um banco **PostgreSQL** via **SQLAlchemy**.

O objetivo desta tarefa é gerar um **dashboard analítico em HTML puro** (sem frameworks JS, sem React, sem Vue) que responda perguntas operacionais de segurança sobre os alertas coletados, tais como;

- Máquinas afetadas → impacted_entity onde entity_type = 'host', com nome, GUID e IPs via entity_ip

- Contas afetadas → impacted_entity onde entity_type = 'account', com entity_value

- Como foram afetadas / tipo de ataque → matched_rule.name + matched_filter.name + técnicas MITRE via filter_mitre_technique

- Acesso de dentro pra fora (egress/C2) → indicators do tipo domain e ip com field = 'hostName' ou objectIps — como o caso do Rave.exe → reddit.com nos seus logs

- Acesso de fora pra dentro (ingress) → indicators do tipo fullpath com field filePathName + processName como o sftp-server no caso do Apache

- Arquivos maliciosos / suspeitos → indicators do tipo fullpath (processFilePath, filePathName) e command_line

- Processos suspeitos → indicators do tipo command_line (processCmd, parentCmd)

- Técnicas MITRE ATT&CK — quais TTPs foram acionadas (T1071, T1071.001 etc.) — ótimo para maturidade

- Hosts mais recorrentes — mesma máquina aparecendo em múltiplos alertas = prioridade de remediação

- Contas mais visadas — idem para usuários

- Timeline de eventos — matched_event.matched_datetime dá granularidade de quando cada evento ocorreu dentro do período

- Modelos/regras mais disparadas — quais detecções são mais frequentes (ruído vs. ameaça real)

- Tipos de evento (TELEMETRY_DNS, PRODUCT_EVENT_LOG) — separa C2 via DNS de modificação de arquivo, etc.

- Score de risco por host — agregado dos score dos alertas por máquina
________________________________________

O dashboard será servido por um endpoint Flask/FastAPI que executa as consultas SQLAlchemy e injeta os dados no template via Jinja2.

---

## Schema do banco de dados (SQLAlchemy)

As tabelas abaixo já existem no banco. Use-as exatamente como estão — não crie novas colunas.

```
workbench_alert         → alertas principais (id, severity, status, score, created_datetime, ...)
alert_model             → modelo de detecção (id, name, model_type)
impact_scope            → contagens de impacto por alerta (desktop_count, server_count, account_count, ...)
impacted_entity         → entidades afetadas (entity_type: 'host' | 'account', entity_name, entity_value, entity_guid, ...)
entity_ip               → IPs vinculados a cada entidade (ip_address)
indicator               → indicadores de comprometimento (type, field, value, provenance)
entity_indicator_rel    → relação N:N entre entidades e indicadores
matched_rule            → regras disparadas (name)
matched_filter          → filtros dentro das regras (name, matched_datetime)
filter_mitre_technique  → técnicas MITRE ATT&CK mapeadas (mitre_technique_id)
matched_event           → eventos individuais (event_type: TELEMETRY_DNS | PRODUCT_EVENT_LOG, matched_datetime)
```

**Tipos de indicador relevantes para o dashboard:**
- `type = 'host'`, `field = 'interestedHost'` → hostname afetado
- `type = 'domain'`, `field = 'hostName'` → domínio externo acessado (egresso)
- `type = 'ip'`, `field = 'objectIps'` → IP externo acessado (egresso)
- `type = 'ip'`, `provenance = 'Network Enrichment'` → IPs enriquecidos da rede
- `type = 'fullpath'`, `field IN ('filePathName', 'processFilePath')` → arquivo suspeito
- `type = 'command_line'`, `field IN ('processCmd', 'parentCmd')` → processo suspeito
- `type = 'user_account'` → conta de usuário envolvida
- `type = 'detection_name'` → nome da detecção (ex: "Application - Apache HTTP Server")

**Lógica de direção do tráfego:**
- **Egresso (interno → externo):** indicadores `type='domain'` ou `type='ip'` com `field='objectIps'`, provenientes de alertas cujo `matched_filter.name` contém "Non-Browser" ou "Twitter" ou "Reddit", e cujo `event_type = 'TELEMETRY_DNS'`
- **Ingresso (externo → interno):** indicadores `type='fullpath'` com `field='filePathName'` provenientes de processos como `sftp-server`, ou alertas cujo modelo envolve modificação de arquivos de servidor web

---

## Camada de dados — o que gerar com SQLAlchemy

Crie um módulo `dashboard_queries.py` com funções separadas para cada seção do dashboard. Cada função recebe `db: Session`, `date_from: datetime`, `date_to: datetime` e retorna um dict ou lista de dicts serializáveis (strings, ints, floats — sem objetos ORM).

### Função 1 — `get_kpis(db, date_from, date_to) -> dict`
Retorna:
```python
{
  "total_alerts": int,           # count de workbench_alert no período
  "hosts_afetados": int,         # impacted_entity distintos com entity_type='host'
  "contas_afetadas": int,        # impacted_entity distintos com entity_type='account'
  "acessos_egresso": int,        # indicators com type='domain' ou (type='ip' AND field='objectIps')
  "acessos_ingresso": int,       # indicators com type='fullpath' AND field='filePathName'
  "arquivos_suspeitos": int,     # indicators com type='fullpath' distintos
  "processos_suspeitos": int,    # indicators com type='command_line' distintos
  "tecnicas_mitre": int,         # filter_mitre_technique distintas no período
}
```

### Função 2 — `get_hosts_afetados(db, date_from, date_to) -> list[dict]`
Retorna lista ordenada por `alert_count DESC`, máximo 20 registros:
```python
[{
  "entity_name": str,            # impacted_entity.entity_name (hostname)
  "entity_guid": str,
  "ips": list[str],              # entity_ip.ip_address[] para esta entidade
  "entity_type": str,            # 'host'
  "alert_count": int,            # quantos alertas distintos envolvem este host
  "pior_severidade": str,        # 'high' | 'medium' | 'low' — pior entre os alertas
  "vetores": list[str],          # ex: ['egresso', 'arquivo', 'processo']
  "ultimo_alerta": str,          # ISO date do alerta mais recente
}]
```

### Função 3 — `get_contas_afetadas(db, date_from, date_to) -> list[dict]`
Retorna lista de contas com `entity_type='account'`, ordenada por `alert_count DESC`, máximo 20:
```python
[{
  "entity_value": str,           # ex: "DOMINIO\\usuario" ou nome completo
  "alert_count": int,
  "ultimo_alerta": str,          # ISO date
  "direcoes": list[str],         # ['egresso'] ou ['ingresso'] ou ambos
}]
```

### Função 4 — `get_vetores_acesso(db, date_from, date_to) -> dict`
```python
{
  "total_egresso": int,
  "total_ingresso": int,
  "por_tipo": [
    {"label": str, "count": int, "direcao": "egresso"|"ingresso"},
    ...
  ]   # ex: "DNS não-browser → domínio externo", "SFTP externo → arquivo web", etc.
}
```

### Função 5 — `get_arquivos_processos(db, date_from, date_to) -> list[dict]`
```python
[{
  "value": str,                  # caminho ou command line
  "type": str,                   # 'fullpath' | 'command_line'
  "field": str,                  # 'filePathName' | 'processFilePath' | 'processCmd' | etc.
  "alert_count": int,
  "hosts": list[str],            # hostnames envolvidos
}]
```
Ordenar por `alert_count DESC`, máximo 30.

### Função 6 — `get_ips_externos(db, date_from, date_to) -> list[dict]`
Indicadores `type='ip'` com `field='objectIps'` ou `provenance='Network Enrichment'`:
```python
[{
  "ip": str,
  "alert_count": int,
  "hosts_origem": list[str],
  "direcao": str,                # 'egresso' | 'ingresso'
  "dominios_associados": list[str],  # domínios do mesmo alerta
}]
```

### Função 7 — `get_tecnicas_mitre(db, date_from, date_to) -> list[dict]`
```python
[{
  "technique_id": str,           # ex: "T1071.001"
  "alert_count": int,
  "filtros": list[str],          # nomes dos matched_filters que dispararam
}]
```

### Função 8 — `get_modelos_disparados(db, date_from, date_to) -> list[dict]`
```python
[{
  "model_name": str,             # alert_model.name
  "model_type": str,             # 'preset' | 'custom'
  "alert_count": int,
  "percentual": float,           # em relação ao total de alertas no período
}]
```

### Função 9 — `get_timeline_eventos(db, date_from, date_to) -> list[dict]`
Agrupa `matched_event.matched_datetime` por hora:
```python
[{
  "hora": str,                   # ex: "2026-06-18T04:00"
  "egresso": int,                # eventos TELEMETRY_DNS nessa hora
  "ingresso": int,               # eventos PRODUCT_EVENT_LOG com arquivo nessa hora
  "total": int,
}]
```

---

## Dashboard HTML — especificação visual

Gere um único arquivo `dashboard_threat_intel.html` com HTML + CSS + JavaScript inline. **Não use nenhum framework JS externo** — apenas Chart.js carregado via CDN para os gráficos.

### Estrutura de páginas/seções (navegação por âncora ou scroll)

```
[Barra de filtros fixa no topo]
  └─ Seletor de período: últimos 7d / 15d / 30d / 90d / personalizado
  └─ Filtro de severidade: Todas / Alta / Média / Baixa
  └─ Botão "Atualizar dados" (recarrega a página com novos parâmetros GET)

[Seção 1] KPIs — 8 cards numéricos em grid
[Seção 2] Hosts afetados — tabela com filtro servidor/desktop
[Seção 3] Contas afetadas — tabela
[Seção 4] Vetores de acesso — cards egresso vs. ingresso + barras horizontais
[Seção 5] Arquivos e processos suspeitos — tabela com badges por tipo
[Seção 6] IPs externos — tabela com direção e domínios associados
[Seção 7] Técnicas MITRE ATT&CK — tags visuais + tabela de frequência
[Seção 8] Modelos de detecção — barras horizontais + % do total
[Seção 9] Timeline de eventos — gráfico de linha (Chart.js) por hora
```

### Regras visuais obrigatórias

- Fundo branco (`#ffffff`), texto principal `#0b0b0b`, texto secundário `#52514e`
- Cards KPI: fundo `#f5f5f3`, sem borda, border-radius 8px, padding 14px 16px
- Cards de seção: fundo branco, borda `0.5px solid rgba(11,11,11,0.1)`, border-radius 12px
- Tabelas: sem borda externa, linhas separadas por `border-bottom: 0.5px solid rgba(11,11,11,0.1)`
- Badges de severidade: `high` → fundo `#fceaea` texto `#a32d2d`; `medium` → `#fef4e0` / `#7a5200`; `low` → `#eaf3de` / `#3b6d11`
- Badges de direção: `egresso` → `#e6f1fb` / `#0c447c`; `ingresso` → `#faece7` / `#993c1d`
- Badges de tipo de indicador: `arquivo` → `#eeedfe` / `#3c3489`; `processo/cmd` → `#fbeaf0` / `#993556`
- Tags MITRE: fundo `#f0effc`, texto `#3c3489`, border-radius 100px, padding 3px 10px
- Fonte: `system-ui, -apple-system, sans-serif`; nunca abaixo de 11px
- Números nos KPIs: 26px, font-weight 500
- Sem gradientes, sem sombras decorativas, sem bordas arredondadas em bordas simples (border-left/top)

### Paleta de cores para gráficos (Chart.js — hex direto, não CSS vars)

```
Série 1 (egresso/azul):   #2a78d6
Série 2 (ingresso/coral): #d85a30
Série 3 (neutro):         #888780
Gridlines:                #e1e0d9
Labels dos eixos:         #898781
```

### Integração com Jinja2

O HTML usa variáveis Jinja2 injetadas pelo endpoint Flask/FastAPI. As seções de dados são renderizadas como JSON embutido em `<script>` tags:

```html
<script>
  const DATA_KPIS = {{ kpis | tojson }};
  const DATA_HOSTS = {{ hosts | tojson }};
  const DATA_CONTAS = {{ contas | tojson }};
  const DATA_VETORES = {{ vetores | tojson }};
  const DATA_ARQUIVOS = {{ arquivos | tojson }};
  const DATA_IPS = {{ ips_externos | tojson }};
  const DATA_MITRE = {{ mitre | tojson }};
  const DATA_MODELOS = {{ modelos | tojson }};
  const DATA_TIMELINE = {{ timeline | tojson }};
  const FILTROS = {{ filtros | tojson }};  // {periodo_dias: 15, severidade: 'all', date_from: '...', date_to: '...'}
</script>
```

O JavaScript lê essas variáveis e popula o DOM — sem nenhuma chamada fetch/AJAX.

---

## Endpoint Flask/FastAPI — especificação

Crie um endpoint `GET /dashboard/threat-intel` com parâmetros de query:

```
?periodo=15          # dias para trás a partir de hoje (default: 15)
?severidade=all      # 'all' | 'high' | 'medium' | 'low'
?date_from=          # opcional, ISO date — sobrepõe periodo
?date_to=            # opcional, ISO date
```

O endpoint deve:
1. Calcular `date_from` e `date_to` com base nos parâmetros
2. Chamar todas as 9 funções de `dashboard_queries.py` com a mesma `db` e datas
3. Aplicar o filtro de severidade no nível das queries (parâmetro adicional nas funções)
4. Renderizar o template `dashboard_threat_intel.html` com os dados
5. Retornar `Content-Type: text/html`

Tratar erros de banco com try/except: se uma query falhar, retornar o dado vazio correspondente (lista `[]` ou dict com zeros) e logar o erro — não quebrar o dashboard inteiro.

---

## Comportamento interativo (JavaScript puro, sem frameworks)

### Filtro de hosts (servidor/desktop)
Botões "Todos / Servidores / Desktops" filtram as linhas da tabela de hosts pelo atributo `data-htype` de cada `<tr>`. Implementar em JS puro com `querySelectorAll` e `style.display`.

### Ordenação de tabelas
Clique no cabeçalho de cada `<th>` ordena a tabela por aquela coluna (toggle asc/desc). Implementar com sort em array JS e re-renderização do `<tbody>`.

### Tooltip nos gráficos Chart.js
Usar o plugin de tooltip padrão do Chart.js, configurado com `mode: 'index'` e `intersect: false`.

### Período personalizado
Se `periodo=custom`, exibir dois `<input type="date">` na barra de filtros. Ao clicar "Atualizar", redirecionar para `?date_from=...&date_to=...`.

---

## Observações de qualidade

- Todas as queries SQLAlchemy devem usar `joinedload` ou `selectinload` onde houver risco de N+1 (ex: ao buscar IPs de cada entidade, não iterar por entidade fazendo query individual)
- Usar `.distinct()` em contagens de entidades para evitar duplicatas da relação N:N
- Datas armazenadas como `TIMESTAMP WITH TIME ZONE` — comparar sempre com objetos `datetime` timezone-aware
- Números exibidos no dashboard: sempre `Math.round()` antes de renderizar, sem casas decimais desnecessárias
- Percentuais: uma casa decimal, ex: `"22.4%"`
- O arquivo HTML final deve funcionar offline após carregamento inicial (Chart.js via CDN é a única dependência externa)
