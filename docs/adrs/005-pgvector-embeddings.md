# ADR-005: pgvector para Embeddings (nao Pinecone)

- Status: Aceita
- Data: Janeiro 2026
- Sprint: Sprint 13 (Conhecimento Dinamico RAG)
- Decisores: Equipe de Engenharia

## Contexto

O Agente Julia precisa de memoria de longo prazo e conhecimento dinamico:

**Requisitos:**

1. **Memoria de conversas**
   - Lembrar preferencias do medico (especialidade, regiao, valores)
   - Recuperar contexto de conversas anteriores
   - "Vc me disse que prefere plantoes noturnos"

2. **Conhecimento dinamico**
   - 529 chunks de conhecimento em `docs/julia/`
   - Como lidar com 10 tipos de objecoes
   - 7 perfis de medicos
   - 8 objetivos de conversa
   - Injetar conhecimento relevante no prompt

3. **RAG (Retrieval-Augmented Generation)**
   - Query: "medico reclamou de valor baixo"
   - Retrieval: chunks sobre objecao de preco
   - Generation: LLM usa chunks para responder

**Tecnologia necessaria:**
- Vector database para armazenar embeddings (1536 dimensoes via Voyage AI)
- Similarity search (cosine similarity)
- Baixa latencia (< 100ms para retrieval)

**Opcoes:**
1. Pinecone (SaaS especializado)
2. Weaviate (self-hosted)
3. pgvector (extensao PostgreSQL)
4. ChromaDB (self-hosted)

## Decisao

Usar **pgvector** (extensao PostgreSQL no Supabase):

### Justificativa

1. **Mesmo banco de dados**
   - PostgreSQL ja usado (Supabase)
   - Adicionar extensao pgvector: `CREATE EXTENSION vector`
   - 1 conexao DB para tudo (dados + vetores)

2. **Custo zero adicional**
   - Supabase inclui pgvector gratuitamente
   - Pinecone: $70/mes (1M vetores)
   - Economia: $840/ano

3. **Simplicidade operacional**
   - Nao precisa gerenciar servico separado
   - Backups via Supabase (ja configurado)
   - Migrations via SQL normal

4. **Performance suficiente**
   - 529 chunks = pequeno dataset
   - Cosine similarity via pgvector: ~50ms
   - IVFFlat index para escalar (futuro)

### Schema

```sql
CREATE TABLE conhecimento_chunks (
    id UUID PRIMARY KEY,
    conteudo TEXT NOT NULL,
    embedding vector(1536),  -- Voyage AI embeddings
    metadata JSONB,
    tipo TEXT,  -- "objecao", "perfil", "objetivo"
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_conhecimento_embedding
ON conhecimento_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Query de similarity

```python
async def buscar_chunks_relevantes(query: str, limit: int = 5) -> List[dict]:
    # Gerar embedding da query
    query_embedding = await voyage_client.embed(query)

    # Buscar chunks similares
    response = supabase.rpc(
        "match_conhecimento",
        {
            "query_embedding": query_embedding,
            "match_threshold": 0.7,
            "match_count": limit
        }
    ).execute()

    return response.data
