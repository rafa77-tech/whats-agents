# ÉPICO 3: Particle Animations

## Contexto

Este épico adiciona vida ao grafo radial: partículas animadas representando mensagens viajando entre chips e Julia. É o que transforma um diagrama estático no efeito "ahá".

## Escopo

- **Incluído**: Sistema de partículas CSS-only, pool de partículas, diferenciação visual por direção, intensidade proporcional
- **Excluído**: WebSocket (usa polling), replay histórico, interação click

---

## Tarefa 3.1: Sistema de Partículas

### Objetivo

Criar o engine de partículas que gerencia a criação, animação e reciclagem de partículas no SVG. Cada partícula representa uma mensagem recente viajando entre um chip e Julia.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/components/dashboard/message-flow/particle-system.tsx` |
| Criar | `dashboard/components/dashboard/message-flow/use-particles.ts` |

### Implementação

#### Hook `useParticles`

```typescript
interface Particle {
  id: string
  chipId: string
  direction: MessageDirection
  /** Progresso da animação 0-1 */
  progress: number
  /** Timestamp de criação para TTL */
  createdAt: number
}

interface UseParticlesOptions {
  /** Mensagens recentes para criar partículas */
  messages: RecentMessage[]
  /** Máximo de partículas simultâneas */
  maxParticles?: number // default: 20
  /** Duração da animação em ms */
  animationDuration?: number // default: 1500
}

function useParticles(options: UseParticlesOptions): Particle[]
```

**Lógica:**
1. Quando `messages` muda, comparar com snapshot anterior
2. Novas mensagens (por id) → criar partícula
3. Partículas com TTL expirado → remover do pool
4. Se pool cheio (> maxParticles) → dropar as mais antigas
5. Usar `useRef` para tracking, `useState` para render

**Importante:** Não usar `setInterval` para animar. As partículas usam CSS animation puro. O hook apenas gerencia o ciclo de vida (criar/remover).

#### Componente `ParticleSystem`

```typescript
interface ParticleSystemProps {
  particles: Particle[]
  chipPositions: Map<string, { x: number; y: number }>
  centerX: number
  centerY: number
}
```

Renderiza SVG `<circle>` para cada partícula com CSS animation:

```xml
<circle
  cx={startX}
  cy={startY}
  r="3"
  className={direction === 'outbound' ? 'particle-outbound' : 'particle-inbound'}
  style={{
    '--start-x': `${startX}px`,
    '--start-y': `${startY}px`,
    '--end-x': `${endX}px`,
    '--end-y': `${endY}px`,
    animationDuration: `${duration}ms`,
  }}
/>
```

**Cores das partículas:**
- Outbound (Julia → chip): azul claro (`hsl(210, 80%, 60%)`)
- Inbound (chip → Julia): verde claro (`hsl(150, 70%, 50%)`)
- Erro: vermelho (`hsl(0, 70%, 55%)`) — se implementado

**CSS Animations:**
```css
@keyframes particle-travel {
  0% {
    cx: var(--start-x);
    cy: var(--start-y);
    opacity: 0;
    r: 2;
  }
  10% {
    opacity: 1;
    r: 3;
  }
  90% {
    opacity: 1;
    r: 3;
  }
  100% {
    cx: var(--end-x);
    cy: var(--end-y);
    opacity: 0;
    r: 2;
  }
}

/* Outbound: Julia (centro) → Chip */
.particle-outbound {
  fill: hsl(210, 80%, 60%);
  animation: particle-travel var(--duration, 1500ms) ease-in-out forwards;
}

/* Inbound: Chip → Julia (centro) */
.particle-inbound {
  fill: hsl(150, 70%, 50%);
  animation: particle-travel var(--duration, 1500ms) ease-in-out forwards;
}
```

**Nota sobre CSS variables em SVG:** `cx` e `cy` não são animáveis diretamente com CSS em todos os browsers. Alternativa robusta:

```css
@keyframes particle-travel {
  0% {
    transform: translate(0, 0);
    opacity: 0;
  }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% {
    transform: translate(var(--dx), var(--dy));
    opacity: 0;
  }
}
```

Onde `--dx` e `--dy` são calculados como a diferença entre posição do chip e Julia. Usar `transform` é GPU-accelerated e cross-browser.

### Performance

- Máximo 20 partículas = 20 elementos SVG animados
- CSS animations são GPU-accelerated (off main thread)
- `will-change: transform, opacity` nas partículas
- Partículas removidas do DOM após animação (evento `animationend`)
- Sem requestAnimationFrame, sem JavaScript animation loop

### Testes Obrigatórios

**Unitários (useParticles):**
- [ ] Cria partícula quando nova mensagem aparece
- [ ] Não duplica partícula para mesma mensagem (por id)
- [ ] Remove partícula após TTL expirar
- [ ] Respeita maxParticles (20)
- [ ] Dropa partículas mais antigas quando pool cheio
- [ ] Retorna array vazio quando sem mensagens
- [ ] Direction correta (outbound para tipo='saida', inbound para tipo='entrada')

**Unitários (ParticleSystem):**
- [ ] Renderiza círculos SVG para cada partícula
- [ ] Classe CSS correta por direção (particle-outbound / particle-inbound)
- [ ] CSS variables --dx, --dy calculados corretamente
- [ ] Não renderiza se particles vazio

**Visual:**
- [ ] Partículas viajam suavemente do ponto A ao B
- [ ] Fade in no início, fade out no final
- [ ] Cores distinguíveis (azul outbound, verde inbound)

### Definition of Done

- [ ] Hook useParticles gerencia ciclo de vida das partículas
- [ ] ParticleSystem renderiza animações CSS puras
- [ ] Performance: 60fps com 20 partículas simultâneas
- [ ] Sem memory leaks (partículas removidas do pool)
- [ ] Sem `any`
- [ ] `npm run typecheck` passa
- [ ] Testes passando

### Estimativa

5 pontos

---

## Tarefa 3.2: Intensidade Visual Proporcional

### Objetivo

A velocidade e densidade das partículas reflete o volume real de tráfego. Chips com mais atividade têm mais partículas e conexões mais visíveis.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Modificar | `dashboard/components/dashboard/message-flow/radial-graph.tsx` |
| Modificar | `dashboard/components/dashboard/message-flow/particle-system.tsx` |

### Implementação

**Opacidade das conexões baseada em atividade:**
```typescript
// Linha de conexão
const connectionOpacity = chip.isActive
  ? Math.min(0.2 + (chip.recentOutbound + chip.recentInbound) * 0.05, 0.6)
  : 0.1
