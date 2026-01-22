# Epic 02: Mapeamento Schema

## Objetivo

Criar documento de referencia mapeando todas as diferencas entre o codigo atual e o schema real do banco.

## Contexto

O codigo foi escrito para um schema antigo (epoca do Twilio). O banco evoluiu mas o codigo nao acompanhou. Este epico documenta todas as diferencas para guiar a refatoracao.

---

## Story 2.1: Documentar Schema Real da Tabela campanhas

### Objetivo

Criar arquivo de referencia com o schema atual da tabela `campanhas`.

### Tarefas

1. **Criar arquivo** `docs/arquitetura/schema-campanhas.md`:

```markdown
# Schema: Tabela campanhas

> Atualizado em: 2026-01-21
> Sprint: 35

## Colunas

| Coluna | Tipo | Nullable | Descricao |
|--------|------|----------|-----------|
| `id` | bigint | NO | PK auto-increment |
| `nome_template` | text | YES | Nome/titulo da campanha |
| `categoria` | text | YES | Categoria (marketing, etc) |
| `idioma` | text | YES | Idioma (pt-BR, etc) |
| `corpo` | text | YES | Template da mensagem ou descricao |
| `tom` | text | YES | Tom a usar (amigavel, formal) |
| `tipo_campanha` | text | YES | discovery, oferta, reativacao, followup |
| `aprovado_meta` | boolean | YES | Aprovado pela Meta (WhatsApp Business) |
| `data_aprovacao_meta` | timestamptz | YES | Data da aprovacao |
| `pressure_points` | integer | YES | Pontos que adiciona ao pressure_score |
| `ativo` | boolean | YES | Se esta ativa |
| `created_at` | timestamptz | YES | Data de criacao |
| `updated_at` | timestamptz | YES | Data de atualizacao |
| `objetivo` | text | YES | Objetivo da campanha |
| `hipotese` | text | YES | Hipotese a testar |
| `kpi_primaria` | text | YES | KPI principal |
| `kpi_secundaria` | text | YES | KPI secundaria |
| `playbook_versao` | text | YES | Versao do playbook usado |
| `meta_status` | text | YES | Status na Meta |
| `meta_error_reason` | text | YES | Motivo de erro na Meta |
| `status` | text | YES | rascunho, agendada, ativa, concluida, pausada |
| `agendar_para` | timestamptz | YES | Quando iniciar |
| `iniciada_em` | timestamptz | YES | Quando iniciou |
| `concluida_em` | timestamptz | YES | Quando concluiu |
| `audience_filters` | jsonb | YES | Filtros de segmentacao |
| `created_by` | text | YES | Quem criou |
| `started_at` | timestamptz | YES | Alias de iniciada_em |
| `completed_at` | timestamptz | YES | Alias de concluida_em |
| `total_destinatarios` | integer | YES | Total de alvos |
| `enviados` | integer | YES | Quantidade enviada |
| `entregues` | integer | YES | Quantidade entregue |
| `respondidos` | integer | YES | Quantidade que respondeu |
| `escopo_vagas` | jsonb | YES | Vagas relacionadas |
| `regras` | jsonb | YES | Regras de envio |
| `pode_ofertar` | boolean | YES | Se pode ofertar vagas |

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
| `discovery` | Primeiro contato, conhecer medico | Dinamica via `obter_abertura()` |
| `oferta` | Oferecer vaga especifica | Template com dados da vaga |
| `reativacao` | Retomar contato apos inatividade | Template de reativacao |
| `followup` | Acompanhamento | Template de followup |

## Colunas que NAO EXISTEM (codigo legado)

| Coluna Legada | Usar Em Vez |
|---------------|-------------|
| `nome` | `nome_template` |
| `tipo` | `tipo_campanha` |
| `mensagem_template` | `corpo` ou geracao dinamica |
| `config` | `audience_filters` |
| `envios_criados` | `enviados` |
| `finalizada_em` | `concluida_em` ou `completed_at` |
```

### DoD

- [ ] Arquivo `docs/arquitetura/schema-campanhas.md` criado
- [ ] Todas as colunas documentadas
- [ ] Formato de `audience_filters` documentado
- [ ] Colunas legadas listadas com substitutos

---

## Story 2.2: Documentar Tabelas Removidas

### Objetivo

Documentar tabelas que foram removidas do banco mas ainda tem referencias no codigo.

### Tarefas

1. **Adicionar secao ao arquivo** `docs/arquitetura/schema-campanhas.md`:

