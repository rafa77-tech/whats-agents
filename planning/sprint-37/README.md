# Sprint 37 - Gerenciamento de Instâncias Evolution API

**Início:** A definir
**Duração estimada:** 3-5 dias
**Dependências:** Sprint 36 (Dashboard de Chips) completa

---

## Objetivo

Integrar no dashboard as funcionalidades de gerenciamento de instâncias WhatsApp da Evolution API, permitindo criar, conectar (via QR code), desconectar e excluir instâncias diretamente da interface.

### Por que agora?

O dashboard de chips (Sprint 36) mostra o status dos chips, mas todas as operações de gerenciamento de instâncias ainda precisam ser feitas via Evolution API Dashboard externo. Isso:
- Quebra o fluxo de trabalho do operador
- Exige conhecimento técnico da Evolution API
- Impede automação completa do ciclo de vida dos chips

### Benefícios

| Antes | Depois |
|-------|--------|
| Criar instância no Evolution Dashboard | Criar direto no Julia Dashboard |
| Copiar QR code de outra interface | QR code modal integrado |
| Não sabe se chip está conectado em tempo real | Status de conexão com polling |
| Precisa acessar duas interfaces | Tudo em um lugar |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                      Dashboard (Next.js)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │  Create Instance │    │   QR Code Modal  │                   │
│  │     Dialog       │───►│  (with polling)  │                   │
│  └──────────────────┘    └────────┬─────────┘                   │
│                                   │                              │
│  ┌──────────────────┐             │                              │
│  │ Chip Actions     │◄────────────┘                              │
│  │ Panel (updated)  │                                            │
│  └────────┬─────────┘                                            │
│           │                                                      │
└───────────┼──────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                            │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────────┐    ┌───────────────────┐                  │
│  │ chips_dashboard   │    │ instance_manager  │                  │
│  │ router (updated)  │───►│ service (new)     │                  │
│  └───────────────────┘    └─────────┬─────────┘                  │
│                                     │                             │
└─────────────────────────────────────┼─────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Evolution API                               │
├─────────────────────────────────────────────────────────────────┤
│  POST /instance/create          - Criar instância                │
│  GET  /instance/connect/{name}  - Obter QR code                  │
│  GET  /instance/connectionState - Verificar conexão              │
│  DELETE /instance/logout        - Desconectar                    │
│  DELETE /instance/delete        - Excluir instância              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Decisões Técnicas

### 1. QR Code Polling Strategy

| Parâmetro | Valor | Motivo |
|-----------|-------|--------|
| Poll interval | 3 segundos | Balanceia responsividade vs carga |
| QR expiration | 60 segundos | QR da Evolution expira em ~45-60s |
| Max poll time | 120 segundos | Evita polling infinito |
| Auto-refresh | Sim | Gera novo QR quando expira |

### 2. Estados de Conexão

```
Evolution State    →    UI State           →    Ação
─────────────────────────────────────────────────────────
"close"            →    showing_qr         →    Exibe QR code
"connecting"       →    connecting         →    Exibe spinner
"open"             →    connected          →    Fecha modal, refresh
error              →    error              →    Exibe retry
timeout            →    expired            →    Exibe refresh
```

### 3. Fluxo de Criação de Instância

```
1. Usuário clica "Nova Instância"
2. Preenche telefone (obrigatório) e nome (opcional)
3. Backend:
   a. POST /instance/create na Evolution API
   b. INSERT chip na tabela com status='pending'
   c. Retorna QR code inicial
4. Frontend abre QR Modal
5. Polling verifica conexão a cada 3s
6. Quando conectado:
   a. Backend atualiza: evolution_connected=true, status='warming'
   b. Frontend fecha modal e refresh lista
```

---

## Épicos

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E01 | Instance Manager Service | Novo serviço Python para Evolution API | 0.5d |
| E02 | API Endpoints | 5 novos endpoints no router | 0.5d |
| E03 | QR Code Modal | Componente React com polling | 1d |
| E04 | Create Instance Dialog | Dialog de criação com form | 0.5d |
| E05 | Actions Panel Update | Adicionar disconnect/reconnect/delete | 0.5d |
| E06 | Page Integration | Botão "Nova Instância" e integração | 0.5d |
| E07 | Types e API Client | Tipos TypeScript e métodos do client | 0.5d |
| E08 | Testes e Validação | Testes manuais end-to-end | 0.5d |

**Total estimado:** 4-5 dias

---

## Arquivos a Criar

### Backend

| Arquivo | Descrição |
|---------|-----------|
| `app/services/chips/instance_manager.py` | Serviço de gerenciamento de instâncias |

### Frontend

| Arquivo | Descrição |
|---------|-----------|
| `dashboard/components/chips/qr-code-modal.tsx` | Modal do QR code com polling |
| `dashboard/components/chips/create-instance-dialog.tsx` | Dialog de criação |

---

## Arquivos a Modificar

### Backend

