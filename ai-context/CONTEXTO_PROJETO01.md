# 🧠 Contexto do Projeto — Controle de Tarefas

> **Finalidade deste arquivo:** Fornecer contexto completo ao Claude em novos chats,
> para manutenções e novas funcionalidades. Deve ser lido em conjunto com os arquivos
> do repositório GitHub (código-fonte sempre atualizado).

---

## 1. Visão Geral

| Item | Detalhe |
|------|---------|
| **Nome** | Controle de Tarefas |
| **Versão atual** | 4.0 (Abril 2026) |
| **Dono** | Mauricio |
| **Stack** | Python 3.11 + Flask + SQLite + Bootstrap 5 |
| **Repositório** | GitHub (fonte da verdade) |
| **Produção** | PythonAnywhere (plano pago) |
| **URL produção** | https://controletarefas.pythonanywhere.com |

---

## 2. Ambiente de Produção — PythonAnywhere

| Item | Valor |
|------|-------|
| **Usuário PA** | `controletarefas` |
| **Pasta do projeto** | `/home/controletarefas/controle_tarefas/` |
| **Templates** | `/home/controletarefas/controle_tarefas/templates/` |
| **Banco de dados** | `/home/controletarefas/controle_tarefas/instance/tarefas.db` |
| **Virtualenv** | `/home/controletarefas/.virtualenvs/venv_tarefas` |
| **Python** | 3.11 |
| **WSGI file** | `/var/www/controletarefas_pythonanywhere_com_wsgi.py` |

### 2.1 Conteúdo do WSGI

```python
import sys
import os

path = '/home/controletarefas/controle_tarefas'
if path not in sys.path:
    sys.path.append(path)

os.environ['FLASK_ENV'] = 'production'

from app import app as application
```

### 2.2 Como atualizar o deploy

Quando houver alterações no GitHub, no Bash do PythonAnywhere:

```bash
cd ~/controle_tarefas
git pull origin main
```

Depois clicar em **Reload** na aba **Web** do PythonAnywhere.

Se houver migração de banco:
```bash
workon venv_tarefas
cd ~/controle_tarefas
python migrar_estagio4_notif_dual.py  # ou o script de migração correspondente
```

### 2.3 Pacotes instalados no virtualenv

```bash
bcrypt==4.1.2
blinker==1.9.0
certifi==2026.2.25
charset-normalizer==3.4.6
click==8.3.1
colorama==0.4.6
Flask==3.0.0
Flask-Login==0.6.3
Flask-SQLAlchemy==3.1.1
greenlet==3.3.2
idna==3.11
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.3
requests==2.32.5
SQLAlchemy==2.0.48
typing_extensions==4.15.0
urllib3==2.6.3
Werkzeug==3.0.1```

---

## 3. Estrutura de Arquivos do Projeto

```
controle_tarefas/
├── app.py                        # Aplicação Flask principal — rotas, lógica
├── models.py                     # Modelos SQLAlchemy (User, Tarefa, Categoria)
├── notificacoes.py               # Envio de e-mail (Gmail SMTP) e WhatsApp (CallMeBot)
├── requirements.txt              # Dependências de produção
├── tarefas.db                    # Banco SQLite (não versionado no Git)
├── .env                          # Variáveis de ambiente (não versionado)
├── migrar_para_v3.py             # Migração V2→V3
├── migrar_estagio1_whatsapp.py   # Migração estágio 1 notificações
├── migrar_estagio3_notif2.py     # Migração estágio 3 notificações
├── migrar_estagio4_notif_dual.py # Migração estágio 4 (atual) — dual canal
├── GUIA_ATUALIZACAO_V3.md
├── GUIA_ATUALIZACAO_V4.md
├── mapa_projetoV4.md             # Documentação técnica detalhada do projeto
└── templates/
    ├── base.html                 # Template base — navbar, tema dark/light, footer
    ├── login.html                # Standalone — não estende base.html
    ├── register.html
    ├── index.html                # Dashboard com stats dinâmicas
    ├── cadastro_tarefa.html
    ├── editar_tarefa.html
    ├── lista_tarefas.html        # Filtros + busca + paginação
    ├── cadastro_categoria.html
    ├── editar_categoria.html
    ├── lista_categorias.html
    ├── perfil.html               # Configuração de e-mail e WhatsApp
    └── calendario.html           # Calendário visual de tarefas
```

---

## 4. Banco de Dados

### 4.1 Modelos

**User**
```python
id, username, password (bcrypt), email_notif,
whatsapp_numero, whatsapp_apikey
```

**Categoria**
```python
id, nome, cor (bootstrap class), user_id, created_at
```

**Tarefa**
```python
id, tarefa, comentario, data_meta, data_realizado,
hora_inicio, hora_fim, prioridade, recorrencia, categoria,
status, user_id, created_at,
notif_datetime_1, notif_email_enviada_1, notif_whatsapp_enviada_1,
notif_datetime_2, notif_email_enviada_2, notif_whatsapp_enviada_2
```

### 4.2 Relacionamentos
- `User` (1) → (N) `Tarefa` — cascade delete
- `User` (1) → (N) `Categoria` — cascade delete

### 4.3 Histórico de Migrações
| Script | O que fez |
|--------|-----------|
| `migrar_para_v3.py` | Criou tabela categoria, adicionou campo comentario |
| `migrar_estagio1_whatsapp.py` | Campos WhatsApp no User, notif simples na Tarefa |
| `migrar_estagio3_notif2.py` | Ajuste para 2 notificações por tarefa |
| `migrar_estagio4_notif_dual.py` | Suporte dual canal (e-mail + WhatsApp) por notificação |

