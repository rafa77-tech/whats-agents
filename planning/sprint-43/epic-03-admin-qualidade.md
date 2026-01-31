# Epic 03 - Admin/Qualidade UI

## Objetivo
Criar pagina `/qualidade` para avaliacao de conversas, gestao de sugestoes de prompt e analise de qualidade das respostas da Julia.

## APIs Disponiveis (Backend Pronto - 16 endpoints)

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/admin/conversas` | GET | Lista conversas (filtros: status, avaliada) |
| `/admin/conversas/{id}` | GET | Conversa com interacoes |
| `/admin/conversas/por-tag/{tag}` | GET | Conversas por tag |
| `/admin/avaliacoes` | POST | Salva avaliacao |
| `/admin/sugestoes` | GET | Lista sugestoes |
| `/admin/sugestoes` | POST | Cria sugestao |
| `/admin/sugestoes/{id}` | PATCH | Atualiza status |
| `/admin/sugestoes/agregadas` | GET | Sugestoes por tipo |
| `/admin/tags` | GET | Tags disponiveis |
| `/admin/metricas/performance` | GET | Metricas de performance |
| `/admin/metricas/health` | GET | Health check |
| `/admin/validacao/metricas` | GET | Metricas do validador |
| `/admin/validacao/testar` | POST | Testa texto |
| `/admin/validacao/padroes` | GET | Padroes ativos |
| `/admin/validacao/corrigir` | POST | Corrige texto |
| `/admin/aberturas/variacao` | POST | Gera variacao |
| `/admin/aberturas/estatisticas` | GET | Stats de aberturas |

## Stories

---

### S43.E3.1 - Pagina Qualidade (Overview)

**Objetivo:** Dashboard de qualidade com metricas e filas de trabalho.

**Layout:**
```
+----------------------------------------------------------+
| Qualidade das Conversas                                   |
+----------------------------------------------------------+
| Metricas de Hoje:                                         |
| [Avaliadas]  [Pendentes]  [Score Medio]  [Validacoes]    |
|     45           12          4.2/5           98%         |
+----------------------------------------------------------+
| Filas de Trabalho:                                        |
| +------------------------+  +------------------------+   |
| | Conversas p/ Avaliar   |  | Sugestoes Pendentes    |   |
| | 12 novas               |  | 5 aguardando revisao   |   |
| | [Iniciar Avaliacao]    |  | [Ver Sugestoes]        |   |
| +------------------------+  +------------------------+   |
+----------------------------------------------------------+
| Validador de Output:                                      |
| Validacoes hoje: 1.234  |  Falhas: 23 (1.8%)             |
| Padroes mais violados: revelacao_ia (12), formato (8)    |
+----------------------------------------------------------+
```

**Tarefas:**
1. Criar rota `/qualidade` no dashboard
2. Cards de metricas (avaliadas, pendentes, score)
3. Cards de filas com contadores
4. Resumo do validador de output

**API Calls:**
- `GET /admin/metricas/performance`
- `GET /admin/conversas?avaliada=false&limit=1` - Contagem
- `GET /admin/sugestoes?status=pendente&limit=1` - Contagem
- `GET /admin/validacao/metricas`

**DoD:**
- [ ] Pagina criada
- [ ] Metricas em tempo real
- [ ] Links para filas de trabalho
- [ ] Testes unitarios

---

### S43.E3.2 - Lista de Conversas para Avaliacao

**Objetivo:** Interface para selecionar e avaliar conversas.

**Layout:**
```
+----------------------------------------------------------+
| Conversas para Avaliacao                        [Filtros] |
+----------------------------------------------------------+
| Status: [Todos v]  Avaliada: [Nao v]  Tag: [Todas v]     |
+----------------------------------------------------------+
| Conversa        | Medico      | Msgs | Status   | Acao   |
|-----------------|-------------|------|----------|--------|
| #1234 - 15/01   | Dr. Carlos  | 12   | Pendente | [Aval] |
| #1235 - 15/01   | Dra. Ana    | 8    | Pendente | [Aval] |
| #1230 - 14/01   | Dr. Pedro   | 15   | Avaliada | [Ver]  |
+----------------------------------------------------------+
| Mostrando conversas nao avaliadas das ultimas 48h        |
+----------------------------------------------------------+
```

**Tarefas:**
1. Criar componente `ConversationList`
2. Filtros por status, avaliada, tag
3. Ordenacao por data
4. Link para detalhe/avaliacao
5. Badge de status (pendente/avaliada)

**API Calls:**
- `GET /admin/conversas?avaliada=false&limit=20`
- `GET /admin/tags` - Tags disponiveis

**DoD:**
- [ ] Lista filtrada
- [ ] Badges de status
- [ ] Paginacao
- [ ] Testes unitarios

---

### S43.E3.3 - Avaliacao de Conversa

**Objetivo:** Interface completa para avaliar uma conversa.

**Layout:**
```
+----------------------------------------------------------+
| Avaliar Conversa #1234                           [Fechar] |
+----------------------------------------------------------+
| Historico:                        | Avaliacao:           |
| +----------------------------+    | Naturalidade: [1-5]  |
| | Julia: Oi Dr Carlos!       |    | ○○○○○                |
| | 14:30                      |    |                      |
| +----------------------------+    | Persona: [1-5]       |
| +----------------------------+    | ○○○○○                |
| | Dr Carlos: Oi, tudo bem?   |    |                      |
| | 14:32                      |    | Objetivo: [1-5]      |
| +----------------------------+    | ○○○○○                |
| +----------------------------+    |                      |
| | Julia: Tudo otimo! Vi que  |    | Satisfacao: [1-5]    |
| | vc é cardiologista...      |    | ○○○○○                |
| | 14:33                      |    |                      |
| +----------------------------+    | Tags:                |
|                                   | [+] Adicionar tag    |
|                                   |                      |
|                                   | Observacoes:         |
|                                   | [________________]   |
|                                   |                      |
|                                   | [Salvar Avaliacao]   |
+----------------------------------------------------------+
| [< Anterior]              [Proxima >]                     |
+----------------------------------------------------------+
```

**Tarefas:**
1. Criar pagina/modal `EvaluateConversation`
2. Exibir historico de mensagens
3. Form de avaliacao com ratings
4. Seletor de tags
5. Campo de observacoes
6. Navegacao entre conversas pendentes

**API Calls:**
- `GET /admin/conversas/{id}` - Detalhe
- `POST /admin/avaliacoes` - Salvar
- `GET /admin/tags` - Tags disponiveis

**DoD:**
- [ ] Historico legivel
- [ ] Ratings funcionais
- [ ] Tags selecionaveis
- [ ] Salvar com feedback
- [ ] Navegacao entre conversas
- [ ] Testes unitarios

---

### S43.E3.4 - Gestao de Sugestoes de Prompt

**Objetivo:** Interface para criar, revisar e aprovar sugestoes de melhoria.

**Layout:**
```
+----------------------------------------------------------+
| Sugestoes de Prompt                      [Nova Sugestao] |
+----------------------------------------------------------+
| Status: [Pendentes v]  Tipo: [Todos v]                   |
+----------------------------------------------------------+
| Tipo       | Descricao                | Status  | Acoes  |
|------------|--------------------------|---------|--------|
| tom        | Julia muito formal em... | pending | [R][A] |
| resposta   | Falta mencionar valor... | pending | [R][A] |
| abertura   | Variacao de saudacao...  | impl.   | [Ver]  |
+----------------------------------------------------------+