```markdown
## Tabelas Removidas

### envios_campanha (REMOVIDA)

Esta tabela foi removida do banco. O codigo ainda referencia em:

| Arquivo | Linha | Funcao |
|---------|-------|--------|
| `app/services/campanha.py` | 52 | `pode_enviar_primeiro_contato()` |
| `app/services/campanha.py` | 66 | `pode_enviar_primeiro_contato()` |
| `app/services/campanha.py` | 157 | `criar_campanha_piloto()` |
| `app/services/campanha.py` | 184 | `executar_campanha()` |
| `app/services/campanha.py` | 222 | `executar_campanha()` |
| `app/services/campanha.py` | 232 | `executar_campanha()` |
| `app/services/campanha.py` | 246 | `executar_campanha()` |
| `app/services/campanha.py` | 395 | `enviar_mensagem_prospeccao()` |
| `app/api/routes/piloto.py` | 32 | endpoint piloto |

**Substituicao:** Usar `fila_mensagens` com `metadata.campanha_id`.

### campanhas_deprecated (EXISTE - BACKUP)

Tabela de backup para campanhas antigas. Nao usar em codigo novo.
```

### DoD

- [ ] Tabelas removidas documentadas
- [ ] Referencias no codigo listadas
- [ ] Substituicao indicada

---

## Story 2.3: Documentar Views Existentes

### Objetivo

Documentar as views que ja existem e devem ser usadas.

### Tarefas

1. **Adicionar secao ao arquivo** `docs/arquitetura/schema-campanhas.md`:

```markdown
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

### Quando Usar

| Operacao | Usar |
|----------|------|
| Criar envio | `fila_service.enfileirar()` com `metadata.campanha_id` |
| Listar envios | View `campaign_sends` |
| Metricas | View `campaign_metrics` |
| Status individual | `fila_mensagens` direto |
```

### DoD

- [ ] Views documentadas
- [ ] Exemplos de queries incluidos
- [ ] Quando usar cada uma explicado

---

## Story 2.4: Criar Tabela de Migracao de Codigo

### Objetivo

Criar tabela de referencia rapida para migracao de codigo.

### Tarefas

1. **Criar arquivo** `docs/arquitetura/migracao-campanhas-codigo.md`:

```markdown
# Migracao de Codigo: Campanhas

> Guia rapido para atualizar codigo legado

## Tabela de Substituicao

### Colunas

| Codigo Antigo | Codigo Novo |
|---------------|-------------|
| `campanha["nome"]` | `campanha["nome_template"]` |
| `campanha["tipo"]` | `campanha["tipo_campanha"]` |
| `campanha["mensagem_template"]` | Ver "Geracao de Mensagem" |
| `campanha.get("config", {})` | `campanha.get("audience_filters", {})` |
| `config["filtro_especialidades"]` | `config["especialidades"]` |
| `config["filtro_regioes"]` | `config["regioes"]` |
| `campanha["envios_criados"]` | `campanha["enviados"]` |
| `campanha["finalizada_em"]` | `campanha["concluida_em"]` |

### Tabelas

| Codigo Antigo | Codigo Novo |
|---------------|-------------|
| `supabase.table("envios_campanha")` | `fila_service.enfileirar()` |
| `supabase.table("envios_campanha").select()` | `campaign_sends` view |
| Metricas manuais | `campaign_metrics` view |

### Geracao de Mensagem

```python
# ANTIGO (NAO FUNCIONA)
mensagem = campanha["mensagem_template"].format(nome=nome)

# NOVO - Para discovery
from app.services.abertura import obter_abertura_texto
mensagem = await obter_abertura_texto(cliente_id, nome)

# NOVO - Para outros tipos
corpo = campanha.get("corpo", "")
if "{nome}" in corpo:
    mensagem = corpo.format(nome=nome, especialidade=especialidade)
else:
    mensagem = corpo
```

### Imports Necessarios

```python
# Remover (deprecated)
# from app.services.campanha import ...  # se usar funcoes legadas

# Adicionar
from app.services.abertura import obter_abertura_texto
from app.services.fila import fila_service
```

## Checklist de Migracao

Para cada arquivo que usa campanhas:

- [ ] Substituir acesso a colunas legadas
- [ ] Remover referencias a `envios_campanha`
- [ ] Usar `fila_service` para enfileirar
- [ ] Usar views para queries
- [ ] Testar funcionalidade
```

### DoD

- [ ] Arquivo `docs/arquitetura/migracao-campanhas-codigo.md` criado
- [ ] Tabela de substituicao completa
- [ ] Exemplos de codigo incluidos
- [ ] Checklist de migracao

---

## Checklist do Epico

- [ ] **S35.E02.1** - Schema de campanhas documentado
- [ ] **S35.E02.2** - Tabelas removidas documentadas
- [ ] **S35.E02.3** - Views documentadas
- [ ] **S35.E02.4** - Guia de migracao criado

### Arquivos Criados

- `docs/arquitetura/schema-campanhas.md`
- `docs/arquitetura/migracao-campanhas-codigo.md`

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 2.1 Schema campanhas | 20min |
| 2.2 Tabelas removidas | 15min |
| 2.3 Views | 15min |
| 2.4 Guia migracao | 20min |
| **Total** | **1h10min** |
