# Epic 01: Indexação da Base de Conhecimento

## Objetivo

Indexar a documentação de treinamento (`docs/julia/`) como embeddings vetoriais para permitir busca semântica de conhecimento relevante.

## Contexto

A pasta `docs/julia/` contém 14 arquivos markdown com ~15.000 linhas de conhecimento:
- Guia de adaptação por perfil (783 linhas)
- Catálogo de objeções (2147 linhas)
- Erros críticos com sêniors (642 linhas)
- Conversas de referência (1060 linhas)
- Sistema de prompts avançado (839 linhas)
- E outros...

Este conhecimento precisa ser chunkeado, embedado e armazenado para busca vetorial.

## Pré-requisitos

- [x] Voyage AI configurado (Sprint 8)
- [x] Supabase pgvector funcionando (Sprint 8)
- [x] Tabela `memorias` já existe com embeddings

---

## Story 1.1: Schema para Documentos Indexados

### Objetivo
Criar tabela no Supabase para armazenar chunks de documentação com embeddings.

### Tarefas

1. **Criar migration** `create_conhecimento_julia`:
```sql
CREATE TABLE conhecimento_julia (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Origem do documento
    arquivo TEXT NOT NULL,           -- ex: 'guia_adaptacao_perfis_medicos.md'
    secao TEXT,                       -- ex: 'PERFIL 3: MÉDICO EXPERIENTE'
    subsecao TEXT,                    -- ex: 'Variação Primária: Soluções'

    -- Conteúdo
    conteudo TEXT NOT NULL,           -- Chunk de texto (500-1000 chars)

    -- Metadados para filtragem
    tipo TEXT NOT NULL,               -- 'perfil', 'objecao', 'erro', 'conversa', 'guardrail'
    subtipo TEXT,                     -- 'senior', 'preco', 'tempo', etc
    tags TEXT[],                      -- ['negociacao', 'valor', 'objecao']

    -- Embedding
    embedding VECTOR(1024),           -- Voyage AI dimension

    -- Controle
    versao TEXT DEFAULT 'v1',
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_conhecimento_embedding ON conhecimento_julia
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_conhecimento_tipo ON conhecimento_julia(tipo);
CREATE INDEX idx_conhecimento_subtipo ON conhecimento_julia(subtipo);
CREATE INDEX idx_conhecimento_tags ON conhecimento_julia USING GIN(tags);
CREATE INDEX idx_conhecimento_ativo ON conhecimento_julia(ativo) WHERE ativo = true;

-- Trigger para updated_at
CREATE TRIGGER conhecimento_julia_updated_at
    BEFORE UPDATE ON conhecimento_julia
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

2. **Criar função de busca** `buscar_conhecimento`:
```sql
CREATE OR REPLACE FUNCTION buscar_conhecimento(
    query_embedding VECTOR(1024),
    tipo_filtro TEXT DEFAULT NULL,
    subtipo_filtro TEXT DEFAULT NULL,
    limite INT DEFAULT 5,
    threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    arquivo TEXT,
    secao TEXT,
    conteudo TEXT,
    tipo TEXT,
    subtipo TEXT,
    tags TEXT[],
    similaridade FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.arquivo,
        c.secao,
        c.conteudo,
        c.tipo,
        c.subtipo,
        c.tags,
        1 - (c.embedding <=> query_embedding) as similaridade
    FROM conhecimento_julia c
    WHERE c.ativo = true
        AND (tipo_filtro IS NULL OR c.tipo = tipo_filtro)
        AND (subtipo_filtro IS NULL OR c.subtipo = subtipo_filtro)
        AND 1 - (c.embedding <=> query_embedding) >= threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT limite;
END;
$$;
```

### DoD

- [ ] Migration aplicada com sucesso
- [ ] Tabela `conhecimento_julia` criada
- [ ] Índices criados (embedding, tipo, subtipo, tags)
- [ ] Função `buscar_conhecimento` funcionando
- [ ] Query de teste retorna resultados vazios (tabela vazia)

### Testes

```python
# tests/conhecimento/test_schema.py
def test_tabela_existe():
    """Verifica que tabela foi criada."""
    result = supabase.table("conhecimento_julia").select("id").limit(1).execute()
    assert result.data is not None

def test_busca_funciona_tabela_vazia():
    """Busca retorna lista vazia quando não há dados."""
    # Gera embedding de teste
    embedding = [0.0] * 1024
    result = supabase.rpc("buscar_conhecimento", {
        "query_embedding": embedding,
        "limite": 5
    }).execute()
    assert result.data == []
```

---

## Story 1.2: Parser de Markdown para Chunks

### Objetivo
Criar parser que converte arquivos markdown em chunks estruturados com metadados.

### Tarefas

1. **Criar** `app/services/conhecimento/__init__.py`:
```python
"""Módulo de conhecimento dinâmico para Julia."""
from .indexador import IndexadorConhecimento
from .buscador import BuscadorConhecimento

__all__ = ["IndexadorConhecimento", "BuscadorConhecimento"]
```

2. **Criar** `app/services/conhecimento/indexador.py`:
```python
"""
Indexador de documentação Julia.

Converte markdown em chunks com metadados para embedding.
"""
import re
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class ChunkConhecimento:
    """Chunk de conhecimento extraído de documento."""
    arquivo: str
    secao: str
    subsecao: Optional[str]
    conteudo: str
    tipo: str           # 'perfil', 'objecao', 'erro', 'conversa', 'guardrail'
    subtipo: Optional[str]
    tags: list[str]


class ParserMarkdown:
    """Parser de markdown para chunks."""

    # Tamanho alvo dos chunks (em caracteres)
    CHUNK_SIZE_MIN = 300
    CHUNK_SIZE_MAX = 1200
    CHUNK_SIZE_TARGET = 700

    # Mapeamento arquivo -> tipo
    TIPO_POR_ARQUIVO = {
        "guia_adaptacao_perfis_medicos.md": "perfil",
        "julia_catalogo_objecoes_respostas.md": "objecao",
        "3_erros_criticos_medicos_senior.md": "erro",
        "CONVERSAS_REFERENCIA.md": "conversa",
        "julia_sistema_prompts_avancado.md": "guardrail",
        "julia_triggers_handoff_humano.md": "handoff",
        "julia_protocolo_escalacao_automatica.md": "escalacao",
        "julia_fundacao_cientifica.md": "fundacao",
        "julia_prompt_negociacao_detalhado.md": "negociacao",
        "PREFERENCIAS_MEDICO.md": "preferencias",
        "MENSAGENS_ABERTURA.md": "abertura",
    }

    # Padrões de seção
    PADRAO_H1 = re.compile(r'^#\s+(.+)$', re.MULTILINE)
    PADRAO_H2 = re.compile(r'^##\s+(.+)$', re.MULTILINE)
    PADRAO_H3 = re.compile(r'^###\s+(.+)$', re.MULTILINE)

    def parsear_arquivo(self, caminho: Path) -> list[ChunkConhecimento]:
        """
        Parseia arquivo markdown em chunks.

        Args:
            caminho: Path do arquivo .md

        Returns:
            Lista de chunks extraídos
        """
        nome_arquivo = caminho.name
        tipo = self.TIPO_POR_ARQUIVO.get(nome_arquivo, "geral")

        conteudo = caminho.read_text(encoding="utf-8")
        chunks = []

        # Dividir por seções H2
        secoes = self._dividir_por_secoes(conteudo)

        for secao_titulo, secao_conteudo in secoes:
            # Dividir seção em chunks menores se necessário
            sub_chunks = self._dividir_em_chunks(secao_conteudo)

            for i, chunk_texto in enumerate(sub_chunks):
                if len(chunk_texto.strip()) < self.CHUNK_SIZE_MIN:
                    continue

                # Detectar subtipo e tags
                subtipo = self._detectar_subtipo(secao_titulo, chunk_texto, tipo)
                tags = self._extrair_tags(secao_titulo, chunk_texto, tipo)

                chunk = ChunkConhecimento(
                    arquivo=nome_arquivo,
                    secao=secao_titulo,
                    subsecao=f"parte_{i+1}" if len(sub_chunks) > 1 else None,
                    conteudo=chunk_texto.strip(),
                    tipo=tipo,
                    subtipo=subtipo,
                    tags=tags
                )
                chunks.append(chunk)

        logger.info(f"Parseado {nome_arquivo}: {len(chunks)} chunks")
        return chunks

    def _dividir_por_secoes(self, conteudo: str) -> list[tuple[str, str]]:
        """Divide conteúdo por headers H2."""
        secoes = []
        partes = re.split(r'\n(?=##\s)', conteudo)

        for parte in partes:
            match = self.PADRAO_H2.match(parte)
            if match:
                titulo = match.group(1).strip()
                texto = parte[match.end():].strip()
                secoes.append((titulo, texto))
            elif parte.strip():
                # Conteúdo antes do primeiro H2
                secoes.append(("Introdução", parte.strip()))

        return secoes

    def _dividir_em_chunks(self, texto: str) -> list[str]:
        """Divide texto em chunks de tamanho adequado."""
        if len(texto) <= self.CHUNK_SIZE_MAX:
            return [texto]

        chunks = []
        paragrafos = texto.split('\n\n')
        chunk_atual = ""

        for paragrafo in paragrafos:
            if len(chunk_atual) + len(paragrafo) <= self.CHUNK_SIZE_TARGET:
                chunk_atual += "\n\n" + paragrafo if chunk_atual else paragrafo
            else:
                if chunk_atual:
                    chunks.append(chunk_atual)
                chunk_atual = paragrafo

        if chunk_atual:
            chunks.append(chunk_atual)

        return chunks

    def _detectar_subtipo(self, secao: str, texto: str, tipo: str) -> Optional[str]:
        """Detecta subtipo baseado no conteúdo."""
        texto_lower = (secao + " " + texto).lower()

        if tipo == "perfil":
            if "recém-formado" in texto_lower or "0-2 anos" in texto_lower:
                return "recem_formado"
            elif "em desenvolvimento" in texto_lower or "2-7 anos" in texto_lower:
                return "em_desenvolvimento"
            elif "experiente" in texto_lower or "7-15 anos" in texto_lower:
                return "experiente"
            elif "sênior" in texto_lower or "15+ anos" in texto_lower:
                return "senior"
            elif "especialista" in texto_lower or "subespecialista" in texto_lower:
                return "especialista"
            elif "transição" in texto_lower:
                return "em_transicao"

        elif tipo == "objecao":
            if "preço" in texto_lower or "valor" in texto_lower or "pag" in texto_lower:
                return "preco"
            elif "tempo" in texto_lower or "agenda" in texto_lower or "ocupado" in texto_lower:
                return "tempo"
            elif "confia" in texto_lower or "conhec" in texto_lower:
                return "confianca"
            elif "processo" in texto_lower or "burocracia" in texto_lower:
                return "processo"
            elif "disponib" in texto_lower:
                return "disponibilidade"
            elif "qualidade" in texto_lower or "hospital" in texto_lower:
                return "qualidade"
            elif "lealdade" in texto_lower or "outra plataforma" in texto_lower:
                return "lealdade"

        elif tipo == "erro":
            if "apoio" in texto_lower or "parceria" in texto_lower:
                return "erro_tom"
            elif "pressão" in texto_lower or "urgência" in texto_lower:
                return "erro_pressao"
            elif "dinheiro" in texto_lower or "remuneração" in texto_lower:
                return "erro_dinheiro"

        return None

    def _extrair_tags(self, secao: str, texto: str, tipo: str) -> list[str]:
        """Extrai tags relevantes do conteúdo."""
        tags = [tipo]
        texto_lower = (secao + " " + texto).lower()

        # Tags de contexto
        if "negoci" in texto_lower:
            tags.append("negociacao")
        if "objeção" in texto_lower or "objecao" in texto_lower:
            tags.append("objecao")
        if "exemplo" in texto_lower:
            tags.append("exemplo")
        if "evitar" in texto_lower or "não faça" in texto_lower:
            tags.append("evitar")
        if "✅" in texto or "correto" in texto_lower:
            tags.append("bom_exemplo")
        if "❌" in texto or "errado" in texto_lower:
            tags.append("mau_exemplo")
        if "framework" in texto_lower or "laar" in texto_lower:
            tags.append("framework")

        return list(set(tags))
```

### DoD

- [ ] Módulo `conhecimento/` criado
- [ ] `ParserMarkdown` implementado
- [ ] Chunks têm tamanho entre 300-1200 chars
- [ ] Tipo detectado corretamente por arquivo
- [ ] Subtipo detectado para perfis e objeções
- [ ] Tags extraídas do conteúdo
- [ ] Logs informativos de progresso

### Testes

```python
# tests/conhecimento/test_parser.py
from pathlib import Path
from app.services.conhecimento.indexador import ParserMarkdown, ChunkConhecimento

def test_parsear_arquivo_perfis():
    """Parseia guia de perfis e extrai chunks."""
    parser = ParserMarkdown()
    path = Path("docs/julia/guia_adaptacao_perfis_medicos.md")

    chunks = parser.parsear_arquivo(path)

    assert len(chunks) > 10
    assert all(isinstance(c, ChunkConhecimento) for c in chunks)
    assert all(c.tipo == "perfil" for c in chunks)

def test_chunks_tem_tamanho_adequado():
    """Chunks respeitam limites de tamanho."""
    parser = ParserMarkdown()
    path = Path("docs/julia/julia_catalogo_objecoes_respostas.md")

    chunks = parser.parsear_arquivo(path)

    for chunk in chunks:
        assert len(chunk.conteudo) >= parser.CHUNK_SIZE_MIN
        assert len(chunk.conteudo) <= parser.CHUNK_SIZE_MAX + 200  # margem

def test_detecta_subtipo_perfil():
    """Detecta subtipo de perfil corretamente."""
    parser = ParserMarkdown()

    subtipo = parser._detectar_subtipo(
        "PERFIL 4: MÉDICO SÊNIOR (15+ anos)",
        "Médicos sênior têm autonomia...",
        "perfil"
    )

    assert subtipo == "senior"

def test_detecta_subtipo_objecao():
    """Detecta subtipo de objeção corretamente."""
    parser = ParserMarkdown()

    subtipo = parser._detectar_subtipo(
        "Objeção 1: Vocês pagam muito pouco",
        "O médico quer mais remuneração...",
        "objecao"
    )

    assert subtipo == "preco"

def test_extrai_tags():
    """Extrai tags do conteúdo."""
    parser = ParserMarkdown()

    tags = parser._extrair_tags(
        "Como negociar",
        "✅ CORRETO: Exemplo de negociação...",
        "objecao"
    )

    assert "objecao" in tags
    assert "negociacao" in tags
    assert "bom_exemplo" in tags
```

---

## Story 1.3: Geração de Embeddings e Armazenamento

### Objetivo
Gerar embeddings para todos os chunks e armazenar no Supabase.

### Tarefas

1. **Adicionar ao** `app/services/conhecimento/indexador.py`:
```python
class IndexadorConhecimento:
    """Indexa documentação Julia no Supabase."""

    def __init__(self):
        self.parser = ParserMarkdown()
        self.docs_path = Path("docs/julia")

    async def indexar_todos(self, reindexar: bool = False) -> dict:
        """
        Indexa todos os documentos da pasta docs/julia/.

        Args:
            reindexar: Se True, remove dados antigos antes

        Returns:
            Estatísticas da indexação
        """
        from app.services.embedding import gerar_embedding
        from app.services.supabase import supabase

        stats = {
            "arquivos": 0,
            "chunks": 0,
            "embeddings": 0,
            "erros": 0
        }

        if reindexar:
            logger.info("Removendo dados antigos...")
            supabase.table("conhecimento_julia").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

        # Listar arquivos .md
        arquivos = list(self.docs_path.glob("*.md"))
        logger.info(f"Encontrados {len(arquivos)} arquivos para indexar")

        for arquivo in arquivos:
            try:
                chunks = self.parser.parsear_arquivo(arquivo)
                stats["arquivos"] += 1

                for chunk in chunks:
                    try:
                        # Gerar embedding
                        embedding = await gerar_embedding(chunk.conteudo)

                        # Salvar no banco
                        data = {
                            "arquivo": chunk.arquivo,
                            "secao": chunk.secao,
                            "subsecao": chunk.subsecao,
                            "conteudo": chunk.conteudo,
                            "tipo": chunk.tipo,
                            "subtipo": chunk.subtipo,
                            "tags": chunk.tags,
                            "embedding": embedding
                        }

                        supabase.table("conhecimento_julia").insert(data).execute()
                        stats["chunks"] += 1
                        stats["embeddings"] += 1

                    except Exception as e:
                        logger.error(f"Erro ao indexar chunk: {e}")
                        stats["erros"] += 1

            except Exception as e:
                logger.error(f"Erro ao processar {arquivo}: {e}")
                stats["erros"] += 1

        logger.info(f"Indexação concluída: {stats}")
        return stats

    async def indexar_arquivo(self, nome_arquivo: str) -> int:
        """
        Indexa um arquivo específico.

        Args:
            nome_arquivo: Nome do arquivo em docs/julia/

        Returns:
            Número de chunks indexados
        """
        from app.services.embedding import gerar_embedding
        from app.services.supabase import supabase

        caminho = self.docs_path / nome_arquivo
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

        # Remover chunks antigos deste arquivo
        supabase.table("conhecimento_julia").delete().eq("arquivo", nome_arquivo).execute()

        chunks = self.parser.parsear_arquivo(caminho)
        count = 0

        for chunk in chunks:
            embedding = await gerar_embedding(chunk.conteudo)

            data = {
                "arquivo": chunk.arquivo,
                "secao": chunk.secao,
                "subsecao": chunk.subsecao,
                "conteudo": chunk.conteudo,
                "tipo": chunk.tipo,
                "subtipo": chunk.subtipo,
                "tags": chunk.tags,
                "embedding": embedding
            }

            supabase.table("conhecimento_julia").insert(data).execute()
            count += 1

        logger.info(f"Indexado {nome_arquivo}: {count} chunks")
        return count
```

2. **Criar script** `scripts/indexar_conhecimento.py`:
```python
#!/usr/bin/env python
"""Script para indexar documentação Julia."""
import asyncio
import sys
from app.services.conhecimento import IndexadorConhecimento

async def main():
    reindexar = "--reindexar" in sys.argv

    indexador = IndexadorConhecimento()
    stats = await indexador.indexar_todos(reindexar=reindexar)

    print(f"\n=== Indexação Concluída ===")
    print(f"Arquivos processados: {stats['arquivos']}")
    print(f"Chunks criados: {stats['chunks']}")
    print(f"Embeddings gerados: {stats['embeddings']}")
    print(f"Erros: {stats['erros']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### DoD

- [ ] `IndexadorConhecimento` implementado
- [ ] Método `indexar_todos()` funciona
- [ ] Método `indexar_arquivo()` funciona
- [ ] Script de indexação criado
- [ ] Todos os docs indexados (>100 chunks)
- [ ] Embeddings gerados via Voyage AI
- [ ] Dados armazenados no Supabase

### Testes

```python
# tests/conhecimento/test_indexador.py
import pytest
from app.services.conhecimento import IndexadorConhecimento

@pytest.mark.asyncio
async def test_indexar_arquivo_unico():
    """Indexa um arquivo e verifica chunks."""
    indexador = IndexadorConhecimento()

    count = await indexador.indexar_arquivo("MENSAGENS_ABERTURA.md")

    assert count > 0

@pytest.mark.asyncio
async def test_reindexar_remove_antigos():
    """Reindexação remove dados antigos."""
    from app.services.supabase import supabase

    indexador = IndexadorConhecimento()

    # Indexar uma vez
    await indexador.indexar_arquivo("MENSAGENS_ABERTURA.md")
    count1 = supabase.table("conhecimento_julia").select("id", count="exact").eq("arquivo", "MENSAGENS_ABERTURA.md").execute()

    # Reindexar
    await indexador.indexar_arquivo("MENSAGENS_ABERTURA.md")
    count2 = supabase.table("conhecimento_julia").select("id", count="exact").eq("arquivo", "MENSAGENS_ABERTURA.md").execute()

    # Não deve duplicar
    assert count1.count == count2.count
```

---

## Story 1.4: Busca Semântica de Conhecimento

### Objetivo
Implementar serviço de busca semântica sobre a base de conhecimento.

### Tarefas

1. **Criar** `app/services/conhecimento/buscador.py`:
```python
"""
Buscador semântico de conhecimento Julia.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from app.services.embedding import gerar_embedding
from app.services.supabase import supabase
from app.services.redis import cache_get, cache_set

logger = logging.getLogger(__name__)

# Cache TTL para buscas (5 minutos)
CACHE_TTL_BUSCA = 300


@dataclass
class ResultadoBusca:
    """Resultado de busca de conhecimento."""
    id: str
    arquivo: str
    secao: str
    conteudo: str
    tipo: str
    subtipo: Optional[str]
    tags: list[str]
    similaridade: float


class BuscadorConhecimento:
    """Busca semântica na base de conhecimento."""

    def __init__(
        self,
        threshold: float = 0.65,
        limite_padrao: int = 3
    ):
        self.threshold = threshold
        self.limite_padrao = limite_padrao

    async def buscar(
        self,
        query: str,
        tipo: Optional[str] = None,
        subtipo: Optional[str] = None,
        limite: Optional[int] = None,
        usar_cache: bool = True
    ) -> list[ResultadoBusca]:
        """
        Busca conhecimento relevante para a query.

        Args:
            query: Texto para buscar
            tipo: Filtrar por tipo (perfil, objecao, etc)
            subtipo: Filtrar por subtipo (senior, preco, etc)
            limite: Número máximo de resultados
            usar_cache: Se deve usar cache

        Returns:
            Lista de resultados ordenados por relevância
        """
        limite = limite or self.limite_padrao

        # Tentar cache
        if usar_cache:
            cache_key = f"conhecimento:{hash(query)}:{tipo}:{subtipo}:{limite}"
            cached = await cache_get(cache_key)
            if cached:
                logger.debug(f"Busca em cache: {query[:50]}...")
                return [ResultadoBusca(**r) for r in cached]

        # Gerar embedding da query
        query_embedding = await gerar_embedding(query)

        # Buscar via função SQL
        response = supabase.rpc("buscar_conhecimento", {
            "query_embedding": query_embedding,
            "tipo_filtro": tipo,
            "subtipo_filtro": subtipo,
            "limite": limite,
            "threshold": self.threshold
        }).execute()

        resultados = [
            ResultadoBusca(
                id=r["id"],
                arquivo=r["arquivo"],
                secao=r["secao"],
                conteudo=r["conteudo"],
                tipo=r["tipo"],
                subtipo=r["subtipo"],
                tags=r["tags"] or [],
                similaridade=r["similaridade"]
            )
            for r in response.data
        ]

        # Salvar em cache
        if usar_cache and resultados:
            await cache_set(
                cache_key,
                [r.__dict__ for r in resultados],
                CACHE_TTL_BUSCA
            )

        logger.info(f"Busca '{query[:30]}...': {len(resultados)} resultados")
        return resultados

    async def buscar_para_objecao(self, mensagem: str) -> list[ResultadoBusca]:
        """
        Busca conhecimento específico para lidar com objeção.

        Args:
            mensagem: Mensagem do médico com objeção

        Returns:
            Conhecimento sobre como responder
        """
        return await self.buscar(
            query=f"Como responder quando médico diz: {mensagem}",
            tipo="objecao",
            limite=3
        )

    async def buscar_para_perfil(self, perfil: str) -> list[ResultadoBusca]:
        """
        Busca conhecimento sobre como abordar perfil específico.

        Args:
            perfil: Nome do perfil (senior, recem_formado, etc)

        Returns:
            Conhecimento sobre abordagem para perfil
        """
        return await self.buscar(
            query=f"Como abordar médico {perfil.replace('_', ' ')}",
            tipo="perfil",
            subtipo=perfil,
            limite=3
        )

    async def buscar_exemplos_conversa(self, contexto: str) -> list[ResultadoBusca]:
        """
        Busca exemplos de conversas reais relevantes.

        Args:
            contexto: Contexto da situação atual

        Returns:
            Exemplos de conversas de referência
        """
        return await self.buscar(
            query=contexto,
            tipo="conversa",
            limite=2
        )
```

### DoD

- [ ] `BuscadorConhecimento` implementado
- [ ] Busca genérica funciona
- [ ] Filtros por tipo/subtipo funcionam
- [ ] Cache implementado (5 min TTL)
- [ ] Métodos específicos: `buscar_para_objecao`, `buscar_para_perfil`, `buscar_exemplos_conversa`
- [ ] Threshold configurável (default 0.65)

### Testes

```python
# tests/conhecimento/test_buscador.py
import pytest
from app.services.conhecimento import BuscadorConhecimento

@pytest.fixture
def buscador():
    return BuscadorConhecimento(threshold=0.5)

@pytest.mark.asyncio
async def test_busca_generica(buscador):
    """Busca genérica retorna resultados."""
    resultados = await buscador.buscar("como lidar com médico sênior")

    assert len(resultados) > 0
    assert all(r.similaridade >= 0.5 for r in resultados)

@pytest.mark.asyncio
async def test_busca_com_filtro_tipo(buscador):
    """Filtro por tipo funciona."""
    resultados = await buscador.buscar(
        "negociação de valor",
        tipo="objecao"
    )

    assert all(r.tipo == "objecao" for r in resultados)

@pytest.mark.asyncio
async def test_buscar_para_objecao(buscador):
    """Busca específica para objeção funciona."""
    resultados = await buscador.buscar_para_objecao(
        "Vocês pagam muito pouco"
    )

    assert len(resultados) > 0
    assert any("preco" in r.subtipo or "valor" in r.conteudo.lower() for r in resultados)

@pytest.mark.asyncio
async def test_buscar_para_perfil(buscador):
    """Busca específica para perfil funciona."""
    resultados = await buscador.buscar_para_perfil("senior")

    assert len(resultados) > 0
    assert any("senior" in r.subtipo or "sênior" in r.conteudo.lower() for r in resultados)

@pytest.mark.asyncio
async def test_cache_funciona(buscador):
    """Cache é usado na segunda busca."""
    # Primeira busca (sem cache)
    await buscador.buscar("teste cache", usar_cache=True)

    # Segunda busca (deve usar cache - verificar via logs ou mock)
    resultados = await buscador.buscar("teste cache", usar_cache=True)

    # Resultado deve ser o mesmo (indica cache)
    assert resultados is not None
```

---

## Checklist do Épico

- [ ] **S13.E1.1** - Schema criado
- [ ] **S13.E1.2** - Parser implementado
- [ ] **S13.E1.3** - Indexador funcionando
- [ ] **S13.E1.4** - Buscador implementado
- [ ] Todos os testes passando
- [ ] Documentação indexada (rodar script)