---

## 5. Rotas da Aplicação

### Públicas
| Rota | Método | Descrição |
|------|--------|-----------|
| `/login` | GET, POST | Login |
| `/register` | GET, POST | Cadastro de usuário |

### Protegidas (login_required)
| Rota | Método | Descrição |
|------|--------|-----------|
| `/` | GET | Dashboard com stats |
| `/logout` | GET | Encerrar sessão |
| `/perfil` | GET, POST | Configurar e-mail e WhatsApp |
| `/cadastro_tarefa` | GET, POST | Nova tarefa |
| `/lista_tarefas` | GET | Lista + filtros + busca + paginação |
| `/editar_tarefa/<id>` | GET, POST | Editar tarefa |
| `/deletar_tarefa/<id>` | POST | Deletar tarefa |
| `/marcar_concluida/<id>` | POST | Marcar como concluída |
| `/duplicar_tarefa/<id>` | GET | Duplicar tarefa |
| `/mover_tarefa/<id>` | POST | Mover data via drag & drop calendário |
| `/categorias` | GET | Lista categorias |
| `/cadastro_categoria` | GET, POST | Nova categoria |
| `/editar_categoria/<id>` | GET, POST | Editar categoria |
| `/deletar_categoria/<id>` | POST | Deletar categoria |
| `/calendario` | GET | Calendário visual |

---

## 6. Funcionalidades Implementadas

### Autenticação
- Login/logout com Flask-Login
- Registro com hash bcrypt
- Cria categorias padrão automaticamente para novos usuários

### Tarefas
- CRUD completo
- Duplicar tarefa
- Marcar como concluída (preenche data_realizado automaticamente)
- Filtros: categoria, prioridade, status, data, busca por texto
- Filtros persistentes na sessão e URL
- Paginação configurável (5/10/20/50/100)
- Ordenação por data + hora

### Categorias
- CRUD completo
- Cores Bootstrap customizáveis
- Proteção: não deleta categoria em uso

### Notificações
- Até 2 notificações por tarefa
- Canal e-mail (Gmail SMTP via variável de ambiente)
- Canal WhatsApp (CallMeBot API)
- Processadas via `@app.before_request` — disparo automático
- Flag individual por canal (email/whatsapp) por notificação
- Reativa notificação se datetime for alterado na edição

### Interface
- Tema dark/light com toggle na navbar
- Preferência salva em `localStorage` (key: `ct-theme`), padrão: dark
- Design system com variáveis CSS (`--accent`, `--bg-card`, etc.)
- Tipografia: Inter (base.html atual usa Inter, mapa cita Syne+DM Sans — verificar)
- Calendário visual com navegação mensal/semanal (mobile)
- Dashboard com 5 cards de estatísticas

---

## 7. Decisões Técnicas Relevantes

- **SQLite** em produção — aceitável para uso pessoal/pequeno volume
- **Filtros via sessão Flask** — persistem entre páginas sem depender de JS
- **Paginação manual** — feita em Python, não via SQLAlchemy paginate (atenção ao escalar)
- **Notificações via before_request** — simples, mas dispara por usuário logado; não é cron
- **Categoria armazenada como string** na Tarefa (não FK) — facilita histórico mas dificulta renomear
- **debug=False** em produção — garantir que está assim no app.py
- **SECRET_KEY** hardcoded no app.py — deve ser movida para `.env`

---

## 8. Variáveis de Ambiente (.env)

```env
NOTIF_EMAIL_REMETENTE=seuemail@gmail.com
NOTIF_EMAIL_SENHA_APP=senha_de_app_google
```

⚠️ O `SECRET_KEY` do Flask ainda está hardcoded no `app.py` — recomendado mover para `.env`.

---

## 9. Segurança

| Item | Status |
|------|--------|
| SQL Injection | ✅ SQLAlchemy ORM |
| XSS | ✅ Jinja2 auto-escape |
| CSRF | ⚠️ Não implementado — recomendado Flask-WTF |
| Brute Force / Rate Limiting | ⚠️ Não implementado |
| SECRET_KEY em produção | ⚠️ Ainda hardcoded no app.py |

---

## 10. Roadmap

### Curto prazo
- [ ] Mover SECRET_KEY para .env
- [ ] Adicionar CSRF protection (Flask-WTF)
- [ ] Dashboard com gráficos (Chart.js)
- [ ] Exportar lista em PDF

### Médio prazo
- [ ] API REST
- [ ] Compartilhamento de tarefas entre usuários
- [ ] Integração Google Calendar

### Longo prazo
- [ ] Subtarefas
- [ ] Aplicativo mobile nativo
- [ ] Colaboração em tempo real
- [ ] CI/CD com GitHub Actions
- [ ] Migrations com Alembic

---

## 11. Histórico de Versões

| Versão | Data | Destaques |
|--------|------|-----------|
| V1 | Jan 2026 | CRUD de tarefas, autenticação básica |
| V2 | Jan 2026 | Filtros, paginação, categorias fixas |
| V3 | Fev 2026 | Categorias dinâmicas, comentários, filtros persistentes |
| V4 | Mar 2026 | Tema dark/light, redesign completo, filtro de busca, calendário, notificações dual canal |
| Deploy | Abr 2026 | Publicado no PythonAnywhere — https://controletarefas.pythonanywhere.com |

---

**Última atualização:** Abril 2026
**Mantido por:** Mauricio
