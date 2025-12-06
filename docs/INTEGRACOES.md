# Integrações Externas - MVP Júlia

Este documento detalha cada integração necessária para o MVP.

---

## Resumo das Integrações

| Integração | Propósito | Status | Prioridade |
|------------|-----------|--------|------------|
| Evolution API | Gateway WhatsApp | Docker OK | P0 |
| Chatwoot | Supervisão humana | Docker OK | P0 |
| Supabase | Banco de dados | Configurado | P0 |
| Claude API (Anthropic) | LLM para Júlia | Pendente API key | P0 |
| Slack Webhook | Notificações/Reports | Pendente config | P1 |

---

## 1. Evolution API

### Descrição
Gateway open-source para WhatsApp Business API. Permite enviar/receber mensagens, mostrar presença, etc.

### Status Atual
- [x] Docker rodando
- [ ] Instância WhatsApp conectada
- [ ] Webhook configurado

### Configuração

**Variáveis de ambiente:**
```bash
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=<gerar no painel>
EVOLUTION_INSTANCE=julia
```

**Criar instância:**
```bash
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: ${EVOLUTION_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "julia",
    "qrcode": true,
    "integration": "WHATSAPP-BAILEYS"
  }'
```

**Configurar webhook:**
```bash
curl -X POST http://localhost:8080/webhook/set/julia \
  -H "apikey: ${EVOLUTION_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://host.docker.internal:8000/webhook/evolution",
    "enabled": true,
    "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]
  }'
```

### Endpoints Utilizados

| Endpoint | Método | Uso |
|----------|--------|-----|
| `/message/sendText/{instance}` | POST | Enviar mensagem |
| `/chat/sendPresence/{instance}` | POST | Mostrar online/digitando |
| `/chat/markMessageAsRead/{instance}` | POST | Marcar como lida |

### Payload de Mensagem Recebida

```json
{
  "event": "messages.upsert",
  "instance": "julia",
  "data": {
    "key": {
      "remoteJid": "5511999999999@s.whatsapp.net",
      "fromMe": false,
      "id": "ABC123"
    },
    "message": {
      "conversation": "Oi, tudo bem?"
    },
    "messageTimestamp": 1701888000
  }
}
```

### Checklist de Teste

- [ ] Escanear QR code e conectar número
- [ ] Enviar mensagem de teste
- [ ] Receber mensagem de teste via webhook
- [ ] Mostrar "digitando" e depois enviar
- [ ] Marcar mensagem como lida

---

## 2. Chatwoot

### Descrição
Plataforma open-source de atendimento. Usamos para o gestor visualizar e intervir nas conversas.

### Status Atual
- [x] Docker rodando
- [ ] Conta admin criada
- [ ] Inbox WhatsApp configurado
- [ ] Webhook para labels

### Configuração

**Variáveis de ambiente:**
```bash
CHATWOOT_URL=http://localhost:3000
CHATWOOT_API_KEY=<gerar no painel>
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1
```

**Criar inbox via API:**
```bash
curl -X POST http://localhost:3000/api/v1/accounts/1/inboxes \
  -H "api_access_token: ${CHATWOOT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Julia WhatsApp",
    "channel": {
      "type": "api",
      "webhook_url": "http://host.docker.internal:8000/webhook/chatwoot"
    }
  }'
```

### Endpoints Utilizados

| Endpoint | Método | Uso |
|----------|--------|-----|
| `/api/v1/accounts/{id}/conversations` | GET/POST | Listar/criar conversas |
| `/api/v1/accounts/{id}/conversations/{id}/messages` | POST | Enviar mensagem |
| `/api/v1/accounts/{id}/conversations/{id}/labels` | POST | Adicionar label |

### Sincronização de Mensagens

```
Médico → WhatsApp → Evolution → FastAPI → Chatwoot
                                    ↓
                               Júlia responde
                                    ↓
FastAPI → Evolution → WhatsApp → Médico
    ↓
Chatwoot (mostra resposta da Júlia)
```

