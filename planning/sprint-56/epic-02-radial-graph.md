# ÉPICO 2: Radial Graph (SVG)

## Contexto

O coração visual do widget: um grafo SVG com Julia no centro e chips posicionados ao redor em layout radial. Este épico cria a estrutura estática (posicionamento, nós, conexões) sem as animações de partículas (Epic 3).

## Escopo

- **Incluído**: SVG radial layout, nó central Julia, nós de chips com status visual, linhas de conexão, legenda, estado idle/empty
- **Excluído**: Animação de partículas (Epic 3), polling/integração na page (Epic 4)

---

## Tarefa 2.1: Componente `MessageFlowWidget` (container)

### Objetivo

Card container que encapsula o widget completo. Gerencia o layout responsivo e delega ao grafo SVG (desktop/tablet) ou ao pulso compacto (mobile).

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/components/dashboard/message-flow/message-flow-widget.tsx` |

### Implementação

```typescript
'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { MessageFlowData } from '@/types/dashboard'
import { RadialGraph } from './radial-graph'
import { MobilePulse } from './mobile-pulse'
import { Activity } from 'lucide-react'

interface MessageFlowWidgetProps {
  data: MessageFlowData | null
  isLoading: boolean
}

export function MessageFlowWidget({ data, isLoading }: MessageFlowWidgetProps) {
  // Loading state: skeleton com pulse
  // Empty state: mensagem "Nenhum chip ativo"
  // Desktop/Tablet (>= 768px): <RadialGraph />
  // Mobile (< 768px): <MobilePulse />
  // Header: "Message Flow" + badge "{messagesPerMinute}/min"
}
```

**Responsividade:**
- Usar `useMediaQuery` ou classes Tailwind `hidden md:block` / `block md:hidden`
- Desktop: Card com altura 320px, RadialGraph dentro
- Tablet: Card com altura 280px, RadialGraph com menos labels
- Mobile: Card com altura 80px, MobilePulse compacto

### Testes Obrigatórios

**Unitários:**
- [ ] Renderiza loading state (skeleton)
- [ ] Renderiza empty state quando `data.chips` vazio
- [ ] Renderiza RadialGraph em viewport desktop
- [ ] Renderiza MobilePulse em viewport mobile
- [ ] Mostra messagesPerMinute no header
- [ ] Não quebra com data=null

### Definition of Done

- [ ] Componente renderiza nos 3 breakpoints
- [ ] Loading e empty states implementados
- [ ] Sem `any` nos tipos
- [ ] `npm run typecheck` passa

### Estimativa

2 pontos

---

## Tarefa 2.2: Componente `RadialGraph` (SVG core)

### Objetivo

SVG que posiciona Julia no centro e chips em círculo ao redor. Desenha linhas de conexão e mostra status visual de cada chip.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/components/dashboard/message-flow/radial-graph.tsx` |

### Implementação

**Geometria:**
```
SVG viewBox: "0 0 800 320"
Centro Julia: (400, 160)
Raio do círculo de chips: 120px
Nó Julia: círculo r=28
Nó Chip: círculo r=16
Conexões: linhas retas do centro ao chip
```

**Posicionamento dos chips:**
```typescript
// Distribuir N chips uniformemente em semicírculo (ou círculo completo)
function getChipPosition(index: number, total: number, cx: number, cy: number, radius: number) {
  const angle = (index / total) * 2 * Math.PI - Math.PI / 2 // começa no topo
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  }
}
```

**Cores por status:**
```typescript
const statusColors: Record<ChipNodeStatus, string> = {
  active: 'var(--color-success)',      // verde
  warming: 'var(--color-warning)',     // amarelo
  degraded: 'var(--color-destructive)', // vermelho
  paused: 'var(--color-muted)',        // cinza
  offline: 'var(--color-muted)',       // cinza escuro
}
```

**Nó Julia (centro):**
- Círculo com gradiente radial (cor primária do tema)
- Label "Julia" abaixo
- Animação de respiração (scale 1.0 → 1.05 → 1.0 em 3s, CSS)

**Nó Chip:**
- Círculo com cor baseada no status
- Borda com opacidade baseada no trustScore (mais opaco = mais trust)
- Label com instance_name truncado (max 8 chars)
- Glow sutil quando isActive=true

**Linhas de conexão:**
- SVG `<line>` do centro (Julia) a cada chip
- Opacidade baseada em atividade (0.15 quando idle, 0.4 quando ativo)
- Servem como "trilho" para as partículas (Epic 3)

**Animação idle (respiração):**
```css
@keyframes breathe {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.05); opacity: 1; }
}
/* Aplicar no nó Julia quando messagesPerMinute === 0 */
```

