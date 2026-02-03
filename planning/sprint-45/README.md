# Sprint 45 - Arquitetura da Informacao & Navegacao

**Status:** ✅ Completa

## Objetivo
Reorganizar a arquitetura da informacao do dashboard Julia para **reduzir carga cognitiva**, **melhorar descobribilidade** e **garantir paridade mobile/desktop**.

## Contexto

### Problema Identificado

Analise da arquitetura atual revelou problemas criticos:

| Problema | Impacto | Severidade |
|----------|---------|------------|
| 17 itens na sidebar sem agrupamento | Fadiga visual, tempo de busca alto | Alta |
| Mobile com apenas 5 itens (vs 17 desktop) | Funcionalidades criticas inacessiveis | Critica |
| Nomenclatura inconsistente | Confusao do usuario | Media |
| Rotas orfas (/hospitais/bloqueados, /grupos) | Arquitetura fragil | Media |
| Falta de busca global | Navegacao ineficiente para power users | Media |

### Estado Atual vs Desejado

**Sidebar Desktop (Atual):**
```
17 itens em lista flat, sem separadores visuais
Usuario precisa escanear todos os itens para encontrar o que quer
```

**Sidebar Desktop (Desejado):**
```
6 grupos semanticos (3-4 itens cada)
Usuario escaneia grupos primeiro, depois itens dentro do grupo
Respeita Lei de Miller (7 +/- 2 itens)
```

**Bottom Nav Mobile (Atual):**
```
5 itens: Dashboard, Campanhas, Chips, Instrucoes, Sistema
FALTANDO: Conversas (critico!), Medicos, Vagas, Monitor, Health...
```

**Bottom Nav Mobile (Desejado):**
```
5 itens: Home, Conversas, Campanhas, Chips, Menu
Menu abre drawer com navegacao completa agrupada
```

### Personas e Fluxos Afetados

| Persona | Fluxo Principal | Problema Atual |
|---------|-----------------|----------------|
| Operador de Campanhas | Dashboard > Medicos > Campanhas > Conversas | Medicos longe de Campanhas |
| Supervisor de Qualidade | Dashboard > Qualidade > Conversas > Auditoria | Qualidade e Auditoria separados |
| Admin Tecnico | Health > Monitor > Chips > Integridade > Sistema | 5 paginas para troubleshooting |

## Escopo

### Fase 1 - Reorganizacao da Sidebar (E01)
- Adicionar labels de secao
- Agrupar itens por dominio
- Separadores visuais

### Fase 2 - Navegacao Mobile (E02)
- Expandir bottom nav com item "Menu"
- Criar drawer com navegacao completa
- Adicionar Conversas no bottom nav

### Fase 3 - Command Palette (E03)
- Implementar busca global (Cmd+K)
- Recentes, acoes rapidas, navegacao

### Fase 4 - Reestruturacao de Rotas (E04)
- Mover /grupos para /chips/grupos
- Criar /cadastros com medicos, vagas, hospitais
- Padronizar nomenclatura

### Fase 5 - Testes e Documentacao (E05)
- Testes de navegacao
- Documentar nova arquitetura

## Fora de Escopo
- Redesign visual completo
- Mudancas no backend
- Novas funcionalidades de negocio

## Metricas de Sucesso
- Tempo medio para encontrar pagina: < 3 segundos
- Paridade mobile/desktop: 100% das rotas acessiveis
- Satisfacao do usuario (qualitativo)
- Zero regressoes em funcionalidades existentes

## Epicos

| Epic | Descricao | Stories | Esforco |
|------|-----------|---------|---------|
| E01 | Reorganizacao da Sidebar | 4 | Baixo |
| E02 | Navegacao Mobile | 4 | Medio |
| E03 | Command Palette | 5 | Medio |
| E04 | Reestruturacao de Rotas | 4 | Medio |
| E05 | Testes e Documentacao | 3 | Baixo |
| **Total** | | **20** | |

## Ordem de Execucao Recomendada

```
Fase 1 - Quick Wins (1-2 dias)
├── S45.E1.1 - Adicionar labels de secao na sidebar
├── S45.E1.2 - Reordenar itens por grupo
└── S45.E2.1 - Adicionar Conversas no bottom nav

Fase 2 - Mobile Navigation (2-3 dias)
├── S45.E2.2 - Criar drawer de navegacao mobile
├── S45.E2.3 - Substituir ultimo item por Menu
└── S45.E2.4 - Agrupar itens no drawer

Fase 3 - Command Palette (3-5 dias)
├── S45.E3.1 - Estrutura base do command palette
├── S45.E3.2 - Busca de paginas
├── S45.E3.3 - Recentes e acoes rapidas
├── S45.E3.4 - Atalho de teclado (Cmd+K)
└── S45.E3.5 - Integracao no header

Fase 4 - Reestruturacao (2-3 dias)
├── S45.E4.1 - Mover /grupos para /chips/grupos
├── S45.E4.2 - Criar agrupamento /cadastros
├── S45.E4.3 - Redirects para URLs antigas
└── S45.E4.4 - Padronizar nomenclatura

Fase 5 - Finalizacao (1-2 dias)
├── S45.E5.1 - Testes de navegacao E2E
├── S45.E5.2 - Documentar nova arquitetura
└── S45.E5.3 - Atualizar CLAUDE.md
```