### Labels para Controle

| Label | Ação |
|-------|------|
| `humano` | Júlia para de responder, gestor assume |
| `vip` | Tratamento especial |
| `urgente` | Prioridade alta |

### Webhook de Label

```json
{
  "event": "conversation_updated",
  "conversation": {
    "id": 123,
    "labels": ["humano"]
  }
}
```

### Checklist de Teste

- [ ] Acessar painel http://localhost:3000
- [ ] Criar conta admin
- [ ] Criar inbox "Julia WhatsApp"
- [ ] Sincronizar conversa de teste
- [ ] Adicionar label e verificar webhook
- [ ] Enviar mensagem pelo painel

---

## 3. Supabase

### Descrição
Banco de dados PostgreSQL gerenciado com API REST automática.

### Status Atual
- [x] Projeto criado
- [x] Schema executado (27 tabelas)
- [x] MCP configurado no Claude Code

### Configuração

**Variáveis de ambiente:**
```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

### Tabelas Principais (MVP)

| Tabela | Uso |
|--------|-----|
| `clientes` | Médicos (nome, telefone, CRM, stage) |
| `conversations` | Estado das conversas |
| `interacoes` | Histórico de mensagens |
| `vagas` | Plantões disponíveis |
| `hospitais` | Lista de hospitais |
| `especialidades` | Lista de especialidades |
| `handoffs` | Registro de transferências |

### Queries Principais

**Buscar médico por telefone:**
```sql
SELECT * FROM clientes WHERE telefone = '5511999999999';
```

**Buscar conversa ativa:**
```sql
SELECT * FROM conversations
WHERE cliente_id = $1 AND status = 'aberta';
```

**Buscar vagas compatíveis:**
```sql
SELECT v.*, h.nome as hospital_nome
FROM vagas v
JOIN hospitais h ON v.hospital_id = h.id
WHERE v.especialidade_id = $1
  AND v.status = 'aberta'
  AND v.data_plantao >= CURRENT_DATE
ORDER BY v.prioridade DESC, v.data_plantao ASC;
```

### Checklist de Teste

- [ ] Conectar via cliente Python
- [ ] Inserir médico de teste
- [ ] Buscar médico
- [ ] Inserir conversa
- [ ] Inserir interação
- [ ] Testar RLS (se habilitado)

---

## 4. Claude API (Anthropic)

### Descrição
API do Claude para geração de respostas da Júlia.

### Status Atual
- [ ] API key obtida
- [ ] Modelo escolhido (Haiku)
- [ ] Fallback configurado (Sonnet)

### Configuração

**Variáveis de ambiente:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514
```

### Uso

**Modelo principal:** Claude 3.5 Haiku
- Custo: $0.25/1M input, $1.25/1M output
- Uso: 80% das interações

**Modelo complexo:** Claude Sonnet 4
- Custo: $3/1M input, $15/1M output
- Uso: Negociações, situações delicadas

### Estimativa de Custo (MVP)

| Cenário | Msgs/dia | Tokens/msg | Custo/dia |
|---------|----------|------------|-----------|
| Baixo | 50 | 500 in + 200 out | ~$0.10 |
| Médio | 200 | 500 in + 200 out | ~$0.40 |
| Alto | 500 | 500 in + 200 out | ~$1.00 |

**Custo mensal estimado:** $10-30 (MVP)

### Exemplo de Chamada

```python
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=500,
    system=SYSTEM_PROMPT_JULIA,
    messages=[
        {"role": "user", "content": contexto + "\n\nMédico: " + mensagem}
    ]
)
```

### Checklist de Teste

- [ ] Obter API key
- [ ] Testar chamada básica
- [ ] Testar com system prompt da Júlia
- [ ] Medir latência
- [ ] Testar fallback para Sonnet

---

## 5. Slack Webhook

