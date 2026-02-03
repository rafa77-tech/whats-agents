# Epic 04 - Reestruturacao de Rotas

## Objetivo
Reorganizar rotas orfas e padronizar nomenclatura para uma arquitetura mais coesa.

## Contexto

### Problemas Identificados

| Problema | Rota Atual | Impacto |
|----------|------------|---------|
| Rota orfa | `/hospitais/bloqueados` | Unica subrota de /hospitais (nao existe /hospitais) |
| Fora do modulo | `/grupos` | Deveria estar em /chips/grupos |
| Nomenclatura | Inconsistencias em PT-BR vs EN | Confusao |

### Decisoes de Arquitetura

1. **Mover /grupos para /chips/grupos** - Grupos WhatsApp sao parte do modulo de chips
2. **Manter /hospitais/bloqueados** - Criar redirect mas manter funcionalidade
3. **Padronizar nomenclatura** - URLs sem acento, labels em PT-BR

## Stories

---

### S45.E4.1 - Mover /grupos para /chips/grupos

**Objetivo:** Transferir a pagina de grupos para dentro do modulo de chips.

**Arquivos Envolvidos:**

| Acao | De | Para |
|------|-----|------|
| Mover | `app/(dashboard)/grupos/page.tsx` | `app/(dashboard)/chips/grupos/page.tsx` |
| Redirect | - | `app/(dashboard)/grupos/page.tsx` (redirect) |
| Update | `chips-module-sidebar.tsx` | Adicionar item Grupos |

**Passo 1: Criar nova rota**

```bash
mkdir -p dashboard/app/\(dashboard\)/chips/grupos
```

**Passo 2: Mover conteudo**

Copiar conteudo de `grupos/page.tsx` para `chips/grupos/page.tsx`.

**Passo 3: Criar redirect**

```tsx
// app/(dashboard)/grupos/page.tsx
import { redirect } from 'next/navigation'

export default function GruposRedirectPage() {
  redirect('/chips/grupos')
}
```

**Passo 4: Atualizar sidebar do modulo chips**

```tsx
// chips-module-sidebar.tsx
const navItems: NavItem[] = [
  { title: 'Visao Geral', href: '/chips', icon: LayoutDashboard, exact: true },
  { title: 'Alertas', href: '/chips/alertas', icon: AlertTriangle, showBadge: true },
  { title: 'Grupos', href: '/chips/grupos', icon: Users },  // NOVO
  { title: 'Warmup', href: '/chips/warmup', icon: Calendar },
  { title: 'Configuracoes', href: '/chips/configuracoes', icon: Settings },
]
```

**Passo 5: Atualizar navegacao principal**

Remover `/grupos` da sidebar principal e bottom nav (ja sera acessivel via /chips).

**Tarefas:**
1. Criar diretorio `chips/grupos`
2. Mover pagina para nova localizacao
3. Criar redirect na rota antiga
4. Atualizar `chips-module-sidebar.tsx`
5. Remover de `sidebar.tsx` (navegacao principal)
6. Testar navegacao

**DoD:**
- [x] Pagina funciona em /chips/grupos
- [x] /grupos redireciona para /chips/grupos
- [x] Item aparece na sidebar do modulo chips
- [x] Removido da sidebar principal (grupos agora em /chips/grupos)
- [x] Sem links quebrados

---

### S45.E4.2 - Atualizar Referencias de Navegacao

**Objetivo:** Garantir que todas as referencias a /grupos apontem para /chips/grupos.

**Arquivos para Verificar:**

```bash
# Buscar referencias a /grupos
grep -r "'/grupos'" dashboard/
grep -r '"/grupos"' dashboard/
```

**Locais Comuns:**
- `sidebar.tsx` - Remover item
- `bottom-nav.tsx` - Verificar se existe
- `mobile-drawer.tsx` - Atualizar href
- `command-palette.tsx` - Atualizar href
- Qualquer link hardcoded em componentes

**Tarefas:**
1. Buscar todas as referencias a `/grupos`
2. Atualizar para `/chips/grupos` onde necessario
3. Remover de navegacao principal onde apropriado
4. Manter em command palette com novo href
5. Testar todos os links

**DoD:**
- [x] Zero referencias a `/grupos` (exceto redirect)
- [x] Command palette atualizado
- [x] Drawer mobile atualizado
- [x] Todos os links funcionam

---

### S45.E4.3 - Padronizar Nomenclatura

**Objetivo:** Garantir consistencia em toda a interface.

**Padroes a Aplicar:**