--- Modal Nova Sugestao ---

+------------------------------------------+
| Nova Sugestao                    [Fechar] |
+------------------------------------------+
| Tipo: [Selecione v]                       |
|       - tom                               |
|       - resposta                          |
|       - abertura                          |
|       - objecao                           |
+------------------------------------------+
| Descricao:                                |
| [________________________________]        |
+------------------------------------------+
| Exemplos (opcional):                      |
| [________________________________]        |
+------------------------------------------+
| [Cancelar] [Criar Sugestao]              |
+------------------------------------------+
```

**Legenda acoes:** R=Rejeitar, A=Aprovar

**Tarefas:**
1. Criar componente `SuggestionList`
2. Filtros por status e tipo
3. Modal para criar nova sugestao
4. Acoes de aprovar/rejeitar com confirmacao
5. Historico de sugestoes implementadas

**API Calls:**
- `GET /admin/sugestoes?status=pendente`
- `POST /admin/sugestoes` - Criar
- `PATCH /admin/sugestoes/{id}` - Atualizar status

**DoD:**
- [ ] Lista filtrada
- [ ] Criar sugestao funcional
- [ ] Aprovar/rejeitar com confirmacao
- [ ] Testes unitarios

---

## Navegacao

Adicionar na sidebar:
```
Gestao
├── Medicos
├── Vagas
├── Campanhas
└── Qualidade   <- NOVO
```

## Componentes Reutilizaveis

1. `RatingInput` - Input de 1-5 estrelas
2. `TagSelector` - Seletor de tags com autocomplete
3. `MessageBubble` - Bolha de mensagem (reutilizar de conversas)
4. `SuggestionCard` - Card de sugestao com acoes

## Consideracoes Tecnicas

- Atalhos de teclado para avaliacao rapida (1-5, N=proxima)
- Cache de conversas para navegacao rapida
- Autosave de avaliacao em progresso
