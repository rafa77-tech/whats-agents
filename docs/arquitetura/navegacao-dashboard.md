# Arquitetura de Navegacao - Dashboard Julia

> Sprint 45 - Reestruturacao de Navegacao

## Visao Geral

O dashboard utiliza uma arquitetura de navegacao em multiplas camadas:

1. **Sidebar Desktop** - Navegacao principal (largura fixa 256px)
2. **Bottom Nav Mobile** - 5 itens principais + drawer
3. **Command Palette** - Acesso rapido via Cmd+K/Ctrl+K
4. **Sidebar de Modulo** - Navegacao especifica (ex: Chips)

## Estrutura de Rotas

### Rotas Principais

| Rota | Descricao | Layout |
|------|-----------|--------|
| /dashboard | Dashboard principal | Padrao |
| /conversas | Chat com medicos | Full-screen |
| /campanhas | Gestao de campanhas | Padrao |
| /vagas | Plantoes disponiveis | Padrao |
| /medicos | Banco de medicos | Padrao |
| /metricas | Analytics detalhado | Padrao |

### Modulo Chips (/chips/*)

| Rota | Descricao |
|------|-----------|
| /chips | Visao geral do pool |
| /chips/[id] | Detalhe de um chip |
| /chips/alertas | Alertas de chips |
| /chips/grupos | Grupos WhatsApp |
| /chips/warmup | Status de aquecimento |
| /chips/configuracoes | Configuracoes |

### Monitoramento

| Rota | Descricao |
|------|-----------|
| /monitor | Jobs em background |
| /health | Status do sistema |
| /integridade | Anomalias e KPIs |

### Qualidade

| Rota | Descricao |
|------|-----------|
| /qualidade | Avaliacoes de conversas |
| /auditoria | Logs de auditoria |

### Configuracao

| Rota | Descricao |
|------|-----------|
| /instrucoes | Diretrizes da Julia |
| /sistema | Configuracoes gerais |
| /ajuda | Ajuda e suporte |
| /hospitais/bloqueados | Hospitais bloqueados |

## Redirects

| De | Para | Motivo |
|----|------|--------|
| /grupos | /chips/grupos | Reorganizacao Sprint 45 |

## Layouts

### Layout Padrao

```
+------------------+------------------------+
|     Sidebar      |        Header          |
|    (w-64)        +------------------------+
|                  |                        |
|  - Dashboard     |      Content Area      |
|  - Operacoes     |      (px-6 py-6)       |
|  - Cadastros     |                        |
|  - WhatsApp      |                        |
|  - Monitor       |                        |
|  - Qualidade     |                        |
|                  |                        |
+------------------+------------------------+
```

- Sidebar desktop fixa (w-64 = 256px)
- Header com busca e notificacoes
- Bottom nav mobile (lg:hidden)
- Padding no conteudo

### Layout Full-Screen

Usado em: `/conversas`

```
+------------------+------------------------+
|     Sidebar      |        Header          |
|    (w-64)        +------------------------+
|                  |  +------------------+  |
|                  |  | Lista | Chat     |  |
|                  |  | (w-80)| Area     |  |
|                  |  |       |          |  |
|                  |  +------------------+  |
+------------------+------------------------+
```

- Sem padding
- Flex column
- Split pane (lista + chat)

### Layout Modulo Chips

```
+------------------+------------------+------------------------+
|     Sidebar      |  Chips Sidebar   |        Content         |
|    (w-64)        |    (w-64)        |                        |
|                  |                  |                        |
|  [Dashboard]     |  - Visao Geral   |     Chip Details       |
|  [Operacoes]     |  - Alertas       |     or List            |
|  [WhatsApp]      |  - Grupos        |                        |
|    > Chips       |  - Warmup        |                        |
|                  |  - Config        |                        |
+------------------+------------------+------------------------+
```

- Sidebar propria do modulo
- Navegacao interna
- Botao voltar para Dashboard

## Navegacao Mobile

### Bottom Nav (5 itens)

```
+--------+--------+--------+--------+--------+
|  Home  | Conver | Campan |  Chips |  Menu  |
| (dash) |  sas   |  has   |        | (drawer)
+--------+--------+--------+--------+--------+
```

1. Home (/dashboard)
2. Conversas (/conversas)
3. Campanhas (/campanhas)
4. Chips (/chips)
5. Menu (abre drawer)

### Drawer Mobile

- Todas as rotas agrupadas
- Mesma estrutura da sidebar desktop
- Abre do lado direito
- Fecha ao selecionar item

## Command Palette (Cmd+K)

Acesso rapido a todas as paginas e acoes.

### Atalhos

| Atalho | Acao |
|--------|------|
| Cmd+K / Ctrl+K | Abrir |
| Escape | Fechar |
| Enter | Selecionar |
| Setas | Navegar |

### Grupos

1. **Recentes** - Ultimas 5 paginas visitadas
2. **Acoes Rapidas** - Nova campanha, Atualizar pagina
3. **Paginas** - Todas as 17 paginas com busca

### Armazenamento

- Recentes salvos em `localStorage`
- Key: `jullia-recent-pages`
- Maximo: 5 itens

## Grupos de Navegacao (Sidebar)

| Grupo | Itens | Icone |
|-------|-------|-------|
| (sem label) | Dashboard | LayoutDashboard |
| Operacoes | Conversas, Campanhas, Vagas, Instrucoes | MessageSquare, Megaphone, Briefcase, FileText |
| Cadastros | Medicos, Hospitais | Stethoscope, Building2 |
| WhatsApp | Chips, Grupos | Smartphone, Users |
| Monitoramento | Monitor, Health, Integridade, Metricas | Activity, HeartPulse, ShieldCheck, BarChart3 |
| Qualidade | Avaliacoes, Auditoria | Star, ClipboardList |
| (footer) | Sistema, Ajuda | Settings, HelpCircle |

## Identidade Visual

### Cores

- **Primary**: #ff0080 (rosa Jull.ia)
- **Active state**: bg-primary/10 + text-primary
- **Hover state**: bg-muted + text-foreground
- **Gradient logo**: bg-jullia-gradient

### Indicadores

- Ponto colorido (w-1.5 h-1.5) para item ativo
- Badge vermelho para alertas criticos
- Icone menor (18px) para items de navegacao

## Componentes

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| Sidebar | `components/dashboard/sidebar.tsx` | Nav desktop |
| SidebarSection | `components/dashboard/sidebar-section.tsx` | Grupo de items |
| BottomNav | `components/dashboard/bottom-nav.tsx` | Nav mobile |
| MobileDrawer | `components/dashboard/mobile-drawer.tsx` | Menu completo mobile |
| CommandPalette | `components/command-palette/command-palette.tsx` | Busca global |
| ChipsModuleSidebar | `components/chips/chips-module-sidebar.tsx` | Nav modulo chips |

## Consideracoes de Acessibilidade

- Navegacao por teclado (Tab, Enter, Escape)
- Labels aria para leitores de tela
- Focus visible em todos os itens
- Contraste adequado (WCAG AA)
- Indicador visual de rota ativa

## Changelog

| Data | Mudanca |
|------|---------|
| Sprint 45 | Sidebar com grupos semanticos |
| Sprint 45 | Mobile drawer com navegacao completa |
| Sprint 45 | Command Palette (Cmd+K) |
| Sprint 45 | /grupos movido para /chips/grupos |