```

**Tamanho do glow no chip baseado em volume:**
```typescript
// Raio do glow proporcional ao volume
const glowIntensity = Math.min(
  (chip.recentOutbound + chip.recentInbound) / 10,
  1.0
)
```

**Velocidade da partícula inversamente proporcional ao volume:**
- Alto tráfego → partículas mais rápidas (1000ms)
- Baixo tráfego → partículas mais lentas (2000ms)
- Dá a sensação de "urgência" quando há muito movimento

```typescript
const duration = Math.max(1000, 2000 - messagesPerMinute * 50)
```

### Testes Obrigatórios

**Unitários:**
- [ ] Opacidade da conexão aumenta com volume
- [ ] Opacidade da conexão nunca excede 0.6
- [ ] Opacidade mínima 0.1 para chips inativos
- [ ] Duration mínimo 1000ms mesmo com alto volume
- [ ] Glow intensity capped em 1.0

### Definition of Done

- [ ] Intensidade visual proporcional verificável visualmente
- [ ] Valores numéricos capped (sem overflow visual)
- [ ] Testes passando

### Estimativa

2 pontos

---

## Tarefa 3.3: CSS Animations (Tailwind + Global)

### Objetivo

Definir todos os keyframes e classes de animação necessários para o widget.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/components/dashboard/message-flow/message-flow.css` |

### Implementação

```css
/* === Message Flow Widget Animations === */

/* Respiração da Julia quando idle */
@keyframes mf-breathe {
  0%, 100% {
    transform: scale(1);
    opacity: 0.85;
  }
  50% {
    transform: scale(1.06);
    opacity: 1;
  }
}

.mf-breathe {
  animation: mf-breathe 3s ease-in-out infinite;
  transform-origin: center;
}

/* Pulse de chip ativo */
@keyframes mf-chip-pulse {
  0%, 100% {
    filter: drop-shadow(0 0 0px currentColor);
  }
  50% {
    filter: drop-shadow(0 0 6px currentColor);
  }
}

.mf-chip-pulse {
  animation: mf-chip-pulse 2s ease-in-out infinite;
}

/* Viagem da partícula (usa CSS custom properties) */
@keyframes mf-particle-travel {
  0% {
    transform: translate(0, 0);
    opacity: 0;
  }
  8% {
    opacity: 0.9;
  }
  85% {
    opacity: 0.9;
  }
  100% {
    transform: translate(var(--mf-dx), var(--mf-dy));
    opacity: 0;
  }
}

.mf-particle {
  will-change: transform, opacity;
  animation: mf-particle-travel var(--mf-duration, 1500ms) ease-in-out forwards;
  pointer-events: none;
}

.mf-particle-outbound {
  fill: hsl(210 80% 60%);
}

.mf-particle-inbound {
  fill: hsl(150 70% 50%);
}

/* Pulse do indicador mobile */
@keyframes mf-mobile-pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 hsl(var(--primary) / 0.4);
  }
  50% {
    transform: scale(1.1);
    box-shadow: 0 0 0 8px hsl(var(--primary) / 0);
  }
}

.mf-mobile-pulse {
  animation: mf-mobile-pulse var(--mf-pulse-speed, 2s) ease-in-out infinite;
}

/* Dark mode adjustments */
.dark .mf-particle-outbound {
  fill: hsl(210 90% 70%);
}

.dark .mf-particle-inbound {
  fill: hsl(150 80% 60%);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .mf-breathe,
  .mf-chip-pulse,
  .mf-particle,
  .mf-mobile-pulse {
    animation: none;
  }

  .mf-particle {
    /* Sem animação: mostrar partícula na posição final */
    transform: translate(var(--mf-dx), var(--mf-dy));
    opacity: 0.5;
  }
}
```

**Prefixo `mf-`** para evitar conflito com outras animações do dashboard.

### Testes Obrigatórios

**Unitários:**
- [ ] CSS importa sem erros
- [ ] Classes aplicadas corretamente nos componentes
- [ ] Prefixo `mf-` em todas as classes

**Acessibilidade:**
- [ ] `prefers-reduced-motion` desabilita animações
- [ ] Widget funcional sem animações (informação ainda visível)

### Definition of Done

- [ ] Todas as animações definidas com prefixo `mf-`
- [ ] Dark mode funciona
- [ ] `prefers-reduced-motion` respeitado
- [ ] CSS importado no componente container
- [ ] Sem conflito com animações existentes

### Estimativa

2 pontos
