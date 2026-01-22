# Módulo de Campanhas

> Sprint 35 - Debt Cleanup

## Estrutura

```
campanhas/
├── __init__.py      # Exports: campanha_repository, campanha_executor
├── types.py         # TipoCampanha, StatusCampanha, CampanhaData, AudienceFilters
├── repository.py    # CampanhaRepository - CRUD
├── executor.py      # CampanhaExecutor - Execução
└── README.md        # Este arquivo
```

## Uso Rápido

```python
# Criar campanha
from app.services.campanhas import campanha_repository
from app.services.campanhas.types import TipoCampanha, AudienceFilters

campanha = await campanha_repository.criar(
    nome_template="Minha Campanha",
    tipo_campanha=TipoCampanha.DISCOVERY,
    audience_filters=AudienceFilters(
        especialidades=["cardiologia"],
        quantidade_alvo=50,
    ),
)

# Executar
from app.services.campanhas import campanha_executor

await campanha_executor.executar(campanha.id)
```

## Tipos de Campanha

| Tipo | Geração de Mensagem |
|------|---------------------|
| `discovery` | Dinâmica via `obter_abertura_texto()` |
| `oferta` | Template no campo `corpo` |
| `oferta_plantao` | Template no campo `corpo` |
| `reativacao` | Template ou mensagem padrão |
| `followup` | Template ou mensagem padrão |

## Repository

```python
from app.services.campanhas import campanha_repository

# Buscar
campanha = await campanha_repository.buscar_por_id(16)

# Listar
agendadas = await campanha_repository.listar_agendadas()
ativas = await campanha_repository.listar_ativas()

# Criar
campanha = await campanha_repository.criar(
    nome_template="Nova Campanha",
    tipo_campanha=TipoCampanha.OFERTA,
    corpo="Oi {nome}! Temos uma vaga para você.",
)

# Atualizar
await campanha_repository.atualizar_status(16, StatusCampanha.ATIVA)
await campanha_repository.incrementar_enviados(16, 10)
```

## Executor

```python
from app.services.campanhas import campanha_executor

# Executar campanha completa
sucesso = await campanha_executor.executar(campanha_id=16)
```

O executor:
1. Busca a campanha
2. Valida status (deve ser AGENDADA ou ATIVA)
3. Busca destinatários via segmentação
4. Gera mensagens apropriadas ao tipo
5. Enfileira em `fila_mensagens`
6. Atualiza contadores

## Types

```python
from app.services.campanhas.types import (
    TipoCampanha,      # Enum: DISCOVERY, OFERTA, OFERTA_PLANTAO, REATIVACAO, FOLLOWUP
    StatusCampanha,    # Enum: RASCUNHO, AGENDADA, ATIVA, PAUSADA, CONCLUIDA, CANCELADA
    AudienceFilters,   # Dataclass: regioes, especialidades, quantidade_alvo
    CampanhaData,      # Dataclass: todos os campos da campanha
)
```

## Testes

```bash
# Todos os testes
uv run pytest tests/services/campanhas/ -v

# Apenas repository
uv run pytest tests/services/campanhas/test_repository.py -v

# Apenas executor
uv run pytest tests/services/campanhas/test_executor.py -v
```

## Documentação

- Arquitetura: `docs/arquitetura/campanhas.md`
- Schema do banco: `docs/arquitetura/schema-campanhas.md`
- Guia de migração: `docs/arquitetura/migracao-campanhas-codigo.md`
