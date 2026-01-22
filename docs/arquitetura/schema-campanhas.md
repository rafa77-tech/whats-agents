# Schema: Tabela campanhas

> Atualizado em: 2026-01-22
> Sprint: 35

## Colunas

| Coluna | Tipo | Nullable | Default | Descricao |
|--------|------|----------|---------|-----------|
| `id` | bigint | NO | auto-increment | PK |
| `nome_template` | text | YES | - | Nome/titulo da campanha |
| `categoria` | text | YES | - | Categoria (marketing, etc) |
| `idioma` | text | YES | - | Idioma (pt-BR, etc) |
| `corpo` | text | YES | - | Template da mensagem ou descricao |
| `tom` | text | YES | - | Tom a usar (amigavel, formal) |
| `tipo_campanha` | text | YES | 'oferta_plantao' | discovery, oferta, reativacao, followup |
| `aprovado_meta` | boolean | YES | true | Aprovado pela Meta (WhatsApp Business) |
| `data_aprovacao_meta` | timestamptz | YES | - | Data da aprovacao |
| `pressure_points` | integer | YES | 25 | Pontos que adiciona ao pressure_score |
| `ativo` | boolean | YES | true | Se esta ativa |
| `created_at` | timestamptz | YES | now() | Data de criacao |
| `updated_at` | timestamptz | YES | now() | Data de atualizacao |
| `objetivo` | text | YES | - | Objetivo da campanha |
| `hipotese` | text | YES | - | Hipotese a testar |
| `kpi_primaria` | text | YES | - | KPI principal |
| `kpi_secundaria` | text | YES | - | KPI secundaria |
| `playbook_versao` | text | YES | - | Versao do playbook usado |
| `meta_status` | text | YES | - | Status na Meta |
| `meta_error_reason` | text | YES | - | Motivo de erro na Meta |
| `status` | text | YES | 'rascunho' | rascunho, agendada, ativa, concluida, pausada |
| `agendar_para` | timestamptz | YES | - | Quando iniciar |
| `iniciada_em` | timestamptz | YES | - | Quando iniciou |
| `concluida_em` | timestamptz | YES | - | Quando concluiu |
| `audience_filters` | jsonb | YES | '{}' | Filtros de segmentacao |
| `created_by` | text | YES | - | Quem criou |
| `started_at` | timestamptz | YES | - | Alias de iniciada_em |
| `completed_at` | timestamptz | YES | - | Alias de concluida_em |
| `total_destinatarios` | integer | YES | 0 | Total de alvos |
| `enviados` | integer | YES | 0 | Quantidade enviada |
| `entregues` | integer | YES | 0 | Quantidade entregue |
| `respondidos` | integer | YES | 0 | Quantidade que respondeu |
| `escopo_vagas` | jsonb | YES | - | Vagas relacionadas |
| `regras` | jsonb | YES | - | Regras de envio |
| `pode_ofertar` | boolean | YES | false | Se pode ofertar vagas |

## Formato audience_filters

```json
{
  "regioes": ["ABC", "Capital"],
  "especialidades": ["cardiologia", "anestesiologia"],
  "quantidade_alvo": 50,
  "pressure_score_max": 70,
  "excluir_opt_out": true
}
```

## Status Possiveis

| Status | Descricao |
|--------|-----------|
| `rascunho` | Criada mas nao agendada |
| `agendada` | Agendada para execucao futura |
| `ativa` | Em execucao |
| `pausada` | Pausada temporariamente |
| `concluida` | Finalizada |
| `cancelada` | Cancelada |

## Tipos de Campanha

| Tipo | Descricao | Geracao de Mensagem |
|------|-----------|---------------------|
| `discovery` | Primeiro contato, conhecer medico | Dinamica via `obter_abertura_texto()` |
| `oferta` | Oferecer vaga especifica | Template com dados da vaga (`corpo`) |
| `reativacao` | Retomar contato apos inatividade | Template de reativacao (`corpo`) |
| `followup` | Acompanhamento | Template de followup (`corpo`) |

---

## Colunas que NAO EXISTEM (codigo legado)

| Coluna Legada | Usar Em Vez |
|---------------|-------------|
| `nome` | `nome_template` |
| `tipo` | `tipo_campanha` |
| `mensagem_template` | `corpo` ou geracao dinamica |
| `config` | `audience_filters` |
| `filtro_especialidades` | `audience_filters.especialidades` |
| `filtro_regioes` | `audience_filters.regioes` |
| `envios_criados` | `enviados` |
| `finalizada_em` | `concluida_em` ou `completed_at` |

---

## Tabelas Removidas

### envios_campanha (REMOVIDA)

Esta tabela foi removida do banco. O codigo ainda referencia em:

| Arquivo | Funcao | Status |
|---------|--------|--------|
| `app/services/campanha.py` | `pode_enviar_primeiro_contato()` | Deprecated |
| `app/services/campanha.py` | `criar_campanha_piloto()` | Deprecated |
| `app/services/campanha.py` | `executar_campanha()` | Deprecated |
| `app/services/campanha.py` | `enviar_mensagem_prospeccao()` | Deprecated |

**Substituicao:** Usar `fila_mensagens` com `metadata.campanha_id` via `fila_service.enfileirar()`.

---

## Views (Usar Estas!)

### campaign_sends

View unificada de envios de campanha. Fonte: `fila_mensagens`.

```sql
SELECT
    send_id,
    cliente_id,
    campaign_id,
    send_type,
    queue_status,
    outcome,
    outcome_reason_code,
    provider_message_id,
    queued_at,
    scheduled_for,
    sent_at,
    outcome_at,
    source_table
FROM campaign_sends
WHERE campaign_id = 16;
```

### campaign_metrics

Metricas agregadas por campanha.

```sql
SELECT
    campaign_id,
    total_sends,
    delivered,
    bypassed,
    blocked,
    failed,
    pending,
    delivery_rate,
    block_rate
FROM campaign_metrics
WHERE campaign_id = 16;
```

### campaign_sends_raw

View de baixo nivel com dados brutos dos envios.

### Quando Usar

| Operacao | Usar |
|----------|------|
| Criar envio | `fila_service.enfileirar()` com `metadata.campanha_id` |
| Listar envios | View `campaign_sends` |
| Metricas | View `campaign_metrics` |
| Status individual | `fila_mensagens` direto |
