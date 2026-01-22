# Arquitetura de Campanhas

> Sprint 35 - Debt Cleanup: Módulo refatorado

## Visão Geral

O sistema de campanhas permite enviar mensagens em massa para médicos segmentados.
Campanhas são executadas através de um pipeline que:
1. Busca destinatários elegíveis
2. Gera mensagens apropriadas por tipo
3. Enfileira envios em `fila_mensagens`
4. Atualiza contadores

## Tipos de Campanha

| Tipo | Descrição | Geração de Mensagem |
|------|-----------|---------------------|
| `discovery` | Primeiro contato | Dinâmica via `obter_abertura_texto()` |
| `oferta` | Oferta de vaga específica | Template no campo `corpo` |
| `oferta_plantao` | Oferta de plantão | Template no campo `corpo` |
| `reativacao` | Reativar médico inativo | Template ou mensagem padrão |
| `followup` | Seguimento de conversa | Template ou mensagem padrão |

## Estrutura de Módulos

```
app/services/campanhas/
├── __init__.py          # Exports públicos
├── types.py             # Enums e dataclasses
├── repository.py        # CRUD de campanhas
└── executor.py          # Execução de campanhas
```

### Exports Disponíveis

```python
from app.services.campanhas import (
    # Repository
    CampanhaRepository,
    campanha_repository,
    # Executor
    CampanhaExecutor,
    campanha_executor,
    # Types
    TipoCampanha,
    StatusCampanha,
    AudienceFilters,
    CampanhaData,
)
```

## Fluxo de Execução

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Scheduler  │────>│  Executor   │────>│ Repository  │
└─────────────┘     └─────────────┘     └─────────────┘
                          │                    │
                          │                    v
                          │              ┌─────────────┐
                          │              │  Supabase   │
                          │              │ (campanhas) │
                          │              └─────────────┘
                          │
                          v
                    ┌─────────────┐
                    │ Segmentação │
                    │  Service    │
                    └─────────────┘
                          │
                          v
                    ┌─────────────┐
                    │    Fila     │
                    │  Mensagens  │
                    └─────────────┘
```

### Sequência Detalhada

1. **Scheduler** chama `campanha_executor.executar(campanha_id)`
2. **Executor** busca campanha via `campanha_repository.buscar_por_id()`
3. **Executor** valida status (AGENDADA ou ATIVA)
4. **Executor** atualiza status para ATIVA
5. **Executor** busca destinatários via `segmentacao_service`
6. Para cada destinatário:
   - Gera mensagem apropriada ao tipo
   - Enfileira via `fila_service.enfileirar()`
7. **Executor** atualiza contadores

## Tabela: campanhas

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | SERIAL | PK |
| `nome_template` | TEXT | Nome identificador |
| `tipo_campanha` | TEXT | discovery, oferta, reativacao, followup |
| `status` | TEXT | rascunho, agendada, ativa, pausada, concluida, cancelada |
| `corpo` | TEXT | Template da mensagem (opcional para discovery) |
| `tom` | TEXT | Tom da mensagem (amigavel, profissional, etc) |
| `audience_filters` | JSONB | Filtros de segmentação |
| `agendar_para` | TIMESTAMPTZ | Data/hora de execução |
| `pode_ofertar` | BOOLEAN | Se pode incluir ofertas de vagas |
| `total_destinatarios` | INT | Quantidade de destinatários |
| `enviados` | INT | Quantidade já enviada |
| `entregues` | INT | Quantidade entregue |
| `respondidos` | INT | Quantidade que respondeu |
| `created_at` | TIMESTAMPTZ | Data de criação |
| `iniciada_em` | TIMESTAMPTZ | Data de início da execução |
| `concluida_em` | TIMESTAMPTZ | Data de conclusão |

### audience_filters (JSONB)

```json
{
  "regioes": ["ABC", "SP"],
  "especialidades": ["cardiologia"],
  "quantidade_alvo": 100,
  "pressure_score_max": 70,
  "excluir_opt_out": true
}
```

## Mensagens: fila_mensagens

Mensagens são enfileiradas em `fila_mensagens` com `metadata.campanha_id`:

```python
await fila_service.enfileirar(
    cliente_id=dest["id"],
    conteudo=mensagem,
    tipo="campanha",
    prioridade=3,
    metadata={"campanha_id": str(campanha_id)}
)
```

## Views de Consulta

- `campaign_sends` - Envios por campanha (consulta `fila_mensagens`)
- `campaign_metrics` - Métricas agregadas

## Uso

### Criar Campanha

```python
from app.services.campanhas import campanha_repository
from app.services.campanhas.types import TipoCampanha, AudienceFilters

campanha = await campanha_repository.criar(
    nome_template="Discovery Cardiologistas SP",
    tipo_campanha=TipoCampanha.DISCOVERY,
    audience_filters=AudienceFilters(
        especialidades=["cardiologia"],
        regioes=["SP"],
        quantidade_alvo=100,
    ),
)
```

### Executar Campanha

```python
from app.services.campanhas import campanha_executor

sucesso = await campanha_executor.executar(campanha_id=16)
```

### Via API

```bash
# Criar
curl -X POST /campanhas/ \
  -H "Content-Type: application/json" \
  -d '{
    "nome_template": "Discovery SP",
    "tipo_campanha": "discovery",
    "especialidades": ["cardiologia"],
    "quantidade_alvo": 50
  }'

# Iniciar
curl -X POST /campanhas/16/iniciar

# Relatório
curl /campanhas/16/relatorio
```

## Decisões de Design

1. **Geração dinâmica para discovery**: Campanhas discovery usam `obter_abertura_texto()`
   para gerar mensagens únicas, evitando detecção como spam.

2. **Fila de mensagens**: Todas as mensagens vão para `fila_mensagens` para rate limiting,
   retry e tracking unificado.

3. **Separação repository/executor**: Repository para CRUD puro, Executor para lógica de
   negócio (buscar destinatários, gerar mensagens, enfileirar).

4. **Templates com placeholders**: Suporte a `{nome}` e `{{nome}}` para compatibilidade.

## Código Legado (DEPRECATED)

**NÃO usar** os seguintes módulos/funções (deprecated):

```python
# DEPRECATED - não usar
from app.services.campanha import criar_campanha_piloto  # usa colunas legadas
from app.services.campanha import executar_campanha      # usa tabela removida
```

Usar sempre o novo módulo `app.services.campanhas`.

## Testes

```bash
# Todos os testes de campanhas
uv run pytest tests/services/campanhas/ tests/api/routes/test_campanhas.py -v

# Apenas repository
uv run pytest tests/services/campanhas/test_repository.py -v

# Apenas executor
uv run pytest tests/services/campanhas/test_executor.py -v
```

## Referências

- Schema completo: `docs/arquitetura/schema-campanhas.md`
- Guia de migração: `docs/arquitetura/migracao-campanhas-codigo.md`
- Decisões técnicas: `planning/sprint-35-debt-cleanup/decisoes-tecnicas.md`
