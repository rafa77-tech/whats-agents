# Sprint 56 - Message Flow Visualization

**Início:** A definir
**Duração estimada:** 1 semana
**Dependências:** Nenhuma (dashboard já funcional)
**Status:** 📋 Planejado

---

## Progresso

| Epic | Status | Descrição |
|------|--------|-----------|
| Epic 1: Types & API Route | 📋 Pendente | Tipos TypeScript + endpoint de dados |
| Epic 2: Radial Graph (SVG) | 📋 Pendente | Layout hub-and-spoke com Julia + chips |
| Epic 3: Particle Animations | 📋 Pendente | Mensagens animadas fluindo entre nós |
| Epic 4: Integração na Dashboard | 📋 Pendente | Widget no page.tsx + responsividade |

---

## Objetivo

Criar um widget visual em tempo real no dashboard home que mostra mensagens fluindo entre cada chip WhatsApp e a Julia. Layout radial (hub-and-spoke) com animações de partículas representando o tráfego de mensagens.

### Por que agora?

O dashboard tem ~12 widgets, todos baseados em números, tabelas e gráficos estáticos. Falta um elemento visual que transmita **"o sistema está vivo"** de relance. Este widget:

- **Operacional:** Mostra atividade/inatividade dos chips instantaneamente
- **Showcase:** Efeito "ahá" para stakeholders e novos operadores
- **Complementar:** Não substitui nenhum widget, adiciona uma dimensão visual nova

### Decisões Técnicas

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Renderização | SVG inline + CSS animations | Zero dependências novas, performático, acessível |
| Layout | Radial (hub-and-spoke) | Julia no centro, chips ao redor — metáfora clara |
| Dados | Polling 5s | Consistente com padrão existente (alertas usam 15s) |
| Posição na page | Entre Operational Status e Chip Pool | Ponte visual entre status abstrato e detalhes de chips |
| Animação de partículas | CSS @keyframes + offset-path | Nativo do browser, GPU-accelerated |
| Mobile | Versão compacta "pulso" | Grafo radial não funciona em telas < 768px |

### Escopo

**Incluído:**
- Widget card full-width com grafo radial SVG
- Julia (nó central) + até 15 chips (nós ao redor)
- Partículas animadas representando mensagens (inbound/outbound)
- Status visual dos chips (cor por saúde)
- Animação idle ("respiração") quando sem tráfego
- Polling 5s para dados ao vivo
- Responsivo: desktop (grafo completo), tablet (simplificado), mobile (pulso compacto)
- API route com dados de chips + mensagens recentes
- Legenda compacta

**Excluído:**
- Replay histórico
- Click em chip para navegar (pode ser sprint futura)
- WebSocket/SSE (polling é suficiente para 5s)
- Novas dependências npm (sem D3, sem framer-motion)
- Dados de conteúdo das mensagens (apenas contagem/direção)

---

## Critérios de Sucesso

- [ ] Widget renderiza corretamente com dados reais do Supabase
- [ ] Partículas animam fluentemente em 60fps (sem jank)
- [ ] Polling 5s atualiza sem flicker ou re-render total
- [ ] Responsivo funcional em mobile, tablet e desktop
- [ ] Chip sem atividade mostra estado idle (respiração)
- [ ] Chip com atividade pulsa proporcionalmente ao volume
- [ ] `npm run validate` passa (typecheck + lint + format)
- [ ] `npm run build` passa sem warnings

---

## Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Performance SVG com muitos nós | Médio | Limitar a 15 chips; usar `will-change` e `transform` para GPU |
| Polling 5s sobrecarrega API | Baixo | Query leve (COUNT + status, sem payload pesado) |
| CSS animations inconsistentes cross-browser | Médio | Usar apenas propriedades GPU-accelerated (transform, opacity) |
| Widget muito grande empurrando conteúdo | Baixo | Altura fixa (300px desktop, 200px tablet, 80px mobile) |
| Muitas partículas simultâneas | Médio | Pool de partículas com máximo 20 simultâneas; reciclar elementos |

---

## Arquitetura Visual

```
┌─────────────────────────────────────────────────┐
│  Message Flow                          ● 12/min │
│                                                  │
│              chip3     chip4                     │
│          chip2    ·bg pulse·   chip5             │
│                                                  │
│        chip1    ●═══ JULIA ═══●   chip6         │
│                  ←── particle ──→                 │
│          chip8    ·         ·    chip7           │
│              chip9     chip10                    │
│                                                  │
│  ● ativo  ● aquecendo  ● degradado    idle: ~   │
└─────────────────────────────────────────────────┘

Mobile (compacto):
┌─────────────────────────┐
│  ● Julia Ativa  12/min  │
│  ████████░░ 8 chips     │
│  ↑5 ↓7 mensagens/min   │
└─────────────────────────┘
```

---

## Stack

| Tecnologia | Uso | Já instalado? |
|------------|-----|---------------|
| SVG inline | Grafo radial | Nativo (JSX) |
| CSS @keyframes | Animação de partículas | Nativo (Tailwind) |
| CSS offset-path | Partículas seguindo caminho | Nativo (CSS) |
| Tailwind CSS | Responsividade + tema | ✅ Sim |
| Recharts | Não usado neste widget | ✅ (não necessário) |
| Lucide React | Ícones na legenda | ✅ Sim |
| Radix Card | Container do widget | ✅ Sim |
