# EPICO 1: Infraestrutura CNES

## Contexto

O CNES (Cadastro Nacional de Estabelecimentos de Saude) e a base oficial do governo brasileiro com ~400k estabelecimentos de saude. Dados publicos via DataSUS. Ao importar localmente, o pipeline pode fazer lookup instantaneo sem custo por request.

**Objetivo:** Criar tabela CNES local, importar dados relevantes de SP, e disponibilizar RPC de busca por similaridade.

## Escopo

- **Incluido:**
  - Migration da tabela `cnes_estabelecimentos` com indices pg_trgm
  - Migration das colunas de enriquecimento na tabela `hospitais`
  - RPC `buscar_cnes_por_nome` com pg_trgm
  - Importacao de dados CNES via API publica ou CSV DataSUS
  - Servico Python `hospital_cnes.py` para lookup

- **Excluido:**
  - Importacao de outros estados alem de SP (fase 1)
  - Atualizacao automatica periodica dos dados CNES (futuro)
  - Interface de busca CNES no dashboard

---

## Tarefa 1.1: Migration — Tabela CNES e Colunas de Enriquecimento

### Objetivo

Criar a tabela `cnes_estabelecimentos` para armazenar dados do CNES e adicionar colunas de enriquecimento na tabela `hospitais`.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MIGRATION | `add_cnes_estabelecimentos_table` — via `mcp__supabase__apply_migration` |
| MIGRATION | `add_hospital_enrichment_columns` — via `mcp__supabase__apply_migration` |

### Implementacao

**Migration 1 — Tabela CNES:**

```sql
CREATE TABLE IF NOT EXISTS cnes_estabelecimentos (
    cnes_codigo TEXT PRIMARY KEY,
    cnpj TEXT,
    razao_social TEXT NOT NULL,
    nome_fantasia TEXT,
    tipo_unidade TEXT,
    logradouro TEXT,
    numero TEXT,
    bairro TEXT,
    cidade TEXT NOT NULL,
    uf TEXT NOT NULL,
    cep TEXT,
    telefone TEXT,
    latitude NUMERIC,
    longitude NUMERIC,
    ativo BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_cnes_nome_fantasia_trgm ON cnes_estabelecimentos
  USING gin (nome_fantasia gin_trgm_ops);
CREATE INDEX idx_cnes_razao_social_trgm ON cnes_estabelecimentos
  USING gin (razao_social gin_trgm_ops);
CREATE INDEX idx_cnes_cidade_uf ON cnes_estabelecimentos (cidade, uf);
CREATE INDEX idx_cnes_tipo_unidade ON cnes_estabelecimentos (tipo_unidade);
```

**Migration 2 — Colunas de enriquecimento:**

```sql
ALTER TABLE hospitais ADD COLUMN IF NOT EXISTS cnes_codigo TEXT;
ALTER TABLE hospitais ADD COLUMN IF NOT EXISTS google_place_id TEXT;
ALTER TABLE hospitais ADD COLUMN IF NOT EXISTS telefone TEXT;
ALTER TABLE hospitais ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;
ALTER TABLE hospitais ADD COLUMN IF NOT EXISTS enriched_by TEXT;

CREATE INDEX idx_hospitais_cnes_codigo ON hospitais (cnes_codigo)
  WHERE cnes_codigo IS NOT NULL;
CREATE INDEX idx_hospitais_google_place_id ON hospitais (google_place_id)
  WHERE google_place_id IS NOT NULL;
```

### Definition of Done

- [ ] Tabela `cnes_estabelecimentos` criada com indices
- [ ] Colunas `cnes_codigo`, `google_place_id`, `telefone`, `enriched_at`, `enriched_by` adicionadas em `hospitais`
- [ ] Indices parciais criados

---

## Tarefa 1.2: RPC de Busca CNES

### Objetivo

Criar funcao SQL para buscar estabelecimentos CNES por nome usando pg_trgm, com filtro opcional de cidade e UF.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MIGRATION | `add_rpc_buscar_cnes_por_nome` — via `mcp__supabase__apply_migration` |

### Implementacao

```sql
CREATE OR REPLACE FUNCTION buscar_cnes_por_nome(
    p_nome TEXT,
    p_cidade TEXT DEFAULT NULL,
    p_uf TEXT DEFAULT 'SP',
    p_limite INT DEFAULT 5
) RETURNS TABLE(
    cnes_codigo TEXT,
    nome_fantasia TEXT,
    razao_social TEXT,
    cidade TEXT,
    uf TEXT,
    logradouro TEXT,
    numero TEXT,
    bairro TEXT,
    cep TEXT,
    telefone TEXT,
    latitude NUMERIC,
    longitude NUMERIC,
    score FLOAT
)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.cnes_codigo,
        e.nome_fantasia,
        e.razao_social,
        e.cidade,
        e.uf,
        e.logradouro,
        e.numero,
        e.bairro,
        e.cep,
        e.telefone,
        e.latitude,
        e.longitude,
        GREATEST(
            similarity(COALESCE(lower(e.nome_fantasia), ''), lower(p_nome)),
            similarity(lower(e.razao_social), lower(p_nome))
        )::FLOAT AS score
    FROM cnes_estabelecimentos e
    WHERE e.ativo = true
      AND (p_cidade IS NULL OR lower(e.cidade) = lower(p_cidade))
      AND lower(e.uf) = lower(p_uf)
      AND (
          COALESCE(e.nome_fantasia, '') % p_nome
          OR e.razao_social % p_nome
      )
    ORDER BY score DESC
    LIMIT p_limite;
END;
$$;
```

### Definition of Done