| Arquivo | Mudança |
|---------|---------|
| `app/services/chips/__init__.py` | Exportar `instance_manager` |
| `app/api/routes/chips_dashboard.py` | 5 novos endpoints |

### Frontend

| Arquivo | Mudança |
|---------|---------|
| `dashboard/types/chips.ts` | Tipos de instância e conexão |
| `dashboard/lib/api/chips.ts` | 6 novos métodos API |
| `dashboard/components/chips/chip-actions-panel.tsx` | 3 novas ações |
| `dashboard/components/chips/chips-page-content.tsx` | Botão "Nova Instância" |

---

## Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/dashboard/chips/instances/create` | Criar instância |
| GET | `/api/dashboard/chips/instances/{name}/qr-code` | Obter QR code |
| GET | `/api/dashboard/chips/instances/{name}/connection-state` | Status conexão |
| POST | `/api/dashboard/chips/{id}/disconnect` | Desconectar |
| DELETE | `/api/dashboard/chips/{id}/instance` | Excluir |
| POST | `/api/dashboard/chips/{id}/reconnect` | Reconectar |

---

## Fluxos de Uso

### Criar Nova Instância

```
Usuário                    Frontend                   Backend                  Evolution
   │                          │                          │                         │
   │──[Clica Nova Instância]─►│                          │                         │
   │                          │──[Abre Dialog]──────────►│                         │
   │──[Preenche telefone]────►│                          │                         │
   │──[Clica Criar]──────────►│                          │                         │
   │                          │──[POST /instances/create]►│                         │
   │                          │                          │──[POST /instance/create]►│
   │                          │                          │◄─[QR code base64]────────│
   │                          │                          │──[INSERT chip]──────────►│
   │                          │◄─[QR code + chip_id]─────│                         │
   │                          │──[Abre QR Modal]────────►│                         │
   │◄─[Exibe QR code]─────────│                          │                         │
   │                          │──[Poll /connection-state]►│                         │
   │──[Escaneia QR]──────────────────────────────────────────────────────────────►│
   │                          │                          │◄─[state: open]──────────│
   │                          │◄─[connected: true]───────│                         │
   │                          │                          │──[UPDATE chip status]───►│
   │◄─[Fecha modal, refresh]──│                          │                         │
```

### Desconectar Instância

```
1. Usuário clica "Desconectar" no Actions Panel
2. Confirmation dialog aparece
3. Usuário confirma
4. POST /chips/{id}/disconnect
5. Backend: DELETE /instance/logout/{name}
6. Backend: UPDATE chip SET evolution_connected=false, status='pending'
7. Frontend: Refresh página
```

### Reconectar Instância

```
1. Usuário clica "Reconectar" em chip desconectado
2. QR Modal abre
3. POST /chips/{id}/reconnect gera novo QR
4. Mesmo fluxo de polling
```

---

## Checklist Final

### Pré-requisitos
- [ ] Sprint 36 (Dashboard de Chips) completa
- [ ] Evolution API rodando e acessível
- [ ] Variáveis de ambiente configuradas (EVOLUTION_API_URL, EVOLUTION_API_KEY)

### Entregas

#### Backend
- [ ] E01 - `instance_manager.py` criado e funcionando
- [ ] E02 - 5 endpoints implementados e testados

#### Frontend
- [ ] E03 - QR Code Modal com polling funcionando
- [ ] E04 - Create Instance Dialog implementado
- [ ] E05 - Actions Panel com novas ações
- [ ] E06 - Botão "Nova Instância" na página
- [ ] E07 - Types e API client atualizados

### Validação End-to-End
- [ ] Criar instância → QR aparece → Escanear → Chip aparece como "warming"
- [ ] Desconectar chip → Status muda para "pending" → evolution_connected=false
- [ ] Reconectar chip → Novo QR → Escanear → Conectado novamente
- [ ] Excluir instância → Chip marcado como "cancelled"
- [ ] QR expira → Botão refresh → Novo QR gerado
- [ ] Polling detecta conexão em < 5 segundos

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| QR code expira muito rápido | Média | Baixo | Auto-refresh com timer visível |
| Evolution API indisponível | Baixa | Alto | Circuit breaker, mensagem clara de erro |
| Polling sobrecarrega API | Baixa | Médio | Interval de 3s, max poll time |
| Usuário fecha modal antes de conectar | Média | Baixo | Chip fica como "pending", pode reconectar |
| Nome de instância duplicado | Baixa | Médio | Validação backend, erro claro |

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Tempo para criar e conectar instância | < 2 minutos |
| Taxa de sucesso de conexão | > 95% |
| Tempo de detecção de conexão (polling) | < 6 segundos |
| Erros de UX reportados | 0 |

---

## Referências

- Evolution API Quick Ref: `docs/integracoes/evolution-api-quickref.md`
- Dashboard Patterns: `dashboard/components/chips/chip-actions-panel.tsx`
- Existing Sync Service: `app/services/chips/sync_evolution.py`
