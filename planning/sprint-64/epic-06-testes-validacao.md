# EPICO 06: Testes & Validacao

## Contexto

Todos os epicos anteriores fazem mudancas significativas na pagina /conversas. Este epico garante que tudo funciona junto, com testes de regressao e validacao end-to-end.

## Escopo

- **Incluido**: Testes unitarios para novos componentes, testes de integracao para API routes, testes E2E para fluxos criticos, validacao cross-browser
- **Excluido**: Testes de backend Python (cobertos nos respectivos epicos do backend)

---

## Tarefa 6.1: Testes unitarios — novos componentes

### Objetivo

Criar testes para todos os novos componentes criados nos epicos anteriores.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `dashboard/__tests__/conversas/attention-feed.test.tsx` |
| Criar | `dashboard/__tests__/conversas/conversation-summary.test.tsx` |
| Criar | `dashboard/__tests__/conversas/context-drawer.test.tsx` |
| Modificar | `dashboard/__tests__/conversas/chat-sidebar.test.tsx` |

### Cobertura por componente

**AttentionFeed (Epic 04):**
- [ ] Renderiza cards com motivo correto para cada tipo de atencao
- [ ] Botao "Assumir" funciona para conversas AI
- [ ] Botao "Assumir" nao aparece para conversas Human
- [ ] Botao "Ver conversa" funciona
- [ ] Lista vazia mostra estado vazio

**ConversationSummary (Epic 05):**
- [ ] Renderiza resumo de texto
- [ ] Renderiza metricas
- [ ] Dismiss funciona
- [ ] Dados parciais nao quebram

**ChatSidebar simplificado (Epic 04):**
- [ ] Card mostra max 6 sinais visuais
- [ ] Especialidade na mesma linha do nome
- [ ] Sem chip info, sem stage badge, sem check marks
- [ ] Borda de urgencia funciona

**Context drawer (Epic 03):**
- [ ] Renderiza como Sheet em telas < lg
- [ ] Fecha ao clicar fora
- [ ] Dados do DoctorContextPanel corretos

### Definition of Done

- [ ] Cobertura >= 80% nos componentes novos
- [ ] Todos os testes passando
- [ ] Sem snapshots frageis (testar comportamento, nao markup)

### Estimativa

4h

---

## Tarefa 6.2: Testes de integracao — API routes

### Objetivo

Validar que as mudancas nas API routes retornam dados corretos.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `dashboard/__tests__/api/conversas-route.test.ts` |
| Criar | `dashboard/__tests__/api/conversas-counts.test.ts` |

### Cenarios

**GET /api/conversas:**
- [ ] Retorna todas conversas quando chipId=null
- [ ] Retorna conversas filtradas por chipId (incluindo backfilled)
- [ ] Retorna last_message correto (1 por conversa, nao N+1)
- [ ] Retorna attention_reason quando tab=atencao
- [ ] Retorna unread_count real (nao 0)
- [ ] Paginacao funcional (page, per_page)
- [ ] Tab filtering server-side (nao truncado por limit)
- [ ] Search funciona por nome e telefone

**GET /api/conversas/counts:**
- [ ] Contagens reais para todas as tabs
- [ ] Contagem aguardando baseada em dados reais (nao 30%)
- [ ] Filtro por chipId funciona
- [ ] Fallback retorna contagens corretas (nao estimativas)

### Definition of Done

- [ ] Testes de integracao para ambas as routes
- [ ] Cobertura dos cenarios de edge case
- [ ] Sem mocks frageis (usar fixtures de dados reais)

### Estimativa

3h

---

## Tarefa 6.3: Testes E2E — fluxos criticos

### Objetivo

Validar os fluxos completos de supervisao end-to-end.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `dashboard/__tests__/e2e/conversas-supervision.test.ts` |

### Fluxos a testar

**Fluxo 1: Triagem de atencao**
1. Acessar /conversas
2. Tab "Atencao" carrega com feed de triagem
3. Cada card mostra motivo
4. Clicar "Ver conversa" abre o chat
5. Clicar "Assumir" muda controle para humano

**Fluxo 2: Navegacao mobile**
1. Em viewport mobile (375px)
2. Lista de conversas visivel
3. Clicar conversa → chat visivel, lista escondida
4. Clicar voltar → lista visivel, chat escondido

**Fluxo 3: Supervisao de conversa**
1. Selecionar conversa Julia ativa
2. Resumo visivel no topo
3. Abrir context panel
4. Ver notas, memoria, metricas
5. Assumir conversa → input de mensagem aparece

**Fluxo 4: Filtro por chip**
1. Selecionar chip especifico
2. Conversas filtradas (incluindo antigas backfilled)
3. Contadores atualizados
4. Voltar para "Todos" mostra todas

### Definition of Done

- [ ] 4 fluxos E2E passando
- [ ] Mobile e desktop cobertos
- [ ] Nenhum fluxo depende de dados hardcoded

### Estimativa

4h

---

## Tarefa 6.4: Validacao manual e checklist de regressao

### Objetivo

Checklist manual para validar antes de merge.

### Checklist

**Dados:**
- [ ] Conversas de todos os chips aparecem em "Todos"
- [ ] Filtro por chip mostra conversas corretas (incluindo antigas)
- [ ] Contadores de tabs batem com realidade
- [ ] unread_count reflete mensagens nao respondidas

**Funcionalidade:**
- [ ] Tab "Atencao" mostra motivos claros
- [ ] Clicar "Assumir" no feed de triagem funciona
- [ ] Resumo de conversa aparece ao abrir chat
- [ ] Feedback em mensagens funciona (sem NaN)
- [ ] Notas recarregam ao trocar conversa
- [ ] Supervisor channel funciona

**Mobile:**
- [ ] Lista → Chat → Voltar funcional
- [ ] Context panel abre como drawer
- [ ] Layout nao quebra em 375px

**Performance:**
- [ ] Sem polling duplo (verificar Network tab)
- [ ] Lista de conversas carrega < 500ms
- [ ] Troca de conversa carrega < 300ms
- [ ] Sem requests desnecessarios ao trocar tabs

**Regressao:**
- [ ] Enviar mensagem (handoff mode) funciona
- [ ] Emoji picker funciona
- [ ] Audio recording funciona
- [ ] Attachment upload funciona
- [ ] SSE real-time funciona
- [ ] Nova conversa dialog funciona

### Definition of Done

- [ ] Todos os items do checklist validados
- [ ] Screenshots/videos dos fluxos principais
- [ ] Zero regressoes identificadas

### Estimativa

2h