**Animação de chip ativo (pulse):**
```css
@keyframes chip-pulse {
  0%, 100% { filter: drop-shadow(0 0 0px transparent); }
  50% { filter: drop-shadow(0 0 6px currentColor); }
}
/* Aplicar no nó do chip quando isActive=true */
```

### SVG Structure

```xml
<svg viewBox="0 0 800 320" className="w-full h-full">
  {/* Definições: gradientes, filtros */}
  <defs>
    <radialGradient id="julia-gradient">...</radialGradient>
  </defs>

  {/* Camada 1: Linhas de conexão */}
  <g className="connections">
    {chips.map(chip => <line ... />)}
  </g>

  {/* Camada 2: Nós dos chips */}
  <g className="chip-nodes">
    {chips.map(chip => <ChipNodeSVG ... />)}
  </g>

  {/* Camada 3: Nó central Julia */}
  <g className="julia-node">
    <circle ... />
    <text>Julia</text>
  </g>

  {/* Camada 4: Partículas (Epic 3 — placeholder) */}
  <g className="particles">
    {/* Epic 3 adiciona aqui */}
  </g>
</svg>
```

### Testes Obrigatórios

**Unitários:**
- [ ] Renderiza SVG com viewBox correto
- [ ] Posiciona nó Julia no centro
- [ ] Posiciona N chips em círculo (testar com 1, 5, 10, 15 chips)
- [ ] Cores corretas por status (active=verde, warming=amarelo, etc.)
- [ ] Linhas de conexão entre Julia e cada chip
- [ ] Labels de chip truncados em 8 caracteres
- [ ] Classe de animação `breathe` quando idle (messagesPerMinute=0)
- [ ] Classe de animação `chip-pulse` quando chip.isActive=true
- [ ] Não quebra com 0 chips
- [ ] Não quebra com 15 chips (máximo)

**Visual:**
- [ ] Grafo legível em 800x320
- [ ] Chips não se sobrepõem
- [ ] Labels não cortados

### Definition of Done

- [ ] SVG renderiza com layout radial correto
- [ ] Status visual por cor funciona
- [ ] Animação breathe (Julia) e pulse (chips ativos) funcionam
- [ ] Sem `any` nos tipos
- [ ] Acessível (role="img", aria-label no SVG)
- [ ] `npm run typecheck` passa
- [ ] Testes passando

### Estimativa

5 pontos

---

## Tarefa 2.3: Componente `MobilePulse` (versão compacta)

### Objetivo

Versão mobile do widget: card compacto que mostra atividade da Julia como um pulso visual, sem o grafo radial.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/components/dashboard/message-flow/mobile-pulse.tsx` |

### Implementação

```
┌─────────────────────────────────┐
│ ● Julia Ativa     12 msg/min    │
│ ████████░░░ 8/10 chips ativos   │
│ ↑ 5 enviadas  ↓ 7 recebidas    │
└─────────────────────────────────┘
```

**Componentes:**
- Indicador pulsante (bolinha que pulsa com atividade)
- Status text ("Ativa" / "Idle" / "Offline")
- Messages/min
- Barra de progresso: chips ativos / total chips
- Contadores inbound/outbound

**Animação:**
- Bolinha pulsa quando messagesPerMinute > 0
- Intensidade proporcional ao volume (mais rápido = mais msgs)

### Testes Obrigatórios

**Unitários:**
- [ ] Renderiza com dados válidos
- [ ] Mostra "Idle" quando messagesPerMinute = 0
- [ ] Mostra "Ativa" quando messagesPerMinute > 0
- [ ] Barra de progresso proporcional (chips ativos / total)
- [ ] Contadores inbound/outbound corretos

### Definition of Done

- [ ] Renderiza corretamente em viewport < 768px
- [ ] Pulso visual funciona
- [ ] Sem `any`
- [ ] Testes passando

### Estimativa

2 pontos

---

## Tarefa 2.4: Componente `FlowLegend` (legenda)

### Objetivo

Legenda compacta abaixo do grafo mostrando o significado das cores e símbolos.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/components/dashboard/message-flow/flow-legend.tsx` |

### Implementação

```
● ativo  ● aquecendo  ● degradado  ● pausado  │  → enviada  ← recebida
```

- Horizontal, inline, texto pequeno (text-xs)
- Escondida em mobile (a MobilePulse tem sua própria representação)
- Cores matching com statusColors do RadialGraph

### Testes Obrigatórios

**Unitários:**
- [ ] Renderiza todos os status com cores corretas
- [ ] Renderiza indicadores de direção

### Definition of Done

- [ ] Legenda compacta e legível
- [ ] Hidden em mobile (`hidden md:flex`)
- [ ] Testes passando

### Estimativa

1 ponto
