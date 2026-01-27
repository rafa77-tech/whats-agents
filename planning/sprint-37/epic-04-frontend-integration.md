# Epic 04 - Frontend Integration

**Sprint:** 37
**Estimativa:** 1.5 dias
**Prioridade:** P0 (Bloqueador)
**Depende de:** Epic 03

---

## Objetivo

Integrar todos os componentes de gerenciamento de instâncias no dashboard existente.

---

## Escopo

1. Create Instance Dialog
2. Atualização do Actions Panel
3. Atualização da Chips Page
4. Types TypeScript
5. API Client

---

## 1. Create Instance Dialog

**Arquivo:** `dashboard/components/chips/create-instance-dialog.tsx`

```tsx
interface CreateInstanceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: () => void
}

export function CreateInstanceDialog({
  open,
  onOpenChange,
  onCreated,
}: CreateInstanceDialogProps)
```

### Layout

```
┌─────────────────────────────────────┐
│  Criar Nova Instância         [X]  │
├─────────────────────────────────────┤
│  Adicione um novo chip/instância    │
│  WhatsApp ao pool.                  │
│                                     │
│  Telefone *                         │
│  ┌─────────────────────────────┐    │
│  │ 5511999999999               │    │
│  └─────────────────────────────┘    │
│  Formato: DDI + DDD + número        │
│                                     │
│  Nome da Instância (opcional)       │
│  ┌─────────────────────────────┐    │
│  │ julia-12345678              │    │
│  └─────────────────────────────┘    │
│  Se não informado, será gerado      │
│                                     │
├─────────────────────────────────────┤
│  [Cancelar]         [Criar e Conectar]│
└─────────────────────────────────────┘
```

### Fluxo

1. Usuário preenche telefone
2. Clica "Criar e Conectar"
3. POST /instances/create
4. Fecha dialog
5. Abre QR Code Modal
6. Após conectar, refresh lista

---

## 2. Actions Panel Update

**Arquivo:** `dashboard/components/chips/chip-actions-panel.tsx`

### Novas Ações

| Ação | Condição | Variant |
|------|----------|---------|
| Desconectar | `evolution_connected === true` | outline |
| Reconectar | `status === 'pending'` ou `evolution_connected === false` | default |
| Excluir | `status !== 'active'` e `status !== 'warming'` | destructive |

### Configuração

```tsx
const actionsConfig = {
  // ... ações existentes (pause, resume, promote)

  disconnect: {
    label: 'Desconectar',
    description: 'Desconecta a sessão do WhatsApp. O chip pode ser reconectado depois.',
    confirmLabel: 'Desconectar',
    icon: WifiOff,
    variant: 'outline',
    condition: (chip) => chip.evolutionConnected === true,
  },
  reconnect: {
    label: 'Reconectar',
    description: 'Gera novo QR Code para reconectar o chip.',
    confirmLabel: 'Reconectar',
    icon: QrCode,
    variant: 'default',
    condition: (chip) => chip.status === 'pending' || chip.evolutionConnected === false,
  },
  delete: {
    label: 'Excluir Instância',
    description: 'Remove permanentemente a instância. Esta ação não pode ser desfeita.',
    confirmLabel: 'Excluir',
    icon: Trash2,
    variant: 'destructive',
    condition: (chip) => !['active', 'warming'].includes(chip.status),
  },
}
```

---

## 3. Chips Page Update

**Arquivo:** `dashboard/components/chips/chips-page-content.tsx`

### Mudanças

```tsx
// Novo estado
const [showCreateDialog, setShowCreateDialog] = useState(false)

// Botão no header
<Button variant="default" size="sm" onClick={() => setShowCreateDialog(true)}>
  <Plus className="mr-2 h-4 w-4" />
  Nova Instância
</Button>

// Dialog
<CreateInstanceDialog
  open={showCreateDialog}
  onOpenChange={setShowCreateDialog}
  onCreated={() => {
    setShowCreateDialog(false)
    fetchChips()
    fetchPoolStatus()
  }}
/>
```

---

## 4. Types TypeScript

**Arquivo:** `dashboard/types/chips.ts`

```typescript
// ============================================================================
// Instance Management Types
// ============================================================================

export type ConnectionState = 'open' | 'close' | 'connecting'

export interface CreateInstanceRequest {
  telefone: string
  instanceName?: string
}

export interface CreateInstanceResponse {
  sucesso: boolean
  chipId: string
  instanceName: string
  qrCode: string
  error?: string
}

export interface QRCodeResponse {
  qrCode: string
  code: string
  connected: boolean
  instanceName: string
}

export interface ConnectionStateResponse {
  state: ConnectionState
  connected: boolean
  instanceName: string
}

export interface InstanceActionResponse {
  sucesso: boolean
  message?: string
  error?: string
}

// Atualizar ChipFullDetail
export interface ChipFullDetail extends ChipListItem {
  // ... campos existentes
  evolutionConnected: boolean  // NOVO
  instanceName: string         // NOVO
}
```

---

## 5. API Client

**Arquivo:** `dashboard/lib/api/chips.ts`

```typescript
// ============================================================================
// Instance Management
// ============================================================================

export async function createInstance(
  data: CreateInstanceRequest
): Promise<CreateInstanceResponse> {
  return fetchApi<CreateInstanceResponse>('/api/dashboard/chips/instances/create', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getQRCode(instanceName: string): Promise<QRCodeResponse> {
  return fetchApi<QRCodeResponse>(
    `/api/dashboard/chips/instances/${encodeURIComponent(instanceName)}/qr-code`
  )
}

export async function getConnectionState(
  instanceName: string
): Promise<ConnectionStateResponse> {
  return fetchApi<ConnectionStateResponse>(
    `/api/dashboard/chips/instances/${encodeURIComponent(instanceName)}/connection-state`
  )
}

export async function disconnectChip(chipId: string): Promise<InstanceActionResponse> {
  return fetchApi<InstanceActionResponse>(`/api/dashboard/chips/${chipId}/disconnect`, {
    method: 'POST',
  })
}

export async function deleteInstance(chipId: string): Promise<InstanceActionResponse> {
  return fetchApi<InstanceActionResponse>(`/api/dashboard/chips/${chipId}/instance`, {
    method: 'DELETE',
  })
}

export async function reconnectChip(chipId: string): Promise<QRCodeResponse> {
  return fetchApi<QRCodeResponse>(`/api/dashboard/chips/${chipId}/reconnect`, {
    method: 'POST',
  })
}

// Atualizar exports
export const chipsApi = {
  // ... existentes
  createInstance,
  getQRCode,
  getConnectionState,
  disconnectChip,
  deleteInstance,
  reconnectChip,
}
```

---

## Checklist

### Create Instance Dialog
- [ ] Form com validação de telefone
- [ ] Nome opcional auto-gerado
- [ ] Loading state durante criação
- [ ] Erro exibido em banner vermelho
- [ ] Abre QR modal após criar

### Actions Panel
- [ ] Ação "Desconectar" para chips conectados
- [ ] Ação "Reconectar" para chips desconectados
- [ ] Ação "Excluir" para chips não ativos
- [ ] Confirmation dialogs para todas
- [ ] Reconnect abre QR modal

### Chips Page
- [ ] Botão "Nova Instância" no header
- [ ] Dialog integrado
- [ ] Refresh após criar/conectar

### Types & API
- [ ] Todos os tipos definidos
- [ ] API client com 6 novos métodos
- [ ] Exports atualizados
