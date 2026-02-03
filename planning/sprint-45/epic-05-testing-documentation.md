# Epic 05 - Testes e Documentacao

## Objetivo
Garantir qualidade da implementacao com testes de navegacao e documentar as mudancas no projeto.

## Stories

---

### S45.E5.1 - Testes de Navegacao E2E

**Objetivo:** Criar testes automatizados para validar que toda a navegacao funciona.

**Arquivo:** `dashboard/__tests__/navigation.test.tsx`

**Cenarios de Teste:**

```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import { useRouter, usePathname } from 'next/navigation'

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(),
}))

describe('Navigation', () => {
  describe('Sidebar', () => {
    it('renders all navigation groups', () => {
      // Verificar que todos os grupos sao renderizados
    })

    it('highlights active item correctly', () => {
      // Verificar active state
    })

    it('renders footer items separately', () => {
      // Verificar Instrucoes, Sistema, Ajuda no footer
    })
  })

  describe('Bottom Nav', () => {
    it('renders 4 navigation items plus menu button', () => {
      // Verificar 5 itens no total
    })

    it('opens drawer when menu is clicked', () => {
      // Verificar abertura do drawer
    })

    it('includes Conversas in navigation', () => {
      // Verificar que Conversas esta presente
    })
  })

  describe('Mobile Drawer', () => {
    it('renders all navigation groups', () => {
      // Verificar grupos no drawer
    })

    it('closes when item is clicked', () => {
      // Verificar fechamento ao clicar
    })

    it('closes when clicking outside', () => {
      // Verificar fechamento ao clicar fora
    })
  })

  describe('Command Palette', () => {
    it('opens with Cmd+K', () => {
      // Simular Cmd+K
    })

    it('closes with Escape', () => {
      // Simular Escape
    })

    it('navigates when item is selected', () => {
      // Verificar navegacao
    })

    it('shows recent pages', () => {
      // Verificar recentes
    })

    it('filters pages by search', () => {
      // Verificar busca
    })
  })

  describe('Redirects', () => {
    it('redirects /grupos to /chips/grupos', () => {
      // Verificar redirect
    })
  })
})
```

**Tarefas:**
1. Criar arquivo de testes
2. Implementar testes de sidebar
3. Implementar testes de bottom nav
4. Implementar testes de mobile drawer
5. Implementar testes de command palette
6. Implementar testes de redirects
7. Rodar e corrigir falhas

**Comandos:**
```bash
cd dashboard
npm run test -- --testPathPattern=navigation
```

**DoD:**
- [x] Todos os testes passando (2338 tests)
- [x] Cobertura de todos os componentes de navegacao
- [x] Testes de integracao para redirects
- [x] CI configurado para rodar testes

---

### S45.E5.2 - Testes Manuais de Regressao

**Objetivo:** Validar manualmente que nenhuma funcionalidade foi quebrada.

**Checklist de Testes Manuais:**

**Desktop:**

| Pagina | Teste | Status |
|--------|-------|--------|
| /dashboard | Carrega corretamente | [ ] |
| /conversas | Layout full-screen funciona | [ ] |
| /campanhas | Wizard de nova campanha abre | [ ] |
| /vagas | Lista de vagas carrega | [ ] |
| /medicos | Filtros funcionam | [ ] |
| /chips | Modulo com sidebar propria | [ ] |
| /chips/grupos | Pagina carrega (nova localizacao) | [ ] |
| /grupos | Redireciona para /chips/grupos | [ ] |
| /monitor | Jobs carregam | [ ] |
| /health | Status exibido | [ ] |
| /integridade | Anomalias carregam | [ ] |
| /metricas | Graficos carregam | [ ] |
| /qualidade | Lista de avaliacoes | [ ] |
| /auditoria | Logs carregam | [ ] |
| /instrucoes | Diretrizes exibidas | [ ] |
| /hospitais/bloqueados | Lista carrega | [ ] |
| /sistema | Configuracoes editaveis | [ ] |
| /ajuda | Conteudo exibido | [ ] |

**Mobile (Simular em DevTools):**

