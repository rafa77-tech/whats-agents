# Epic 02 - Group Entry UI

## Objetivo
Criar pagina `/grupos` para gestao completa do Group Entry Engine: importacao de links, validacao, agendamento, fila e configuracao.

## APIs Disponiveis (Backend Pronto - 21 endpoints)

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/group-entry/import/csv` | POST | Importa CSV |
| `/group-entry/import/excel` | POST | Importa Excel |
| `/group-entry/links` | GET | Lista links (filtros) |
| `/group-entry/links/stats` | GET | Stats por status |
| `/group-entry/links/{id}` | GET | Detalhe do link |
| `/group-entry/validate/{id}` | POST | Valida link |
| `/group-entry/validate/batch` | POST | Valida lote |
| `/group-entry/revalidate/{id}` | POST | Revalida link |
| `/group-entry/schedule` | POST | Agenda entrada |
| `/group-entry/schedule/batch` | POST | Agenda lote |
| `/group-entry/queue` | GET | Lista fila |
| `/group-entry/queue/stats` | GET | Stats da fila |
| `/group-entry/queue/{id}` | DELETE | Cancela agendamento |
| `/group-entry/process` | POST | Processa fila |
| `/group-entry/process/{id}` | POST | Processa especifico |
| `/group-entry/check-pending` | POST | Verifica pendentes |
| `/group-entry/chips` | GET | Chips disponiveis |
| `/group-entry/capacity` | GET | Capacidade total |
| `/group-entry/config` | GET | Config atual |
| `/group-entry/config` | PATCH | Atualiza config |
| `/group-entry/dashboard` | GET | Visao consolidada |

## Stories

---

### S43.E2.1 - Pagina Principal Group Entry

**Objetivo:** Dashboard consolidado do Group Entry com metricas e acoes rapidas.

**Layout:**
```
+----------------------------------------------------------+
| Entrada em Grupos                      [Importar] [Config]|
+----------------------------------------------------------+
| Capacidade: 45/100 grupos              [=====-----] 45%   |
+----------------------------------------------------------+
| Links        | Fila         | Processados Hoje           |
| 234 total    | 12 agendados | 8 sucesso / 2 falha        |
| 45 pendentes | 3 em processo|                            |
+----------------------------------------------------------+
| Acoes Rapidas:                                            |
| [Validar Pendentes] [Agendar Validados] [Processar Fila] |
+----------------------------------------------------------+
```

**Tarefas:**
1. Criar rota `/grupos` no dashboard
2. Criar componente `GroupEntryDashboard`
3. Card de capacidade com barra de progresso
4. Cards de metricas (links, fila, processados)
5. Botoes de acoes rapidas com confirmacao

**API Calls:**
- `GET /group-entry/dashboard` - Dados consolidados
- `GET /group-entry/capacity` - Capacidade
- `POST /group-entry/validate/batch` - Validar pendentes
- `POST /group-entry/schedule/batch` - Agendar validados
- `POST /group-entry/process` - Processar fila

**DoD:**
- [ ] Pagina criada e acessivel
- [ ] Metricas em tempo real
- [ ] Acoes rapidas funcionais
- [ ] Confirmacao para acoes em lote
- [ ] Testes unitarios

---

### S43.E2.2 - Importacao de Links

**Objetivo:** Interface para importar links de grupos via CSV/Excel.

**Layout:**
```
+------------------------------------------+
| Importar Links                   [Fechar] |
+------------------------------------------+
| Arraste um arquivo CSV ou Excel aqui      |
| ou [Selecionar arquivo]                   |
+------------------------------------------+
| Formato esperado:                         |
| link, categoria (opcional)                |
| https://chat.whatsapp.com/xxx, medicos    |
+------------------------------------------+
| [Baixar template CSV]                     |
+------------------------------------------+

--- Apos upload ---