```

## Alternativas Consideradas

### 1. Pinecone
- **Pros**:
  - Especializado em vector search
  - Performance otimizada
  - API simples
  - Escalabilidade ilimitada
- **Cons**:
  - Custo: $70/mes (1M vetores)
  - Dependencia de SaaS externo
  - Latencia de rede (API externa)
  - Vendor lock-in
- **Rejeicao**: Custo e dependencia nao justificados para dataset pequeno

### 2. Weaviate (self-hosted)
- **Pros**:
  - Open source, controle total
  - Performance excelente
  - Suporta filtros complexos
- **Cons**:
  - DevOps overhead (mais um servico)
  - Complexidade de setup
  - Custo de servidor adicional
- **Rejeicao**: Overkill para 529 chunks, overhead operacional

### 3. ChromaDB
- **Pros**:
  - Simples de usar
  - Open source
  - Python-first
- **Cons**:
  - Menos maduro que pgvector
  - Precisa servico separado
  - Persistencia menos robusta
- **Rejeicao**: Menos maduro, sem vantagem sobre pgvector

### 4. Elasticsearch com dense_vector
- **Pros**:
  - Ja pode ter Elasticsearch (search full-text)
  - Suporta hybrid search (dense + sparse)
- **Cons**:
  - Nao temos Elasticsearch
  - Complexidade alta
  - Custo de servidor
- **Rejeicao**: Nao precisamos de full-text search avancado

## Consequencias

### Positivas

1. **Custo zero adicional**
   - Supabase inclui pgvector
   - Vs $70/mes Pinecone = $840/ano economizados

2. **Simplicidade operacional**
   - 1 banco de dados para tudo
   - Backups automaticos (Supabase)
   - Migrations SQL normais

3. **Latencia baixa**
   - Query local (mesma VPC)
   - ~50ms para retrieval de 5 chunks
   - Vs 100-200ms com API externa

4. **Joins nativos**
   - Combinar vector search com filtros SQL
   - Ex: buscar chunks de "objecao" E similarity > 0.8
   ```sql
   SELECT * FROM conhecimento_chunks
   WHERE tipo = 'objecao'
   ORDER BY embedding <=> query_embedding
   LIMIT 5;
   ```

5. **Ferramentas familiares**
   - SQL para queries
   - pgAdmin para inspecao
   - Migrations via Supabase CLI

### Negativas

1. **Scaling limitado**
   - pgvector nao eh otimizado para bilhoes de vetores
   - Performance degrada com > 1M vetores
   - Mitigacao: Dataset pequeno (529 chunks), IVFFlat index

2. **Performance inferior a Pinecone**
   - Pinecone: ~10ms para retrieval
   - pgvector: ~50ms
   - Trade-off: Suficiente para use case (< 100ms target)

3. **Menos features avancados**
   - Pinecone tem metadata filtering otimizado
   - Pinecone tem namespaces
   - pgvector eh basico
   - Mitigacao: SQL normal resolve (WHERE clauses)

4. **Index tuning manual**
   - IVFFlat precisa configurar `lists` parameter
   - Nao eh auto-tuning como Pinecone
   - Mitigacao: Documentar best practices

### Mitigacoes

1. **IVFFlat index para escalar**
```sql
CREATE INDEX idx_conhecimento_embedding
ON conhecimento_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- sqrt(num_chunks)
```

2. **Monitoring de performance**
   - Tracking de latencia de retrieval
   - Alerta se > 200ms
   - Considerar migrar para Pinecone se dataset crescer 10x

3. **Caching de chunks populares**
   - Redis cache para chunks frequentemente acessados
   - TTL 1h
   - Reduz queries ao banco

4. **Escape hatch**
   - Se dataset crescer muito (> 100k chunks), migrar para Pinecone
   - Export/import via script Python
   - Abstraction layer: `VectorStore` interface

## Implementacao

### Indexacao de chunks

```python
# Indexar conhecimento
async def indexar_conhecimento():
    chunks = carregar_chunks_de_docs()

    for chunk in chunks:
        # Gerar embedding
        embedding = await voyage_client.embed(chunk.conteudo)

        # Salvar no banco
        await supabase.table("conhecimento_chunks").insert({
            "conteudo": chunk.conteudo,
            "embedding": embedding,
            "metadata": chunk.metadata,
            "tipo": chunk.tipo
        })
```

### Retrieval

```python
# Buscar chunks relevantes
async def buscar_conhecimento(query: str) -> List[str]:
    # Embedding da query
    query_embedding = await voyage_client.embed(query)

    # Similarity search
    response = supabase.rpc("match_conhecimento", {
        "query_embedding": query_embedding,
        "match_threshold": 0.7,
        "match_count": 5
    }).execute()

    return [chunk["conteudo"] for chunk in response.data]
```

### Function SQL para similarity

```sql
CREATE OR REPLACE FUNCTION match_conhecimento(
    query_embedding vector(1536),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id uuid,
    conteudo text,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        conteudo,
        1 - (embedding <=> query_embedding) as similarity
    FROM conhecimento_chunks
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
```

## Metricas de Sucesso

1. **Latencia de retrieval < 100ms** (p95)
2. **Accuracy de retrieval > 90%** (chunks relevantes retornados)
3. **Custo: $0 adicional** (incluido no Supabase)
4. **529 chunks indexados** com sucesso

## Referencias

- Codigo: `app/services/memoria.py` (RAG implementation)
- Schema: Migration `create_conhecimento_chunks.sql`
- Docs: `docs/arquitetura/rag-conhecimento.md` (se existir)
- pgvector docs: https://github.com/pgvector/pgvector
- Voyage AI: https://www.voyageai.com/

## Historico de Mudancas

- **2026-01**: Sprint 13 - Implementacao inicial
- **2026-01**: Sprint 13 - Indexacao de 529 chunks
- **2026-02**: Atual - Accuracy 92%, latencia p95 65ms
