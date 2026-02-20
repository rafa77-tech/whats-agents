# EPICO 03: Mobile & Responsividade

## Contexto

A pagina /conversas esta completamente quebrada em mobile. O chat panel tem `hidden md:flex`, entao em telas < 768px so aparece a sidebar. Clicar em uma conversa muda o `selectedId` mas o chat continua invisivel. Alem disso, o context panel so aparece em telas xl (1280px+), inacessivel na maioria dos laptops.

## Escopo

- **Incluido**: Navegacao mobile (lista ↔ chat), context panel como drawer em telas menores, ajustes de breakpoint
- **Excluido**: Redesign de componentes (Epics 04-05), bugs de dados (Epic 01)

---

## Tarefa 3.1: Navegacao mobile lista ↔ chat

### Objetivo

Implementar padrao WhatsApp/Telegram: em mobile, clicar na conversa mostra o chat (esconde a lista). Botao "Voltar" retorna a lista.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/(dashboard)/conversas/page.tsx` |
| Modificar | `dashboard/app/(dashboard)/conversas/components/chat-panel.tsx` |

### Implementacao

```typescript
// page.tsx: Adicionar estado de view mobile
const [mobileView, setMobileView] = useState<'list' | 'chat'>('list')

// Quando seleciona conversa em mobile:
const handleSelectConversation = (id: string) => {
  setSelectedId(id)
  // Em mobile, trocar para view de chat
  if (window.innerWidth < 768) {
    setMobileView('chat')
  }
}

// Botao voltar no chat-panel (so mobile):
const handleBack = () => {
  setMobileView('list')
  // Nao limpar selectedId para manter seleção ao voltar
}

// Layout condicional:
return (
  <div className="flex h-full overflow-hidden">
    {/* Sidebar - visivel em desktop sempre, em mobile so na view 'list' */}
    <div className={cn(
      "flex h-full w-full flex-col border-r bg-background md:w-[380px] lg:w-[420px]",
      mobileView === 'chat' && "hidden md:flex"
    )}>
      {/* ... sidebar content */}
    </div>

    {/* Chat panel - visivel em desktop sempre, em mobile so na view 'chat' */}
    <div className={cn(
      "h-full min-h-0 flex-1",
      mobileView === 'list' ? "hidden md:flex" : "flex"
    )}>
      {selectedId ? (
        <ChatPanel
          conversationId={selectedId}
          onBack={handleBack}  // Nova prop
          showBackButton={mobileView === 'chat'}  // Nova prop
          // ...
        />
      ) : (
        // Empty state
      )}
    </div>
  </div>
)
```

### Chat-panel: Botao voltar

```typescript
// Adicionar no header do chat-panel:
{showBackButton && (
  <Button variant="ghost" size="icon" onClick={onBack} className="md:hidden">
    <ArrowLeft className="h-5 w-5" />
  </Button>
)}
```

### Testes Obrigatorios

**Unitarios:**
- [ ] Em mobile (< 768px): clicar conversa mostra chat, esconde lista
- [ ] Em mobile: botao voltar mostra lista, esconde chat
- [ ] Em desktop (>= 768px): ambos visiveis sempre
- [ ] Seleção persiste ao alternar views
- [ ] Resize de janela nao quebra estado

### Definition of Done

- [ ] Mobile funcional: navegar lista → conversa → voltar
- [ ] Desktop nao afetado (comportamento identico ao atual)
- [ ] Botao voltar visivel apenas em mobile
- [ ] Testes passando

### Estimativa

2h

---

## Tarefa 3.2: Context panel como drawer responsivo

### Objetivo

O context panel so aparece em telas `xl` (1280px+). Mudar para `lg` (1024px+) como panel, e em telas menores como Sheet/Drawer que desliza da direita.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/(dashboard)/conversas/page.tsx` |
| Criar | `dashboard/app/(dashboard)/conversas/components/context-drawer.tsx` |

### Implementacao

```typescript
// page.tsx: Usar Sheet do shadcn para telas < lg
import { Sheet, SheetContent } from '@/components/ui/sheet'

// Desktop (lg+): panel fixo como hoje
{showContext && selectedId && (
  <div className="hidden h-full w-[340px] border-l lg:block">
    <DoctorContextPanel conversationId={selectedId} onClose={() => setShowContext(false)} />
  </div>
)}

// Mobile/Tablet (< lg): drawer da direita
<Sheet open={showContext && !!selectedId} onOpenChange={(open) => !open && setShowContext(false)}>
  <SheetContent side="right" className="w-[340px] p-0 lg:hidden">
    <DoctorContextPanel conversationId={selectedId!} onClose={() => setShowContext(false)} />
  </SheetContent>
</Sheet>
```

### Testes Obrigatorios

**Unitarios:**
- [ ] Em lg+: context panel aparece como painel fixo
- [ ] Em < lg: context panel aparece como drawer/sheet
- [ ] Fechar drawer funciona
- [ ] Toggle funciona em ambos os modos
- [ ] Content panel exibe dados corretos em ambos modos

### Definition of Done

- [ ] Context panel acessivel em telas >= 768px (como drawer)
- [ ] Em lg+ (1024px): panel fixo como hoje (mas agora em lg, nao xl)
- [ ] Em < lg: Sheet/Drawer da direita
- [ ] Testes passando

### Estimativa

2h