- [ ] RPC criada e funcional
- [ ] Retorna matches corretos para hospitais conhecidos (testar com `buscar_cnes_por_nome('Hospital Sao Luiz', NULL, 'SP', 5)`)

---

## Tarefa 1.3: Importacao de Dados CNES

### Objetivo

Importar dados do CNES para a tabela local. Fonte: API publica CNES ou CSV do DataSUS. Filtrar tipos relevantes (hospitais, UPAs, UBSs, clinicas). Foco em SP na fase 1.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | Script de importacao (executado uma vez, nao precisa ser arquivo permanente) |

### Implementacao

**Fonte de dados:** API CNES publica `https://cnes.datasus.gov.br/` ou download CSV.

**Alternativa pragmatica:** Usar a API do CNES via endpoint publico:
- `https://apidadosabertos.saude.gov.br/cnes/estabelecimentos` (paginado)

**Tipos a filtrar:**
- HOSPITAL GERAL
- HOSPITAL ESPECIALIZADO
- PRONTO SOCORRO GERAL
- PRONTO SOCORRO ESPECIALIZADO
- UNIDADE DE PRONTO ATENDIMENTO
- UNIDADE BASICA DE SAUDE
- CENTRO DE SAUDE/UNIDADE BASICA
- CLINICA/CENTRO DE ESPECIALIDADE
- POLICLINICA
- UNIDADE MISTA
- HOSPITAL/DIA — ISOLADO

**Estrategia:** Importar via `execute_sql` em batches de 500 registros. Se API publica nao estiver disponivel, usar CSV do DataSUS ou gerar dados via scraping da API.

**Estimativa:** ~5.000-15.000 registros para SP apos filtro de tipo.

### Definition of Done

- [ ] Tabela `cnes_estabelecimentos` populada com >= 5.000 registros de SP
- [ ] Dados incluem nome_fantasia, razao_social, endereco, cidade, uf
- [ ] `SELECT COUNT(*) FROM cnes_estabelecimentos WHERE uf = 'SP';` retorna > 5000

---

## Tarefa 1.4: Servico Python — hospital_cnes.py

### Objetivo

Criar servico de lookup CNES que encapsula a chamada RPC e converte dados para uso no pipeline.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `app/services/grupos/hospital_cnes.py` (~100 linhas) |

### Implementacao

```python
"""
Lookup de hospitais na base CNES local.

Sprint 61 - Epico 1: Busca por similaridade na tabela cnes_estabelecimentos.
"""

from dataclasses import dataclass
from typing import Optional

from app.core.logging import get_logger
from app.services.supabase import supabase

logger = get_logger(__name__)

SCORE_MINIMO_CNES = 0.4


@dataclass
class InfoCNES:
    """Dados de um estabelecimento CNES."""

    cnes_codigo: str
    nome_oficial: str
    cidade: str
    estado: str
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    score: float = 0.0


async def buscar_hospital_cnes(
    nome: str,
    cidade: Optional[str] = None,
    estado: str = "SP",
) -> Optional[InfoCNES]:
    """
    Busca hospital na tabela CNES local.

    Tenta primeiro com filtro de cidade. Se nao encontrar, busca sem filtro.
    Retorna melhor match com score >= SCORE_MINIMO_CNES.
    """
    # Tentativa 1: com cidade
    if cidade and cidade != "Nao informada":
        info = await _buscar_cnes_rpc(nome, cidade, estado)
        if info:
            return info

    # Tentativa 2: sem cidade
    info = await _buscar_cnes_rpc(nome, None, estado)
    return info


async def _buscar_cnes_rpc(
    nome: str,
    cidade: Optional[str],
    estado: str,
) -> Optional[InfoCNES]:
    """Chama RPC buscar_cnes_por_nome e retorna melhor match."""
    try:
        result = supabase.rpc(
            "buscar_cnes_por_nome",
            {
                "p_nome": nome,
                "p_cidade": cidade,
                "p_uf": estado,
                "p_limite": 1,
            },
        ).execute()

        if not result.data:
            return None

        row = result.data[0]
        if row["score"] < SCORE_MINIMO_CNES:
            return None

        return InfoCNES(
            cnes_codigo=row["cnes_codigo"],
            nome_oficial=row["nome_fantasia"] or row["razao_social"],
            cidade=row["cidade"],
            estado=row["uf"],
            logradouro=row.get("logradouro"),
            numero=row.get("numero"),
            bairro=row.get("bairro"),
            cep=row.get("cep"),
            telefone=row.get("telefone"),
            latitude=float(row["latitude"]) if row.get("latitude") else None,
            longitude=float(row["longitude"]) if row.get("longitude") else None,
            score=row["score"],
        )

    except Exception as e:
        logger.warning(f"Erro ao buscar CNES: {e}", extra={"nome": nome})
        return None
```

### Testes Obrigatorios

**Unitarios:**
- [ ] `buscar_hospital_cnes` retorna InfoCNES quando RPC retorna match
- [ ] `buscar_hospital_cnes` retorna None quando score < 0.4
- [ ] `buscar_hospital_cnes` tenta sem cidade quando primeira busca falha
- [ ] `buscar_hospital_cnes` retorna None quando RPC retorna vazio

### Definition of Done

- [ ] Arquivo `hospital_cnes.py` criado
- [ ] `InfoCNES` dataclass com todos os campos
- [ ] `buscar_hospital_cnes()` funcional com fallback cidade -> sem cidade
- [ ] Testes unitarios passando

---

## Dependencias

Nenhuma — este e o primeiro epico da sprint.

## Risco: MEDIO

Dados CNES podem nao estar disponiveis via API publica no momento da importacao. Mitigacao: CSV do DataSUS como alternativa, ou scraping manual se necessario.
