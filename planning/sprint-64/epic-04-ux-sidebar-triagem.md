# EPICO 04: UX Redesign — Sidebar & Triagem

## Contexto

A sidebar atual tem sobrecarga cognitiva (13+ sinais visuais por card de conversa) e a tab "Atencao" mostra a mesma lista sem explicar POR QUE cada conversa precisa de atencao. O supervisor precisa scanear visualmente cada conversa para encontrar problemas ao inves de ter os problemas apresentados de forma acionavel.

## Escopo

- **Incluido**: Simplificar card da sidebar, redesenhar tab "Atencao" como feed de triagem, melhorar hierarquia visual
- **Excluido**: Chat panel e context panel (Epic 05), backend/queries (Epics 01-02), mobile (Epic 03)

---

## Tarefa 4.1: Simplificar card de conversa na sidebar

### Objetivo

Reduzir de 13+ sinais visuais para ~6, movendo informacoes secundarias para o context panel.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/(dashboard)/conversas/components/chat-sidebar.tsx` |

### Design

**MANTER (essencial para scan rapido):**
1. Avatar com iniciais (cor por estado: AI azul / Handoff laranja)
2. Nome do medico + especialidade (1 linha)
3. Preview da ultima mensagem (1 linha, truncada)
4. Tempo desde ultima mensagem
5. Badge de estado (icone AI/Handoff, pequeno)
6. Borda lateral de urgencia (vermelho/amarelo)

**REMOVER da sidebar (mover para context panel):**
- Dot de sentimento no avatar (ja tem borda de urgencia)
- Check marks (✓✓) na preview
- Stage da jornada (badge)
- Info do chip (instance + telefone)
- Badge de wait time separado (ja tem borda amarela)

**AJUSTAR:**
- unread_count: manter mas so mostrar quando > 0 (ja faz isso)
- Especialidade: integrar na linha do nome (nao em linha separada)

### Implementacao

```tsx
// Novo card simplificado (~50px altura vs ~80px atual)
<button className={cn(
  "flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-muted/50",
  urgencyBorder,
  isSelected && "bg-muted"
)}>
  {/* Avatar */}
  <Avatar className="h-10 w-10 flex-shrink-0">
    <AvatarFallback className={cn(
      "text-xs font-medium",
      isHandoff ? "bg-state-handoff ..." : "bg-state-ai ..."
    )}>
      {initials}
    </AvatarFallback>
  </Avatar>

  {/* Content - 2 linhas apenas */}
  <div className="min-w-0 flex-1">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-1.5 min-w-0">
        <span className="truncate text-sm font-medium">{nome}</span>
        {especialidade && (
          <span className="truncate text-xs text-muted-foreground">· {especialidade}</span>
        )}
      </div>
      <span className="text-xs text-muted-foreground flex-shrink-0">{timeAgo}</span>
    </div>
    <div className="flex items-center justify-between mt-0.5">
      <span className="truncate text-xs text-muted-foreground">{lastMessage}</span>
      <div className="flex items-center gap-1 flex-shrink-0">
        {isHandoff ? <UserCheck className="h-3.5 w-3.5 text-state-handoff-foreground" />
                    : <Bot className="h-3.5 w-3.5 text-state-ai-foreground" />}
        {unreadCount > 0 && (
          <span className="...">{unreadCount}</span>
        )}
      </div>
    </div>
  </div>
