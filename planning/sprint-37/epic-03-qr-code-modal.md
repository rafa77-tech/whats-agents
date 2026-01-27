# Epic 03 - QR Code Modal

**Sprint:** 37
**Estimativa:** 1 dia
**Prioridade:** P0 (Bloqueador)
**Depende de:** Epic 02

---

## Objetivo

Criar componente React para exibir QR code de autenticação WhatsApp com polling automático.

---

## Arquivo

`dashboard/components/chips/qr-code-modal.tsx`

---

## Componente

```tsx
interface QRCodeModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  instanceName: string
  chipId?: string
  onConnected: () => void
  mode: 'create' | 'reconnect'
}

export function QRCodeModal({
  open,
  onOpenChange,
  instanceName,
  chipId,
  onConnected,
  mode,
}: QRCodeModalProps)
```

---

## Estados

| Estado | Descrição | UI |
|--------|-----------|-----|
| `loading` | Carregando QR | Spinner |
| `showing_qr` | QR visível | Imagem + código |
| `connecting` | Detectou scan | Spinner "Conectando..." |
| `connected` | Conectado | Checkmark verde |
| `expired` | QR expirou | Botão refresh |
| `error` | Erro na API | Mensagem + retry |

---

## Polling Logic

```tsx
const POLL_INTERVAL = 3000   // 3 segundos
const QR_EXPIRATION = 60000  // 60 segundos

// Ao abrir modal
useEffect(() => {
  if (open) {
    fetchQRCode()
  }
  return () => {
    clearInterval(pollIntervalRef.current)
    clearTimeout(qrTimerRef.current)
  }
}, [open])

// Polling quando mostrando QR
useEffect(() => {
  if (status === 'showing_qr') {
    pollIntervalRef.current = setInterval(() => {
      checkConnection()
    }, POLL_INTERVAL)
  }
  return () => clearInterval(pollIntervalRef.current)
}, [status])
```

---

## Layout

```
┌─────────────────────────────────────┐
│  Conectar Nova Instância      [X]  │
├─────────────────────────────────────┤
│  Escaneie o QR Code com o           │
│  WhatsApp para conectar a           │
│  instância julia-12345678           │
│                                     │
│  ┌─────────────────────────┐        │
│  │                         │        │
│  │       [QR CODE]         │        │
│  │                         │        │
│  └─────────────────────────┘        │
│                                     │
│  Código de pareamento:              │
│  ABC-123-XYZ                        │
│                                     │
│  📱 Aguardando escaneamento...      │
├─────────────────────────────────────┤
│  [Cancelar]           [Atualizar QR]│
└─────────────────────────────────────┘
```

---

## Dependências UI

- `@/components/ui/dialog` - Modal container
- `@/components/ui/button` - Botões
- `next/image` - Exibir QR code
- `lucide-react` - Ícones (Loader2, CheckCircle2, RefreshCw, XCircle, Smartphone)

---

## Fluxo de Estados

```
open=true
    │
    ▼
[loading] ─── fetchQRCode() ───┐
    │                          │
    │ erro                     │ sucesso
    ▼                          ▼
[error] ◄───────────── [showing_qr]
    │                          │
    │ retry                    │ poll every 3s
    └──────────────────────────┤
                               │
                    state="connecting"
                               │
                               ▼
                        [connecting]
                               │
                    state="open"
                               │
                               ▼
                        [connected]
                               │
                        onConnected()
                        close modal
```

---

## Testes de Validação

- [ ] Modal abre e exibe QR code
- [ ] QR code é imagem válida (base64)
- [ ] Código de pareamento é exibido
- [ ] Polling detecta conexão
- [ ] Estado "connected" mostra checkmark
- [ ] QR expira após 60s
- [ ] Botão refresh gera novo QR
- [ ] Cancelar fecha modal
- [ ] Erro exibe mensagem e retry