+------------------------------------------+
| Resultado da Importacao                   |
+------------------------------------------+
| Total: 50 links                           |
| Validos: 45                               |
| Duplicados: 3                             |
| Invalidos: 2                              |
+------------------------------------------+
| Erros:                                    |
| Linha 12: URL invalida                    |
| Linha 34: Formato incorreto               |
+------------------------------------------+
| [Cancelar] [Importar 45 links validos]   |
+------------------------------------------+
```

**Tarefas:**
1. Criar modal `ImportLinksModal`
2. Componente de drag-and-drop para arquivos
3. Validacao client-side do formato
4. Preview de resultados da importacao
5. Feedback detalhado de erros

**API Calls:**
- `POST /group-entry/import/csv` ou `/import/excel`

**DoD:**
- [ ] Upload drag-and-drop funcional
- [ ] Suporte a CSV e Excel
- [ ] Preview de resultados
- [ ] Erros claros por linha
- [ ] Template downloadavel
- [ ] Testes unitarios

---

### S43.E2.3 - Lista de Links com Acoes

**Objetivo:** Tabela de links com filtros, validacao e agendamento individual.

**Layout:**
```
+----------------------------------------------------------+
| Links                                    [Filtros] [Export]|
+----------------------------------------------------------+
| Status: [Todos v] Categoria: [Todas v] Busca: [_______]   |
+----------------------------------------------------------+
| Link                  | Status    | Categoria | Acoes     |
|-----------------------|-----------|-----------|-----------|
| chat.whatsapp.com/abc | pending   | medicos   | [V][A][X] |
| chat.whatsapp.com/def | validated | geral     | [A][X]    |
| chat.whatsapp.com/ghi | scheduled | medicos   | [C]       |
+----------------------------------------------------------+
| Selecionados: 3  [Validar] [Agendar] [Excluir]           |
+----------------------------------------------------------+
```

**Legenda acoes:** V=Validar, A=Agendar, X=Excluir, C=Cancelar

**Tarefas:**
1. Criar componente `LinkList` com tabela
2. Filtros por status, categoria
3. Busca por URL
4. Acoes individuais (validar, agendar, excluir)
5. Selecao multipla com acoes em lote
6. Paginacao

**API Calls:**
- `GET /group-entry/links?status=X&categoria=Y&limit=20`
- `POST /group-entry/validate/{id}`
- `POST /group-entry/schedule` com link_id
- `DELETE /group-entry/links/{id}` (se disponivel)

**DoD:**
- [ ] Tabela com filtros
- [ ] Acoes individuais funcionais
- [ ] Selecao e acoes em lote
- [ ] Paginacao
- [ ] Testes unitarios

---

### S43.E2.4 - Fila de Processamento

**Objetivo:** Visualizar e gerenciar a fila de entrada em grupos.

**Layout:**
```
+----------------------------------------------------------+
| Fila de Processamento                          [Refresh]  |
+----------------------------------------------------------+
| Proximas Entradas:                                        |
+----------------------------------------------------------+
| # | Link          | Chip    | Agendado    | Status | Acao|
|---|---------------|---------|-------------|--------|-----|
| 1 | .../abc       | chip_01 | 14:30       | queued | [C] |
| 2 | .../def       | chip_02 | 14:35       | queued | [C] |
| 3 | .../ghi       | chip_01 | processing  | -      | [-] |
+----------------------------------------------------------+
| Chips Disponiveis: chip_01 (3 slots), chip_02 (5 slots)  |
+----------------------------------------------------------+
| [Processar Proximo] [Processar Todos]                    |
+----------------------------------------------------------+
```

**Tarefas:**
1. Criar componente `ProcessingQueue`
2. Lista ordenada por horario agendado
3. Status em tempo real (polling)
4. Cancelamento individual
5. Exibir chips disponiveis com capacidade
6. Botoes de processamento manual

**API Calls:**
- `GET /group-entry/queue` - Lista fila
- `GET /group-entry/queue/stats` - Stats
- `GET /group-entry/chips` - Chips disponiveis
- `DELETE /group-entry/queue/{id}` - Cancelar
- `POST /group-entry/process/{id}` - Processar especifico
- `POST /group-entry/process` - Processar todos

**DoD:**
- [ ] Fila ordenada visivel
- [ ] Status em tempo real
- [ ] Cancelamento funcional
- [ ] Chips com capacidade
- [ ] Testes unitarios

---

### S43.E2.5 - Configuracao do Group Entry

**Objetivo:** Tela para configurar limites e comportamento do Group Entry.

**Layout:**
```
+------------------------------------------+
| Configuracao do Group Entry      [Salvar] |
+------------------------------------------+
| Limites por Chip:                         |
| Grupos por dia:        [10] (max 20)      |
| Intervalo entre (min): [30] minutos       |
| Intervalo entre (max): [60] minutos       |
+------------------------------------------+
| Horario de Operacao:                      |
| Inicio: [08]:00  Fim: [20]:00             |
| Dias: [x]Seg [x]Ter [x]Qua [x]Qui [x]Sex  |
+------------------------------------------+
| Comportamento:                            |
| [x] Auto-validar links importados         |
| [ ] Auto-agendar links validados          |
| [x] Notificar falhas no Slack             |
+------------------------------------------+
```

**Tarefas:**
1. Criar modal/pagina `GroupEntryConfig`
2. Form com validacao de limites
3. Seletor de horario e dias
4. Toggles de comportamento
5. Salvar com confirmacao

**API Calls:**
- `GET /group-entry/config` - Config atual
- `PATCH /group-entry/config` - Atualizar

**DoD:**
- [ ] Form com valores atuais
- [ ] Validacao de limites
- [ ] Salvar funcional
- [ ] Feedback de sucesso/erro
- [ ] Testes unitarios

---

## Navegacao

Adicionar na sidebar:
```
Operacao
├── Dashboard
├── Monitor
├── Integridade
├── Grupos       <- NOVO
└── Health Center
```

## Componentes Reutilizaveis

1. `FileDropzone` - Area de drag-and-drop para arquivos
2. `StatusBadge` - Badge por status do link (pending, validated, etc)
3. `CapacityBar` - Barra de capacidade com slots usados/disponiveis
4. `ChipSelector` - Seletor de chip para agendamento

## Consideracoes Tecnicas

- Polling a cada 30s na fila
- Confirmacao para todas as acoes destrutivas
- Limite de 100 links por importacao
- Virtualizacao para listas grandes
