# Sistema Julia Warmer e Chips

> Implementado nas Sprints 25-27

## Visão Geral

O sistema de Warmer e Chips gerencia múltiplas instâncias de Julia (chips WhatsApp), incluindo aquecimento de números novos, orquestração multi-instância e ativação de chips via VPS.

## Componentes

### Julia Warmer (Sprint 25)

Sistema de aquecimento de números novos para evitar banimento do WhatsApp.

**Objetivo:** Números novos precisam de um período de "aquecimento" antes de serem usados para prospecção ativa.

```
app/services/chips/
├── warmer.py           # Lógica de aquecimento
├── warmer_scheduler.py # Agendamento de aquecimento
├── health_monitor.py   # Monitoramento de saúde dos chips
└── metrics.py          # Métricas de aquecimento
```

### Multi-Julia Orchestration (Sprint 26)

Orquestração de múltiplas instâncias de Julia para escala.

**Funcionalidades:**
- Balanceamento de carga entre instâncias
- Failover automático
- Distribuição de médicos por instância

```
app/services/chips/
├── orchestrator.py     # Orquestrador principal
├── load_balancer.py    # Balanceamento de carga
├── instance_manager.py # Gerenciamento de instâncias
└── failover.py         # Lógica de failover
```

### Chip Activator (Sprint 27)

Ativação de chips via VPS para números virtuais Salvy.

**Fluxo:**
1. Número virtual provisionado via Salvy
2. Chip Activator conecta via VPS
3. Recebe código SMS de verificação
4. Ativa número no WhatsApp

```
app/services/chip_activator/
├── activator.py        # Ativador principal
├── vps_manager.py      # Gerenciamento de VPS
├── sms_handler.py      # Handler de SMS Salvy
└── whatsapp_linker.py  # Link com Evolution API
```

## Fluxo de Aquecimento

```
1. Número Novo Provisionado (Salvy)
         │
         ▼
2. Ativação via Chip Activator
         │
         ▼
3. Período de Aquecimento (7-14 dias)
   - Envio gradual de mensagens
   - Simulação de uso humano
   - Monitoramento de banimento
         │
         ▼
4. Chip Pronto para Produção
         │
         ▼
5. Adicionado ao Pool de Orquestração
```

## Estados de um Chip

| Estado | Descrição |
|--------|-----------|
| `provisioning` | Aguardando provisionamento Salvy |
| `activating` | Em ativação no WhatsApp |
| `warming` | Em período de aquecimento |
| `ready` | Pronto para produção |
| `active` | Em uso ativo |
| `cooling` | Em descanso (rate limit) |
| `banned` | Banido do WhatsApp |
| `retired` | Desativado permanentemente |

## Integração Salvy

A integração com Salvy provê números virtuais brasileiros.

**Documentação:** `docs/integracoes/salvy-quickref.md`

## Configuração

### Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `SALVY_API_TOKEN` | Token da API Salvy |
| `VPS_SSH_KEY` | Chave SSH para VPS |
| `WARMER_MIN_DAYS` | Dias mínimos de aquecimento (default: 7) |
| `MAX_CHIPS_ACTIVE` | Máximo de chips ativos simultâneos |

## Monitoramento

### Métricas

| Métrica | Descrição |
|---------|-----------|
| `chips_total` | Total de chips no sistema |
| `chips_active` | Chips em uso ativo |
| `chips_warming` | Chips em aquecimento |
| `chips_banned_last_7d` | Chips banidos nos últimos 7 dias |
| `warmer_progress` | Progresso do aquecimento por chip |

### Health Check

```bash
curl http://localhost:8000/health/chips
```

## Tabelas no Banco

```sql
-- Chips/Instâncias Julia
CREATE TABLE julia_chips (
    id UUID PRIMARY KEY,
    phone_number TEXT NOT NULL,
    salvy_account_id TEXT,
    status TEXT NOT NULL,
    warmer_progress FLOAT DEFAULT 0,
    activated_at TIMESTAMPTZ,
    ready_at TIMESTAMPTZ,
    banned_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Métricas de aquecimento
CREATE TABLE chip_warmer_metrics (
    id UUID PRIMARY KEY,
    chip_id UUID REFERENCES julia_chips(id),
    day_number INT,
    messages_sent INT,
    messages_received INT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

## Referências

- Sprint 25: `planning/sprint-25/` - Julia Warmer Foundation
- Sprint 26: `planning/sprint-26/` - Multi-Julia Orchestration
- Sprint 27: `planning/sprint-27/` - Chip Activator VPS
- Salvy: `docs/integracoes/salvy-quickref.md`