</button>
```

### Testes Obrigatorios

**Unitarios:**
- [ ] Card renderiza nome + especialidade em 1 linha
- [ ] Card renderiza preview da mensagem
- [ ] Card mostra icone correto (AI vs Handoff)
- [ ] Borda de urgencia funciona (vermelho para handoff, amarelo para espera)
- [ ] unread_count aparece quando > 0
- [ ] Card selected tem background highlight

**Visual:**
- [ ] Altura do card visivelmente menor que antes
- [ ] Sem informacao cortada em telas de 380px de largura

### Definition of Done

- [ ] Max 6 sinais visuais por card
- [ ] Card mais compacto (~50-55px vs ~80px)
- [ ] Informacoes removidas estao acessiveis no context panel
- [ ] Testes passando

### Estimativa

2h

---

## Tarefa 4.2: Redesenhar tab "Atencao" como feed de triagem

### Objetivo

A tab "Atencao" deve funcionar como um feed de alertas acionaveis que mostra O QUE aconteceu, POR QUE precisa de atencao, e O QUE fazer — ao inves de uma lista generica de conversas.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `dashboard/app/(dashboard)/conversas/components/attention-feed.tsx` |
| Modificar | `dashboard/app/(dashboard)/conversas/page.tsx` |
| Modificar | `dashboard/app/api/conversas/route.ts` (adicionar campo `attention_reason`) |

### Design do card de triagem

```
┌──────────────────────────────────────┐
│ 🔴  Dr. Carlos · Cardiologia        │
│     Handoff pendente ha 23min        │  ← MOTIVO claro
│                                      │
│     "Preciso falar com alguem..."    │  ← Contexto (ultima msg)
│                                      │
│     [Assumir]  [Ver conversa]        │  ← Acoes diretas
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ 🟡  Dra. Ana · Pediatria            │
│     Sem resposta ha 1h15             │
│                                      │
│     "Quanto paga o plantao dia 20?"  │
│                                      │
│     [Ver conversa]                   │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ 🔴  Dr. Pedro · Clinico Geral       │
│     Sentimento muito negativo        │
│                                      │
│     "Ja disse que nao tenho..."      │
│                                      │
│     [Assumir]  [Ver conversa]        │
└──────────────────────────────────────┘
```

### Implementacao API

Adicionar campo `attention_reason` no enrichment da API:

```typescript
// route.ts: gerar motivo de atenção
function getAttentionReason(conv: EnrichedConversation): string | null {
  if (conv.controlled_by === 'human' || conv.has_handoff) {
    const handoffTime = conv.handoff_at
      ? formatDistanceToNow(new Date(conv.handoff_at), { locale: ptBR })
      : null
    return `Handoff pendente${handoffTime ? ` ha ${handoffTime}` : ''}`
  }

  if (conv.sentimento_score != null && conv.sentimento_score <= -2) {
    return 'Sentimento muito negativo'
  }

  if (conv.last_message_direction === 'entrada' && conv.last_message_at) {
    const waitMs = Date.now() - new Date(conv.last_message_at).getTime()
    if (waitMs > 60 * 60 * 1000) {
      const waitTime = formatDistanceToNow(new Date(conv.last_message_at), { locale: ptBR })
      return `Sem resposta ha ${waitTime}`
    }
  }

  return null
}
```

### Implementacao Component

```tsx
// attention-feed.tsx
export function AttentionFeed({ conversations, onSelect, onAssume }) {
  return (
    <div className="space-y-2 p-2">
      {conversations.map((conv) => (
        <div key={conv.id} className={cn(
          "rounded-lg border p-3 space-y-2",
          conv.has_handoff ? "border-destructive/30 bg-destructive/5" : "border-status-warning/30 bg-status-warning/5"
        )}>
          {/* Header: urgencia + nome */}
          <div className="flex items-center gap-2">
            <span className={cn(
              "h-2.5 w-2.5 rounded-full flex-shrink-0",
              conv.has_handoff ? "bg-destructive" : "bg-status-warning-solid"
            )} />
            <span className="font-medium text-sm">{conv.cliente_nome}</span>
            {conv.especialidade && (
              <span className="text-xs text-muted-foreground">· {conv.especialidade}</span>
            )}
          </div>

          {/* Motivo - a informacao mais importante */}
          <p className="text-xs font-medium text-muted-foreground">
            {conv.attention_reason}
          </p>

          {/* Contexto: ultima mensagem */}
          {conv.last_message && (
            <p className="text-xs text-muted-foreground italic line-clamp-2">
              "{conv.last_message}"
            </p>
          )}

          {/* Acoes */}
          <div className="flex gap-2">
            {(conv.controlled_by === 'ai') && (
              <Button size="sm" variant="outline" className="h-7 text-xs"
                onClick={() => onAssume(conv.id)}>
                Assumir
              </Button>
            )}
            <Button size="sm" variant="ghost" className="h-7 text-xs"
              onClick={() => onSelect(conv.id)}>
              Ver conversa
            </Button>
          </div>
        </div>
      ))}
    </div>
  )
}
```

### Integrar no page.tsx

```typescript
// Renderizar AttentionFeed quando tab === 'atencao', ChatSidebar nas demais
{activeTab === 'atencao' ? (
  <AttentionFeed
    conversations={data.data}
    onSelect={handleSelectConversation}
    onAssume={handleAssumeConversation}
  />
) : (
  <ChatSidebar ... />
)}
```

### Testes Obrigatorios

**Unitarios:**
- [ ] AttentionFeed renderiza card com motivo correto para handoff
- [ ] AttentionFeed renderiza card com motivo correto para sentimento negativo
- [ ] AttentionFeed renderiza card com motivo correto para espera longa
- [ ] Botao "Assumir" chama onAssume com ID correto
- [ ] Botao "Ver conversa" chama onSelect com ID correto
- [ ] API retorna attention_reason no response

**Integracao:**
- [ ] Tab "Atencao" mostra AttentionFeed (nao ChatSidebar)
- [ ] Tabs normais continuam mostrando ChatSidebar
- [ ] Clicar "Ver conversa" abre o chat panel

### Definition of Done

- [ ] Tab "Atencao" mostra feed de triagem com motivos claros
- [ ] Cada card tem motivo + contexto + acoes
- [ ] Acoes diretas (Assumir, Ver conversa) funcionais
- [ ] Demais tabs mantem ChatSidebar simplificado (Tarefa 4.1)
- [ ] Testes passando

### Estimativa

4h

---

## Tarefa 4.3: Melhorar header da sidebar com metricas de overview

### Objetivo

O header atual mostra apenas "X chips · Y conversas". Adicionar overview rapido do estado geral.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/(dashboard)/conversas/page.tsx` |