| Teste | Status |
|-------|--------|
| Bottom nav renderiza 5 itens | [ ] |
| Conversas acessivel no bottom nav | [ ] |
| Menu abre drawer | [ ] |
| Drawer tem todas as paginas | [ ] |
| Drawer fecha ao clicar em item | [ ] |
| Drawer fecha ao clicar fora | [ ] |
| Active state funciona no drawer | [ ] |

**Command Palette:**

| Teste | Status |
|-------|--------|
| Cmd+K abre | [ ] |
| Ctrl+K abre (Windows) | [ ] |
| Escape fecha | [ ] |
| Busca filtra paginas | [ ] |
| Keywords funcionam (ex: "chat" encontra Conversas) | [ ] |
| Recentes aparecem | [ ] |
| Acoes rapidas funcionam | [ ] |
| Navegacao por teclado (setas + enter) | [ ] |

**Tarefas:**
1. Executar checklist em ambiente local
2. Testar em diferentes browsers (Chrome, Firefox, Safari)
3. Testar em diferentes tamanhos de tela
4. Documentar bugs encontrados
5. Corrigir bugs antes de merge

**DoD:**
- [ ] Todos os itens do checklist verificados
- [ ] Testado em Chrome, Firefox, Safari
- [ ] Testado em mobile (simulado)
- [ ] Zero bugs criticos
- [ ] Bugs menores documentados

---

### S45.E5.3 - Atualizar Documentacao do Projeto

**Objetivo:** Atualizar CLAUDE.md e docs relacionados com as mudancas.

**Arquivos a Atualizar:**

**1. CLAUDE.md**

Adicionar na secao "Dashboard":

```markdown
### Navegacao

O dashboard usa navegacao agrupada em 6 secoes:

| Secao | Paginas |
|-------|---------|
| (sem label) | Dashboard |
| Operacoes | Conversas, Campanhas, Vagas |
| Cadastros | Medicos, Hospitais |
| WhatsApp | Chips (modulo), Grupos |
| Monitoramento | Monitor, Health, Integridade, Metricas |
| Qualidade | Avaliacoes, Auditoria |
| (footer) | Instrucoes, Sistema, Ajuda |

**Command Palette:** Cmd+K (Mac) ou Ctrl+K (Windows) para busca global.

**Mobile:** Bottom nav com 5 itens + drawer com navegacao completa.
```

**2. docs/arquitetura/navegacao-dashboard.md**

Criar arquivo completo (ja especificado no E04).

**3. planning/README.md**

Adicionar Sprint 45 na lista de sprints.

**4. Atualizar Sprints Concluidas**

```markdown
| 45 | Arquitetura da Informacao & Navegacao | 🔄 Em Andamento |
```

**Tarefas:**
1. Atualizar CLAUDE.md com secao de navegacao
2. Criar docs/arquitetura/navegacao-dashboard.md
3. Atualizar planning/README.md
4. Revisar e commitar

**DoD:**
- [ ] CLAUDE.md atualizado
- [ ] Documentacao de navegacao criada
- [ ] planning/README.md atualizado
- [ ] Documentacao revisada

---

## Checklist Final da Sprint

### Antes de Merge

- [ ] Todos os testes automatizados passando
- [ ] Testes manuais executados e aprovados
- [ ] Zero erros de TypeScript
- [ ] Lint passando
- [ ] Build de producao funciona
- [ ] Documentacao atualizada

### Apos Merge

- [ ] Deploy em staging
- [ ] Smoke test em staging
- [ ] Deploy em producao
- [ ] Monitorar erros no Sentry/logs

### Metricas de Sucesso

| Metrica | Meta | Como Medir |
|---------|------|------------|
| Paridade mobile/desktop | 100% | Todas as rotas acessiveis em mobile |
| Tempo para encontrar pagina | < 3s | Teste com usuarios |
| Bugs de regressao | 0 | Testes + monitoramento |
| Cobertura de testes | > 80% | Jest coverage |

## Rollback Plan

Se problemas criticos forem encontrados apos deploy:

1. **Reverter merge** no Git
2. **Deploy da versao anterior**
3. **Investigar** causa raiz
4. **Corrigir** em nova branch
5. **Re-deploy** com fix

**Nao fazer:**
- Hotfixes diretamente em main
- Deploy sem testes
- Ignorar erros no monitoramento
