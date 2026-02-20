# EPICO 05: UX Redesign — Chat Panel & Contexto

## Contexto

O chat panel nao ajuda o supervisor a entender rapidamente o que aconteceu na conversa. Ele precisa ler todas as mensagens para ter contexto. Alem disso, o context panel tem informacoes uteis mas esta desconectado do fluxo principal.

## Escopo

- **Incluido**: Resumo de conversa no topo do chat, melhorias no context panel, indicadores visuais de estado
- **Excluido**: Sidebar (Epic 04), backend queries (Epic 02), mobile (Epic 03)

---

## Tarefa 5.1: Resumo de conversa no topo do chat panel

### Objetivo

Quando o supervisor abre uma conversa, mostrar um resumo compacto antes das mensagens para que ele entenda o contexto sem precisar ler tudo.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `dashboard/app/(dashboard)/conversas/components/conversation-summary.tsx` |
| Modificar | `dashboard/app/(dashboard)/conversas/components/chat-panel.tsx` |
| Modificar | `dashboard/app/api/conversas/[id]/route.ts` (adicionar campo `summary`) |

### Design

```
┌──────────────────────────────────────────────┐
│ 📋 Resumo                          [Fechar] │
│                                              │
│ Dr. Carlos, cardiologista. Contactado em     │
│ 12/02 via campanha "Plantoes Fevereiro".     │
│ Mostrou interesse em noturno no Sao Luiz.    │
│ Pediu detalhes sobre valor. Comparando com   │
│ outra proposta.                              │
│                                              │
│ Sentimento: Neutro → Positivo               │
│ Mensagens: 8 medico / 12 Julia              │
│ Duracao: 3 dias                              │
└──────────────────────────────────────────────┘
```

### Implementacao — Backend

Gerar resumo baseado em dados estruturados (sem LLM por agora):

```typescript
// API route: /api/conversas/[id]/route.ts
// Adicionar campo 'summary' ao response

function generateSummary(conversation, context): string {
  const parts: string[] = []

  // Quem e o medico
  const doctor = context?.doctor
  if (doctor) {
    parts.push(
      `${doctor.nome}${doctor.especialidade ? ', ' + doctor.especialidade : ''}.`
    )
  }

  // Como comecou
  if (conversation.campanha_nome) {
    parts.push(`Contactado via campanha "${conversation.campanha_nome}".`)
  }

  // Stage atual
  if (doctor?.stage_jornada) {
    const stageLabels = {
      novo: 'Primeiro contato',
      interessado: 'Demonstrou interesse',
      prospectado: 'Em prospecção',
      negociando: 'Em negociação',
      ativo: 'Ativo na plataforma',
      inativo: 'Sem resposta recente',
      perdido: 'Conversa perdida',
    }
    parts.push(stageLabels[doctor.stage_jornada] || doctor.stage_jornada + '.')
  }

  // Memoria relevante (ultimas 2)
  if (context?.memory?.length > 0) {
    const recentMemory = context.memory.slice(0, 2)
    recentMemory.forEach(m => parts.push(m.content + '.'))
  }

  return parts.join(' ')
}
```

### Implementacao — Frontend

```tsx
// conversation-summary.tsx
interface Props {
  summary: string
  metrics: {
    total_msg_medico: number
    total_msg_julia: number
    duracao_dias: number
    sentimento_trend?: string
  }
  onDismiss?: () => void
}

export function ConversationSummary({ summary, metrics, onDismiss }: Props) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  return (
    <div className="border-b bg-muted/20 px-4 py-3">
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1.5">
          <p className="text-sm text-foreground leading-relaxed">{summary}</p>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{metrics.total_msg_medico} msgs medico / {metrics.total_msg_julia} Julia</span>
            {metrics.duracao_dias > 0 && (
              <span>{metrics.duracao_dias} dia{metrics.duracao_dias > 1 ? 's' : ''}</span>
            )}
          </div>
        </div>
        <Button variant="ghost" size="icon" className="h-6 w-6 flex-shrink-0"
          onClick={() => { setDismissed(true); onDismiss?.() }}>
          <X className="h-3 w-3" />
        </Button>
      </div>
    </div>
  )
}
```

### Integrar no chat-panel.tsx

Colocar entre o header e a area de mensagens:

```tsx
{/* Header */}
<div className="...">...</div>

{/* Summary */}
{conversation.summary && (
  <ConversationSummary
    summary={conversation.summary}
    metrics={conversation.metrics || { total_msg_medico: 0, total_msg_julia: 0, duracao_dias: 0 }}
  />
)}

{/* Messages */}
<div className="min-h-0 flex-1 overflow-y-auto">...</div>
```

### Testes Obrigatorios

**Unitarios:**
- [ ] ConversationSummary renderiza resumo corretamente
- [ ] ConversationSummary mostra metricas
- [ ] Botao dismiss esconde o resumo
- [ ] generateSummary gera texto com dados do medico
- [ ] generateSummary inclui stage e memoria
- [ ] generateSummary funciona com dados parciais (sem campanha, sem memoria)

