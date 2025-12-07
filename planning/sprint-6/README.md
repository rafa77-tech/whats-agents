# Sprint 6: Multi-Instância WhatsApp

## Objetivo da Sprint

> **Escalar envio de mensagens usando múltiplas instâncias WhatsApp na Evolution API.**

Ao final desta sprint, você poderá:
- Ter 2+ números WhatsApp operando como "Júlia"
- Distribuir carga entre instâncias
- Rate limit por instância (não global)
- Fallback automático se uma instância cair

---

## Por que Multi-Instância?

| Problema | Solução |
|----------|---------|
| Rate limit de 100 msgs/dia limita escala | 3 instâncias = 300 msgs/dia |
| Ban de um número = sistema parado | Outras instâncias continuam |
| Warm-up lento de novo número | Números já aquecidos em paralelo |

---

## Pré-requisitos

- [ ] Sprint 1-5 completas e estáveis
- [ ] 2+ números WhatsApp disponíveis
- [ ] Números já verificados e com warm-up básico

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Instâncias ativas | 2+ |
| Distribuição de carga | Balanceada (±10%) |
| Failover automático | < 30 segundos |
| Médico sempre fala com mesmo número | 100% (sticky) |

---

## Epics

| Epic | Nome | Stories | Prioridade |
|------|------|---------|------------|
| E1 | [Gerenciamento de Instâncias](./epic-01-instancias.md) | 4 | P0 |
| E2 | [Distribuição de Carga](./epic-02-distribuicao.md) | 3 | P0 |
| E3 | [Monitoramento](./epic-03-monitoramento.md) | 2 | P1 |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      MULTI-INSTÂNCIA                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────────────────────────┐   │
│  │   FastAPI    │───▶│      Instance Manager            │   │
│  └──────────────┘    │  ┌────────────────────────────┐  │   │
│                      │  │ escolher_instancia()       │  │   │
│                      │  │ - Sticky por médico        │  │   │
│                      │  │ - Round-robin se novo      │  │   │
│                      │  │ - Fallback se indisponível │  │   │
│                      │  └────────────────────────────┘  │   │
│                      └──────────────────────────────────┘   │
│                                   │                          │
│              ┌────────────────────┼────────────────────┐    │
│              ▼                    ▼                    ▼    │
│     ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│     │  Revoluna   │      │  Revoluna2  │      │  Revoluna3  │
│     │  (Primary)  │      │ (Secondary) │      │  (Backup)   │
│     │ 20/h, 100/d │      │ 20/h, 100/d │      │ 20/h, 100/d │
│     └─────────────┘      └─────────────┘      └─────────────┘
│           │                    │                    │        │
│           ▼                    ▼                    ▼        │
│     ┌─────────────────────────────────────────────────────┐ │
│     │                  Evolution API                       │ │
│     └─────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Estratégias de Distribuição

### 1. Sticky (Recomendado para MVP)
```python
# Médico sempre fala com mesma instância
instancia = medico.get("instancia_preferida") or escolher_nova()
```

**Vantagem:** Médico não estranha trocar de número
**Desvantagem:** Pode desbalancear se médicos concentrarem em uma instância

### 2. Round-Robin
```python
# Distribui igualmente entre instâncias
instancia = instancias[contador % len(instancias)]
```

**Vantagem:** Distribuição perfeita
**Desvantagem:** Médico pode receber de números diferentes

### 3. Por Especialidade
```python
# Cada especialidade tem sua instância
mapa = {"anestesiologia": "Revoluna", "cardiologia": "Revoluna2"}
instancia = mapa.get(medico.especialidade, "Revoluna")
```

**Vantagem:** Segmentação clara
**Desvantagem:** Desbalanceamento se especialidades têm tamanhos diferentes

### 4. Híbrido (Recomendado para Produção)
```python
# Sticky + fallback + rebalanceamento
instancia = medico.instancia_preferida
if not instancia_disponivel(instancia):
    instancia = escolher_menos_carregada()
    atualizar_preferencia(medico, instancia)
```

---

## Ordem de Execução

```
Dia 1-2:
├── E1.1 - Modelo de instâncias no banco
├── E1.2 - Gerenciador de instâncias
└── E1.3 - Health check de instâncias

Dia 3-4:
├── E2.1 - Estratégia sticky
├── E2.2 - Fallback automático
└── E2.3 - Rate limit por instância

Dia 5:
├── E3.1 - Dashboard de status
└── E3.2 - Alertas de instância down
```

---

## Configuração

```python
# app/core/config.py

# Multi-instância (lista separada por vírgula)
EVOLUTION_INSTANCES: str = "Revoluna,Revoluna2,Revoluna3"

# Estratégia de distribuição
INSTANCE_STRATEGY: str = "sticky"  # sticky, round_robin, by_specialty
```

```env
# .env
EVOLUTION_INSTANCES=Revoluna,Revoluna2,Revoluna3
INSTANCE_STRATEGY=sticky
```

---

## Tabela no Banco

```sql
-- Já existe: whatsapp_instances
-- Campos relevantes:
-- - nome (Revoluna, Revoluna2, etc)
-- - numero_telefone
-- - status (connected, disconnected, banned)
-- - msgs_enviadas_hoje
-- - ultima_msg_at

-- Adicionar na tabela clientes:
ALTER TABLE clientes
ADD COLUMN instancia_preferida VARCHAR(50) REFERENCES whatsapp_instances(nome);
```

---

## Definition of Done (Sprint)

A sprint só está completa quando:

- [ ] 2+ instâncias configuradas na Evolution
- [ ] Todas as instâncias aparecem no health check
- [ ] Médico novo é atribuído a instância com menor carga
- [ ] Médico existente mantém mesma instância (sticky)
- [ ] Se instância cai, médico é migrado automaticamente
- [ ] Rate limit funciona por instância
- [ ] Dashboard mostra status de todas as instâncias
- [ ] Alerta dispara quando instância fica offline

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Médico estranha número diferente | Média | Alto | Usar sticky, só trocar se necessário |
| Números novos são banidos | Alta | Alto | Warm-up gradual antes de usar |
| Complexidade de debug | Média | Médio | Logs com instância em cada linha |
| Desbalanceamento | Baixa | Baixo | Rebalanceamento periódico |

---

## Próximos Passos

1. Aguardar conclusão das Sprints 1-5
2. Adquirir 2 números WhatsApp adicionais
3. Fazer warm-up dos números (1-2 semanas)
4. Implementar Epic 1: Gerenciamento de Instâncias