| Elemento | Padrao | Exemplo |
|----------|--------|---------|
| URLs | Sem acento, lowercase | `/metricas`, `/integridade` |
| Labels | PT-BR com acento | "Métricas", "Integridade" |
| Icones | Lucide icons consistentes | Usar mesmo icone para mesma funcao |

**Nomenclatura Atual vs Proposta:**

| Atual | Proposto | Motivo |
|-------|----------|--------|
| "Pool de Chips" | "Chips" | Mais curto, consistente |
| "Health Center" | "Health" ou "Saude" | Consistencia linguistica |
| "Hospitais Bloqueados" | "Hospitais" | Simplificar |
| "Avaliacoes" (em /qualidade) | Manter | Ja esta correto |

**Decisao:** Manter URLs em PT-BR sem acento (atual) e labels curtos.

**Tarefas:**
1. Renomear "Pool de Chips" para "Chips" na sidebar
2. Renomear "Health Center" para "Health" na sidebar
3. Renomear "Hospitais Bloqueados" para "Hospitais"
4. Verificar consistencia em mobile drawer
5. Verificar consistencia em command palette

**DoD:**
- [x] Labels consistentes em todas as navegacoes
- [x] URLs inalteradas (backwards compatible)
- [x] Mesmo label para mesma funcionalidade

---

### S45.E4.4 - Documentar Nova Arquitetura

**Objetivo:** Criar documentacao da nova estrutura de navegacao.

**Arquivo:** `docs/arquitetura/navegacao-dashboard.md`

**Conteudo:**

```markdown
# Arquitetura de Navegacao - Dashboard Julia

## Estrutura de Rotas

### Rotas Principais

| Rota | Descricao | Layout |
|------|-----------|--------|
| /dashboard | Dashboard principal | Padrao |
| /conversas | Chat com medicos | Full-screen |
| /campanhas | Gestao de campanhas | Padrao |
| /vagas | Plantoes disponiveis | Padrao |
| /medicos | Banco de medicos | Padrao |
| /metricas | Analytics | Padrao |

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
| /grupos | /chips/grupos | Reorganizacao |

## Layouts

### Layout Padrao
- Sidebar desktop (w-64)
- Header
- Bottom nav mobile
- Padding no conteudo

### Layout Full-Screen
- Usado em: /conversas
- Sem padding
- Flex column
- Split pane

### Layout Modulo Chips
- Sidebar propria
- Sem sidebar principal
- Navegacao interna

## Navegacao Mobile

### Bottom Nav (5 itens)
1. Home (/dashboard)
2. Conversas (/conversas)
3. Campanhas (/campanhas)
4. Chips (/chips)
5. Menu (abre drawer)

### Drawer Mobile
- Todas as rotas agrupadas
- Mesma estrutura da sidebar desktop

## Command Palette (Cmd+K)

Acesso rapido a todas as paginas e acoes.

### Atalhos
- Cmd+K / Ctrl+K: Abrir
- Escape: Fechar
- Enter: Selecionar
- Setas: Navegar

### Grupos
1. Recentes (ultimas 5 paginas)
2. Acoes Rapidas
3. Paginas
```

**Tarefas:**
1. Criar arquivo de documentacao
2. Documentar todas as rotas
3. Documentar redirects
4. Documentar layouts especiais
5. Documentar navegacao mobile
6. Documentar command palette

**DoD:**
- [x] Documentacao criada
- [x] Todas as rotas documentadas
- [x] Redirects documentados
- [x] Diagramas/ASCII art incluidos
- [x] Revisado e aprovado

---

## Mapa de Mudancas

### Antes

```
/
├── dashboard
├── metricas
├── campanhas
├── vagas
├── conversas
├── medicos
├── chips/
│   ├── [id]
│   ├── alertas
│   ├── warmup
│   └── configuracoes
├── grupos            ← Fora do modulo chips
├── monitor
├── health
├── integridade
├── qualidade
├── auditoria
├── instrucoes
├── hospitais/
│   └── bloqueados   ← Unica subrota
├── sistema
└── ajuda
```

### Depois

```
/
├── dashboard
├── conversas
├── campanhas
├── vagas
├── medicos
├── chips/
│   ├── [id]
│   ├── alertas
│   ├── grupos       ← Movido para ca
│   ├── warmup
│   └── configuracoes
├── monitor
├── health
├── integridade
├── metricas
├── qualidade
├── auditoria
├── instrucoes
├── hospitais/
│   └── bloqueados
├── sistema
├── ajuda
└── grupos (redirect → /chips/grupos)
```

## Consideracoes de Backwards Compatibility

- **Redirects 301** para URLs antigas
- **Nao quebrar bookmarks** dos usuarios
- **APIs inalteradas** - apenas frontend
- **Testes de regressao** antes de deploy