## Resumo de Entregas

### Componentes Novos

| Componente | Descricao |
|------------|-----------|
| `SidebarSection` | Label de secao com separador |
| `MobileDrawer` | Drawer de navegacao mobile |
| `CommandPalette` | Busca global (Cmd+K) |
| `CommandPaletteProvider` | Context para estado global |

### Arquivos Modificados

| Arquivo | Mudanca |
|---------|---------|
| `sidebar.tsx` | Adicionar secoes e reordenar |
| `bottom-nav.tsx` | Trocar Instrucoes por Menu |
| `header.tsx` | Adicionar trigger do command palette |
| `layout.tsx` | Adicionar providers |

### Rotas Movidas

| De | Para | Redirect |
|----|------|----------|
| `/grupos` | `/chips/grupos` | 301 |
| `/hospitais/bloqueados` | `/cadastros/hospitais` | 301 |

## Nova Estrutura de Navegacao

### Sidebar Desktop

```
┌──────────────────────────────────────┐
│ [J] Julia                    [⌘K]   │
├──────────────────────────────────────┤
│                                      │
│ Dashboard                            │
│                                      │
│ OPERACOES ─────────────────────      │
│   Conversas                          │
│   Campanhas                          │
│   Vagas                              │
│                                      │
│ CADASTROS ─────────────────────      │
│   Medicos                            │
│   Hospitais                          │
│                                      │
│ WHATSAPP ──────────────────────      │
│   Chips              →               │
│   Grupos                             │
│                                      │
│ MONITORAMENTO ─────────────────      │
│   Monitor                            │
│   Health                             │
│   Integridade                        │
│   Metricas                           │
│                                      │
│ QUALIDADE ─────────────────────      │
│   Avaliacoes                         │
│   Auditoria                          │
│                                      │
│ ═══════════════════════════════      │
│   Instrucoes                         │
│   Sistema                            │
│   Ajuda                              │
│                                      │
└──────────────────────────────────────┘
```

### Bottom Nav Mobile

```
┌────────┬────────┬────────┬────────┬────────┐
│  Home  │ Conver │ Campan │ Chips  │  Menu  │
│   🏠   │   💬   │   📢   │   📱   │   ☰    │
└────────┴────────┴────────┴────────┴────────┘
```

### Command Palette (Cmd+K)

```
┌─────────────────────────────────────────────────────────────────────┐
│  🔍 Buscar pagina ou acao...                                esc    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  RECENTES                                                           │
│    💬  Conversas                                                    │
│    📢  Campanhas > Nova Campanha                                    │
│    👨‍⚕️  Medicos > Dr. Carlos Silva                                  │
│                                                                      │
│  ACOES RAPIDAS                                                      │
│    ➕  Nova Campanha                                                │
│    ➕  Novo Medico                                                  │
│    🔄  Atualizar Dashboard                                          │
│                                                                      │
│  PAGINAS                                                            │
│    📊  Dashboard                                                    │
│    💬  Conversas                                                    │
│    📢  Campanhas                                                    │
│    ...                                                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Usuarios desorientados com mudanca | Media | Medio | Comunicar mudancas, manter URLs antigas |
| Regressao em navegacao existente | Baixa | Alto | Testes E2E antes de deploy |
| Performance do command palette | Baixa | Baixo | Lazy loading, debounce |

## Criterios de Aceite da Sprint

### Frontend
- [ ] Sidebar com 6 secoes agrupadas
- [ ] Bottom nav com Conversas e Menu
- [ ] Drawer mobile com navegacao completa
- [ ] Command palette funcional (Cmd+K)
- [ ] Todas as rotas acessiveis em mobile
- [ ] Zero erros de TypeScript
- [ ] Testes de navegacao passando

### UX
- [ ] Navegacao intuitiva (teste com usuario)
- [ ] Paridade mobile/desktop
- [ ] Atalhos de teclado funcionais
- [ ] Transicoes suaves

### Documentacao
- [ ] CLAUDE.md atualizado
- [ ] Diagrama de navegacao atualizado
- [ ] README de cada epic

---

## Stories

Ver arquivos `epic-*.md` para detalhamento completo.