### Descrição
Webhook para enviar notificações e reports para canal do Slack.

### Status Atual
- [ ] Workspace identificado
- [ ] Webhook URL gerada
- [ ] Canal criado

### Configuração

**Variáveis de ambiente:**
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
SLACK_CHANNEL=#julia-reports
```

### Tipos de Mensagem

**Report diário:**
```json
{
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": "📊 Júlia - Report Diário"}
    },
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "*Prospecção*\n• Enviadas: 47\n• Respondidas: 14 (30%)"}
    }
  ]
}
```

**Alerta de handoff:**
```json
{
  "text": "🚨 Handoff necessário!",
  "attachments": [
    {
      "color": "#ff0000",
      "fields": [
        {"title": "Médico", "value": "Dr. Carlos (CRM 123456)"},
        {"title": "Motivo", "value": "Médico irritado"},
        {"title": "Resumo", "value": "Reclamou do valor..."}
      ]
    }
  ]
}
```

**Plantão fechado:**
```json
{
  "text": "🎉 Plantão fechado!",
  "attachments": [
    {
      "color": "#00ff00",
      "fields": [
        {"title": "Médico", "value": "Dra. Ana"},
        {"title": "Hospital", "value": "Hospital Brasil"},
        {"title": "Data", "value": "Sábado, 14/12 - 07h às 19h"},
        {"title": "Valor", "value": "R$ 2.400"}
      ]
    }
  ]
}
```

### Checklist de Teste

- [ ] Criar canal #julia-reports
- [ ] Gerar webhook URL
- [ ] Enviar mensagem de teste
- [ ] Testar formatação de report
- [ ] Testar alerta de handoff

---

## Diagrama de Integrações

```
                                    ┌─────────────────┐
                                    │    Anthropic    │
                                    │   Claude API    │
                                    └────────┬────────┘
                                             │
                                             │ LLM calls
                                             │
┌─────────────┐      ┌─────────────┐      ┌──┴──────────┐      ┌─────────────┐
│   Médico    │◀────▶│  WhatsApp   │◀────▶│   FastAPI   │◀────▶│  Supabase   │
│             │      │             │      │   (Python)  │      │ (PostgreSQL)│
└─────────────┘      └──────┬──────┘      └──────┬──────┘      └─────────────┘
                            │                    │
                            │                    │
                     ┌──────┴──────┐             │
                     │  Evolution  │             │
                     │    API      │             │
                     └─────────────┘             │
                                                 │
                            ┌────────────────────┼────────────────────┐
                            │                    │                    │
                     ┌──────┴──────┐      ┌──────┴──────┐      ┌──────┴──────┐
                     │  Chatwoot   │      │    Slack    │      │   Redis     │
                     │(Supervisão) │      │  (Reports)  │      │  (Filas)    │
                     └─────────────┘      └─────────────┘      └─────────────┘
                            │
                            │
                     ┌──────┴──────┐
                     │   Gestor    │
                     └─────────────┘
```

---

## Ordem de Configuração

1. **Supabase** - Já configurado, verificar conexão
2. **Evolution API** - Conectar número WhatsApp
3. **Claude API** - Obter e testar API key
4. **Chatwoot** - Criar inbox e configurar webhook
5. **Slack** - Criar canal e webhook

---

## Troubleshooting Comum

### Evolution API não recebe mensagens
- Verificar se instância está conectada (QR code escaneado)
- Verificar URL do webhook (use `host.docker.internal` se Docker)
- Verificar se eventos estão habilitados

### Chatwoot não sincroniza
- Verificar API key tem permissão
- Verificar inbox_id correto
- Verificar webhook está configurado

### Claude API lenta
- Verificar região (usar endpoints mais próximos)
- Reduzir max_tokens se possível
- Considerar cache de respostas comuns

### Slack não recebe mensagens
- Verificar webhook URL ainda válida
- Verificar formato do payload
- Verificar canal existe