**Integracao:**
- [ ] API retorna summary no response de conversa
- [ ] Chat panel exibe resumo no topo

### Definition of Done

- [ ] Resumo visivel ao abrir conversa
- [ ] Baseado em dados estruturados (sem custo LLM)
- [ ] Dismissable (supervisor pode fechar)
- [ ] Testes passando

### Estimativa

4h

---

## Tarefa 5.2: Indicador visual de estado da Julia no chat

### Objetivo

Quando Julia esta no controle, o footer mostra "Julia esta respondendo" mas nao da visibilidade sobre o que Julia esta fazendo. Melhorar com indicadores mais uteis.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/(dashboard)/conversas/components/chat-panel.tsx` |

### Design do footer quando Julia esta no controle

```
┌──────────────────────────────────────────────┐
│ 🤖 Julia no controle                        │
│                                              │
│ Confianca: 87%  ·  Ultima resposta: 2min    │
│ Sentimento medico: Positivo ↑                │
│                                              │
│ [Supervisionar]              [Assumir] 🟠    │
└──────────────────────────────────────────────┘
```

### Implementacao

```tsx
// Footer quando Julia controla - versao melhorada
<div className="border-t bg-state-ai px-4 py-3">
  <div className="flex items-center justify-between">
    <div className="space-y-1">
      <div className="flex items-center gap-2 text-sm font-medium text-state-ai-foreground">
        <Bot className="h-4 w-4" />
        {isPaused ? 'Julia pausada' : 'Julia no controle'}
      </div>
      <div className="flex items-center gap-3 text-xs text-state-ai-muted">
        {/* AI confidence da ultima resposta */}
        {lastOutgoingMessage?.ai_confidence != null && (
          <span className="flex items-center gap-1">
            Confianca: {Math.round(lastOutgoingMessage.ai_confidence * 100)}%
          </span>
        )}
        {/* Tempo desde ultima resposta da Julia */}
        {lastOutgoingMessage?.created_at && (
          <span>
            Ultima: {formatDistanceToNow(new Date(lastOutgoingMessage.created_at), { locale: ptBR })}
          </span>
        )}
      </div>
    </div>
    <div className="flex items-center gap-2">
      {onToggleContext && (
        <Button size="sm" variant="outline" onClick={onToggleContext}
          className="gap-1 border-state-ai-border text-state-ai-foreground">
          <Bot className="h-4 w-4" />
          <span className="hidden sm:inline">Supervisionar</span>
        </Button>
      )}
      <Button size="sm" onClick={() => handleControlChange('human')}
        disabled={changingControl}
        className="gap-2 bg-state-handoff-button text-white hover:bg-state-handoff-button-hover">
        {changingControl ? <Loader2 className="h-4 w-4 animate-spin" /> : <Hand className="h-4 w-4" />}
        Assumir
      </Button>
    </div>
  </div>
</div>
```

### Testes Obrigatorios

**Unitarios:**
- [ ] Footer mostra "Julia no controle" quando controlled_by === 'ai'
- [ ] Footer mostra "Julia pausada" quando isPaused
- [ ] Confianca da ultima resposta exibida quando disponivel
- [ ] Tempo desde ultima resposta exibido

### Definition of Done

- [ ] Footer com informacoes uteis sobre estado da Julia
- [ ] Supervisor sabe a confianca e tempo sem ler mensagens
- [ ] Testes passando

### Estimativa

1.5h

---

## Tarefa 5.3: Melhorar DoctorContextPanel com informacoes priorizadas

### Objetivo

O context panel abre tudo colapsado por padrao (exceto Perfil e Memoria). Reorganizar para priorizar informacoes mais uteis para supervisao.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/(dashboard)/conversas/components/doctor-context-panel.tsx` |

### Mudancas

1. **Perfil** — defaultOpen, mas mais compacto (uma linha por info)
2. **Memoria Julia** — defaultOpen (mais util para supervisao)
3. **Resumo de conversa** — NOVO, defaultOpen (metricas + sentimento)
4. **Handoffs** — defaultOpen quando tem handoffs ativos
5. **Notas** — mover para cima (supervisores usam muito)
6. **Eventos** — mover para baixo (menos urgente)

### Ordem nova das secoes

```
1. Perfil (sempre aberto, compacto)
2. Notas do supervisor (sempre aberto — supervisores usam muito)
3. Memoria Julia (sempre aberto)
4. Metricas da conversa (aberto)
5. Handoffs (aberto se tem pendentes)
6. Eventos (colapsado)
```

### Testes Obrigatorios

**Unitarios:**
- [ ] Secoes na ordem correta
- [ ] Notas aparecem antes de Metricas
- [ ] Handoffs abre automaticamente quando tem pendentes
- [ ] Eventos começa colapsado

### Definition of Done

- [ ] Informacoes mais uteis no topo
- [ ] Notas priorizadas (supervisores usam constantemente)
- [ ] Handoffs auto-abre quando relevante
- [ ] Testes passando

### Estimativa

1.5h