### Design

```
┌──────────────────────────────────────┐
│ 🔴 3 atencao  🤖 12 julia  ⏳ 5    │  ← Contadores visuais
│ [Chip 1 (32)] [Chip 2 (18)] [Todos] │  ← Chip pills (existente)
└──────────────────────────────────────┘
```

### Implementacao

Substituir o header atual por uma barra que mostra os contadores das tabs de forma compacta, eliminando a necessidade de clicar em cada tab para ver os numeros.

```tsx
<div className="flex items-center gap-3 border-b px-3 py-2">
  <div className="flex items-center gap-3 text-xs">
    {counts.atencao > 0 && (
      <button onClick={() => handleTabChange('atencao')}
        className="flex items-center gap-1 text-destructive font-medium">
        <AlertTriangle className="h-3.5 w-3.5" />
        {counts.atencao}
      </button>
    )}
    <span className="flex items-center gap-1 text-state-ai-muted">
      <Bot className="h-3.5 w-3.5" />
      {counts.julia_ativa}
    </span>
    <span className="flex items-center gap-1 text-muted-foreground">
      <Clock className="h-3.5 w-3.5" />
      {counts.aguardando}
    </span>
  </div>
  <div className="ml-auto">
    <NewConversationDialog onStart={handleNewConversation} />
  </div>
</div>
```

### Testes Obrigatorios

**Unitarios:**
- [ ] Header mostra contadores corretos
- [ ] Contador de atencao vermelho quando > 0
- [ ] Clicar no contador de atencao muda para tab atencao
- [ ] Header renderiza sem erro quando counts sao 0

### Definition of Done

- [ ] Overview visual dos contadores no header
- [ ] Atencao destacado em vermelho quando > 0
- [ ] Clicavel para navegar para a tab
- [ ] Testes passando

### Estimativa

1h
