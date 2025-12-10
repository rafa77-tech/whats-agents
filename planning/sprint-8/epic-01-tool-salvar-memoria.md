# Epic 01: Tool salvar_memoria

## Prioridade: P0 (Critico)

## Objetivo

> **Criar tool `salvar_memoria` que permite ao LLM salvar informacoes importantes sobre o medico durante a conversa.**

Atualmente, a Julia nao tem como persistir preferencias ou informacoes que o medico menciona durante a conversa. Isso causa:
1. Julia pergunta a mesma coisa varias vezes
2. Nao lembra preferencias ja mencionadas
3. Experiencia parece robotica e sem memoria

---

## Problema

Sem a tool `salvar_memoria`, a Julia:
1. Nao salva quando medico diz "so faco noturno"
2. Nao registra quando medico menciona "moro em Santo Andre"
3. Perde informacoes pessoais como "tenho filhos pequenos entao nao faco plantao de sabado"

---

## Referencia: Tabela doctor_context

A tabela ja existe no schema mas nao esta sendo usada:

```sql
CREATE TABLE doctor_context (
    id UUID PRIMARY KEY,
    cliente_id UUID REFERENCES clientes(id),
    content TEXT NOT NULL,           -- Conteudo da memoria
    embedding vector(1536),          -- Para busca semantica
    source VARCHAR(50),              -- 'conversation', 'manual', 'import'
    tipo VARCHAR(50),                -- 'preferencia', 'restricao', 'info_pessoal'
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

---

## Stories

---

# S8.E1.1 - Definir schema da tool salvar_memoria

## Objetivo

> **Criar definicao da tool salvar_memoria seguindo padrao Anthropic tool_use.**

## Contexto Tecnico

A tool deve permitir que o LLM:
- Salve preferencias do medico (turnos, valores, regioes)
- Salve restricoes (dias que nao pode, hospitais que nao gosta)
- Salve informacoes pessoais relevantes (cidade, familia)
- Categorize o tipo de informacao

## Codigo Esperado

**Arquivo:** `app/tools/memoria.py`

```python
TOOL_SALVAR_MEMORIA = {
    "name": "salvar_memoria",
    "description": """Salva informacao importante sobre o medico para lembrar em conversas futuras.

Use esta tool quando o medico mencionar:
- Preferencias: "so faco noturno", "prefiro acima de 2500", "gosto do ABC"
- Restricoes: "nao trabalho sabado", "nao gosto do Hospital X", "nao faco 24h"
- Informacoes pessoais: "moro em Santo Andre", "tenho filhos pequenos", "sou residente"
- Disponibilidade: "so tenho disponibilidade em dezembro", "to de ferias ate dia 15"

NAO use para:
- Informacoes obvias que ja estao no cadastro (nome, CRM, especialidade)
- Detalhes da conversa atual que nao serao uteis no futuro
- Informacoes temporarias (ex: "to em cirurgia agora")

IMPORTANTE: Seja especifico no conteudo.
Bom: "Prefere plantoes noturnos por causa dos filhos"
Ruim: "falou sobre noturno"
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "tipo": {
                "type": "string",
                "enum": ["preferencia", "restricao", "info_pessoal", "disponibilidade"],
                "description": "Categoria da informacao"
            },
            "conteudo": {
                "type": "string",
                "description": "Informacao a ser salva. Seja especifico e inclua contexto relevante."
            },
            "contexto": {
                "type": "string",
                "description": "Opcional: contexto adicional sobre por que essa informacao e importante"
            }
        },
        "required": ["tipo", "conteudo"]
    }
}
```

## Criterios de Aceite

1. **Definicao valida:** Schema segue formato Anthropic tool_use
2. **Tipos claros:** Enum com categorias bem definidas
3. **Exemplos no description:** Mostra quando usar e quando NAO usar
4. **Conteudo especifico:** Instrui a ser especifico, nao generico

## DoD

- [ ] Constante `TOOL_SALVAR_MEMORIA` definida em `app/tools/memoria.py`
- [ ] Schema validado contra especificacao Anthropic
- [ ] Description inclui exemplos de uso correto
- [ ] Description inclui exemplos de quando NAO usar
- [ ] Enum `tipo` inclui categorias relevantes para o negocio

## Testes de Validacao

```python
def test_tool_schema_valido():
    from app.tools.memoria import TOOL_SALVAR_MEMORIA

    assert "name" in TOOL_SALVAR_MEMORIA
    assert TOOL_SALVAR_MEMORIA["name"] == "salvar_memoria"
    assert "input_schema" in TOOL_SALVAR_MEMORIA
    assert "properties" in TOOL_SALVAR_MEMORIA["input_schema"]

    props = TOOL_SALVAR_MEMORIA["input_schema"]["properties"]
    assert "tipo" in props
    assert "conteudo" in props
    assert props["tipo"]["enum"] == ["preferencia", "restricao", "info_pessoal", "disponibilidade"]

def test_tool_required_fields():
    from app.tools.memoria import TOOL_SALVAR_MEMORIA

    required = TOOL_SALVAR_MEMORIA["input_schema"]["required"]
    assert "tipo" in required
    assert "conteudo" in required
```

---

# S8.E1.2 - Implementar handler salvar_memoria

## Objetivo

> **Criar funcao que salva a memoria no banco quando LLM chama a tool.**

## Contexto Tecnico

O handler deve:
1. Receber parametros da tool
2. Validar que conteudo nao e duplicado
3. Gerar embedding do conteudo (para RAG futuro)
4. Salvar em doctor_context
5. Retornar confirmacao para o LLM

## Codigo Esperado

**Arquivo:** `app/tools/memoria.py`

```python
import logging
from datetime import datetime
from typing import Any

from app.services.supabase import get_supabase
from app.services.embedding import gerar_embedding

logger = logging.getLogger(__name__)


async def handle_salvar_memoria(
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict[str, Any]:
    """
    Executa salvamento de memoria quando LLM chama a tool.

    Args:
        tool_input: Parametros da tool (tipo, conteudo, contexto)
        medico: Dados do medico da conversa
        conversa: Dados da conversa atual

    Returns:
        dict com:
        - success: bool
        - mensagem: str para o LLM contextualizar
    """
    try:
        tipo = tool_input.get("tipo")
        conteudo = tool_input.get("conteudo", "").strip()
        contexto_extra = tool_input.get("contexto", "")

        # Validacoes
        if not tipo or not conteudo:
            return {
                "success": False,
                "mensagem": "Tipo e conteudo sao obrigatorios"
            }

        if len(conteudo) < 10:
            return {
                "success": False,
                "mensagem": "Conteudo muito curto. Seja mais especifico."
            }

        if len(conteudo) > 500:
            return {
                "success": False,
                "mensagem": "Conteudo muito longo. Resuma em ate 500 caracteres."
            }

        cliente_id = medico.get("id")
        if not cliente_id:
            return {
                "success": False,
                "mensagem": "Medico nao identificado"
            }

        # Verificar duplicata (evitar salvar mesma coisa varias vezes)
        supabase = get_supabase()
        existente = await _verificar_memoria_existente(
            cliente_id, tipo, conteudo
        )

        if existente:
            logger.info(f"Memoria similar ja existe para {cliente_id[:8]}")
            return {
                "success": True,
                "mensagem": "Ja tenho essa informacao registrada"
            }

        # Gerar embedding para busca semantica futura
        embedding = await gerar_embedding(conteudo)

        # Montar conteudo completo
        conteudo_final = conteudo
        if contexto_extra:
            conteudo_final = f"{conteudo} (Contexto: {contexto_extra})"

        # Salvar no banco
        response = supabase.table("doctor_context").insert({
            "cliente_id": cliente_id,
            "content": conteudo_final,
            "embedding": embedding,
            "source": "conversation",
            "tipo": tipo,
            "conversa_id": conversa.get("id"),
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        if response.data:
            logger.info(
                f"Memoria salva para {cliente_id[:8]}: "
                f"tipo={tipo}, conteudo={conteudo[:50]}..."
            )
            return {
                "success": True,
                "mensagem": "Anotado! Vou lembrar disso."
            }
        else:
            logger.error(f"Erro ao salvar memoria: {response}")
            return {
                "success": False,
                "mensagem": "Erro ao salvar. Tente novamente."
            }

    except Exception as e:
        logger.error(f"Erro no handler salvar_memoria: {e}", exc_info=True)
        return {
            "success": False,
            "mensagem": "Erro interno ao salvar memoria"
        }


async def _verificar_memoria_existente(
    cliente_id: str,
    tipo: str,
    conteudo: str
) -> bool:
    """
    Verifica se ja existe memoria similar para evitar duplicatas.

    Usa busca semantica para encontrar memorias similares,
    nao apenas texto exato.
    """
    try:
        supabase = get_supabase()

        # Busca simples por tipo (depois pode melhorar com embedding)
        response = (
            supabase.table("doctor_context")
            .select("id, content")
            .eq("cliente_id", cliente_id)
            .eq("tipo", tipo)
            .execute()
        )

        if not response.data:
            return False

        # Verificar similaridade textual basica
        conteudo_lower = conteudo.lower()
        for memoria in response.data:
            existente_lower = memoria["content"].lower()

            # Se mais de 70% das palavras coincidem, considera duplicata
            palavras_novas = set(conteudo_lower.split())
            palavras_existentes = set(existente_lower.split())

            if len(palavras_novas) == 0:
                continue

            intersecao = palavras_novas & palavras_existentes
            similaridade = len(intersecao) / len(palavras_novas)

            if similaridade > 0.7:
                return True

        return False

    except Exception as e:
        logger.error(f"Erro ao verificar memoria existente: {e}")
        return False  # Na duvida, permite salvar
```

## Criterios de Aceite

1. **Validacoes:** Rejeita conteudo vazio, muito curto ou muito longo
2. **Anti-duplicata:** Nao salva se ja existe memoria similar
3. **Embedding gerado:** Prepara para RAG futuro
4. **Logging:** Loga salvamento com contexto
5. **Erro tratado:** Erros nao quebram conversa
6. **Mensagem amigavel:** Retorno natural para LLM

## DoD

- [ ] Funcao `handle_salvar_memoria()` implementada
- [ ] Validacao de tipo e conteudo
- [ ] Validacao de tamanho (min 10, max 500)
- [ ] Verificacao de duplicata funciona
- [ ] Embedding gerado antes de salvar
- [ ] Dados salvos em doctor_context
- [ ] source = 'conversation' para rastreabilidade
- [ ] Logs incluem cliente_id e tipo

## Testes

```python
@pytest.mark.asyncio
async def test_salvar_memoria_sucesso():
    medico = {"id": "123"}
    conversa = {"id": "456"}

    result = await handle_salvar_memoria(
        {"tipo": "preferencia", "conteudo": "Prefere plantoes noturnos"},
        medico,
        conversa
    )

    assert result["success"] == True
    assert "Anotado" in result["mensagem"]

@pytest.mark.asyncio
async def test_salvar_memoria_conteudo_curto():
    result = await handle_salvar_memoria(
        {"tipo": "preferencia", "conteudo": "noturno"},
        {"id": "123"},
        {"id": "456"}
    )

    assert result["success"] == False
    assert "curto" in result["mensagem"].lower()

@pytest.mark.asyncio
async def test_salvar_memoria_duplicata():
    medico = {"id": "123"}
    conversa = {"id": "456"}

    # Primeira vez - sucesso
    result1 = await handle_salvar_memoria(
        {"tipo": "preferencia", "conteudo": "Prefere plantoes noturnos por causa dos filhos"},
        medico,
        conversa
    )
    assert result1["success"] == True

    # Segunda vez - detecta duplicata
    result2 = await handle_salvar_memoria(
        {"tipo": "preferencia", "conteudo": "Prefere plantoes noturnos devido aos filhos"},
        medico,
        conversa
    )
    assert "ja tenho" in result2["mensagem"].lower()
```

---

# S8.E1.3 - Criar servico de embedding

## Objetivo

> **Criar servico para gerar embeddings de texto usando Voyage AI (recomendado pela Anthropic).**

## Contexto Tecnico

Para RAG funcionar, precisamos de embeddings. **Decisao: Voyage AI**

| Criterio | Voyage voyage-3.5-lite | OpenAI text-embedding-3-small |
|----------|------------------------|------------------------------|
| Preco | $0.02/1M tokens | $0.02/1M tokens |
| Qualidade | +6.34% superior | baseline |
| Contexto | 32K tokens | 8K tokens |
| Dimensoes | 1024 | 1536 |
| Parceria Anthropic | ✅ Oficial | ❌ |

**Por que Voyage AI:**
- Recomendacao oficial da Anthropic
- Mesmo preco, qualidade superior
- Contexto 4x maior (importante para memorias longas)
- Dimensoes menores = menos custo de storage no pgvector
- Consistencia com stack Anthropic (Claude)

## Codigo Esperado

**Arquivo:** `app/services/embedding.py`

```python
"""
Servico de geracao de embeddings para RAG.

Usa Voyage AI voyage-3.5-lite (recomendado pela Anthropic).
- Mesmo preco que OpenAI ($0.02/1M tokens)
- Qualidade 6% superior
- Contexto 32K tokens
- Dimensoes 1024 (menor = menos storage)
"""
import logging
from typing import Optional

import voyageai

from app.core.config import settings

logger = logging.getLogger(__name__)

# Dimensao do embedding (voyage-3.5-lite = 1024)
EMBEDDING_DIMENSION = 1024

# Modelo a usar
VOYAGE_MODEL = "voyage-3.5-lite"

# Cliente Voyage (singleton)
_voyage_client: Optional[voyageai.Client] = None


def _get_voyage_client() -> Optional[voyageai.Client]:
    """Retorna cliente Voyage (singleton)."""
    global _voyage_client

    if _voyage_client is None:
        if not settings.VOYAGE_API_KEY:
            logger.warning("VOYAGE_API_KEY nao configurada")
            return None
        _voyage_client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)

    return _voyage_client


async def gerar_embedding(texto: str, input_type: str = "document") -> Optional[list[float]]:
    """
    Gera embedding para um texto usando Voyage AI.

    Args:
        texto: Texto para gerar embedding
        input_type: "document" para memorias, "query" para buscas

    Returns:
        Lista de floats representando o embedding, ou None se erro
    """
    if not texto or not texto.strip():
        return None

    try:
        client = _get_voyage_client()
        if not client:
            return None

        # Limpar texto (Voyage suporta 32K, mas limitamos para economia)
        texto_limpo = texto.strip()[:16000]

        result = client.embed(
            [texto_limpo],
            model=VOYAGE_MODEL,
            input_type=input_type
        )

        return result.embeddings[0]

    except Exception as e:
        logger.error(f"Erro ao gerar embedding Voyage: {e}")
        return None


async def gerar_embeddings_batch(
    textos: list[str],
    input_type: str = "document"
) -> list[Optional[list[float]]]:
    """
    Gera embeddings para multiplos textos em batch.

    Mais eficiente que chamar um por um.

    Args:
        textos: Lista de textos
        input_type: "document" ou "query"

    Returns:
        Lista de embeddings
    """
    if not textos:
        return []

    try:
        client = _get_voyage_client()
        if not client:
            return [None] * len(textos)

        # Limpar textos
        textos_limpos = [t.strip()[:16000] for t in textos]

        result = client.embed(
            textos_limpos,
            model=VOYAGE_MODEL,
            input_type=input_type
        )

        return result.embeddings

    except Exception as e:
        logger.error(f"Erro ao gerar embeddings batch Voyage: {e}")
        return [None] * len(textos)


def calcular_similaridade(embedding1: list[float], embedding2: list[float]) -> float:
    """
    Calcula similaridade coseno entre dois embeddings.

    Returns:
        Float entre 0 e 1 (1 = identico)
    """
    if not embedding1 or not embedding2:
        return 0.0

    # Produto escalar
    dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

    # Normas
    norm1 = sum(a * a for a in embedding1) ** 0.5
    norm2 = sum(b * b for b in embedding2) ** 0.5

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)
```

## Criterios de Aceite

1. **Voyage funciona:** Gera embedding de 1024 dimensoes
2. **Fallback gracioso:** Se nao configurado, retorna None sem quebrar
3. **Batch eficiente:** Suporta multiplos textos
4. **input_type correto:** Usa "document" para memorias, "query" para buscas
5. **Limite respeitado:** Trunca texto > 16000 chars (economia)

## DoD

- [ ] Funcao `gerar_embedding()` implementada
- [ ] Funcao `gerar_embeddings_batch()` implementada
- [ ] Integracao com Voyage AI funcionando
- [ ] Parametro `input_type` implementado
- [ ] Fallback quando API nao configurada
- [ ] Logs de erro com contexto
- [ ] Variavel `VOYAGE_API_KEY` em settings
- [ ] Dependencia `voyageai` adicionada ao pyproject.toml

## Testes

```python
@pytest.mark.asyncio
async def test_gerar_embedding_texto_valido():
    embedding = await gerar_embedding("Prefere plantoes noturnos")

    if settings.VOYAGE_API_KEY:
        assert embedding is not None
        assert len(embedding) == 1024  # Voyage voyage-3.5-lite
    else:
        assert embedding is None  # Fallback sem API

@pytest.mark.asyncio
async def test_gerar_embedding_texto_vazio():
    embedding = await gerar_embedding("")
    assert embedding is None

@pytest.mark.asyncio
async def test_gerar_embedding_texto_longo():
    texto_longo = "a" * 20000
    embedding = await gerar_embedding(texto_longo)
    # Deve truncar para 16000 e funcionar
    if settings.VOYAGE_API_KEY:
        assert embedding is not None

@pytest.mark.asyncio
async def test_gerar_embedding_input_type_query():
    # Para buscas semanticas, usar input_type="query"
    embedding = await gerar_embedding("tem vaga noturna?", input_type="query")

    if settings.VOYAGE_API_KEY:
        assert embedding is not None
```

---

# S8.E1.4 - Registrar tool no agente

## Objetivo

> **Adicionar tool `salvar_memoria` na lista de tools disponiveis para o LLM.**

## Contexto Tecnico

O LLM precisa:
1. Receber a definicao da tool no `tools` parameter da API
2. Ter o handler configurado para processar quando chamar
3. Receber instrucoes no prompt de quando usar

## Codigo Esperado

**Arquivo:** `app/services/agente.py` (modificar)

```python
from app.tools.memoria import TOOL_SALVAR_MEMORIA, handle_salvar_memoria

# Lista de tools disponiveis para o agente
JULIA_TOOLS = [
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
    TOOL_AGENDAR_LEMBRETE,
    TOOL_SALVAR_MEMORIA,  # Nova tool
]


async def processar_tool_call(
    tool_name: str,
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict:
    """Processa chamada de tool do LLM."""

    if tool_name == "buscar_vagas":
        return await handle_buscar_vagas(tool_input, medico, conversa)

    if tool_name == "reservar_plantao":
        return await handle_reservar_plantao(tool_input, medico, conversa)

    if tool_name == "agendar_lembrete":
        return await handle_agendar_lembrete(tool_input, medico, conversa)

    if tool_name == "salvar_memoria":
        return await handle_salvar_memoria(tool_input, medico, conversa)

    return {"success": False, "error": f"Tool desconhecida: {tool_name}"}
```

**Arquivo:** `app/core/prompts.py` (adicionar instrucoes)

```python
INSTRUCOES_TOOL_MEMORIA = """
### salvar_memoria
Use para registrar informacoes importantes que o medico menciona:

QUANDO USAR:
- Medico menciona preferencia: "so faco noturno", "prefiro ABC"
- Medico menciona restricao: "nao trabalho sabado", "nao gosto do Hospital X"
- Medico menciona info pessoal relevante: "moro em Santo Andre", "tenho filhos"
- Medico menciona disponibilidade: "so em dezembro", "to de ferias"

QUANDO NAO USAR:
- Informacoes que ja estao no cadastro (nome, CRM)
- Coisas temporarias ("to em cirurgia agora")
- Detalhes irrelevantes para futuras conversas

COMO USAR:
1. Identifique o tipo: preferencia, restricao, info_pessoal, disponibilidade
2. Escreva conteudo ESPECIFICO: "Prefere noturnos por causa dos filhos"
3. NAO escreva generico: "falou sobre noturno"

Exemplos:
- Medico diz "so aceito acima de 2500" -> salvar_memoria(tipo="preferencia", conteudo="Valor minimo de R$ 2.500 por plantao")
- Medico diz "nao gosto do Sao Luiz" -> salvar_memoria(tipo="restricao", conteudo="Nao quer trabalhar no Hospital Sao Luiz")
- Medico diz "tenho criancas pequenas" -> salvar_memoria(tipo="info_pessoal", conteudo="Tem filhos pequenos - pode afetar disponibilidade")
"""
```

## Criterios de Aceite

1. **Tool listada:** `TOOL_SALVAR_MEMORIA` aparece em JULIA_TOOLS
2. **Handler mapeado:** `salvar_memoria` chama `handle_salvar_memoria`
3. **Import funciona:** Sem erros de import circular
4. **Instrucoes claras:** Prompt explica quando usar
5. **Exemplos concretos:** Mostra uso correto

## DoD

- [ ] `TOOL_SALVAR_MEMORIA` importada em `app/services/agente.py`
- [ ] Tool adicionada em `JULIA_TOOLS`
- [ ] Handler adicionado em `processar_tool_call()`
- [ ] Instrucoes adicionadas em `app/core/prompts.py`
- [ ] Import testado sem erros circulares
- [ ] LLM recebe tool na chamada API

## Teste de Integracao

```python
def test_tool_registrada():
    from app.services.agente import JULIA_TOOLS

    tool_names = [t["name"] for t in JULIA_TOOLS]
    assert "salvar_memoria" in tool_names

@pytest.mark.asyncio
async def test_processar_tool_call_memoria():
    from app.services.agente import processar_tool_call

    result = await processar_tool_call(
        tool_name="salvar_memoria",
        tool_input={"tipo": "preferencia", "conteudo": "Prefere noturnos"},
        medico={"id": "123"},
        conversa={"id": "456"}
    )

    assert "success" in result
```

---

## Resumo do Epic

| Story | Descricao | Complexidade |
|-------|-----------|--------------|
| S8.E1.1 | Definir schema da tool | Baixa |
| S8.E1.2 | Implementar handler | Media |
| S8.E1.3 | Criar servico embedding | Media |
| S8.E1.4 | Registrar no agente | Baixa |

## Ordem de Implementacao

1. S8.E1.3 - Embedding (dependencia do handler)
2. S8.E1.1 - Schema (base para handler)
3. S8.E1.2 - Handler (logica principal)
4. S8.E1.4 - Registro (conecta ao agente)

## Arquivos Criados/Modificados

| Arquivo | Acao |
|---------|------|
| `app/tools/memoria.py` | Criar |
| `app/services/embedding.py` | Criar |
| `app/services/agente.py` | Modificar |
| `app/core/prompts.py` | Modificar |
| `app/core/config.py` | Adicionar VOYAGE_API_KEY |
| `pyproject.toml` | Adicionar voyageai |

## Validacao Final

```python
@pytest.mark.integration
async def test_fluxo_completo_salvar_memoria():
    """
    Simula conversa onde medico menciona preferencia.

    1. Medico: "Oi Julia, prefiro fazer plantoes noturnos por causa dos meus filhos"
    2. Julia: chama salvar_memoria(tipo="preferencia", conteudo="...")
    3. Julia: responde naturalmente
    4. Verificar: memoria salva em doctor_context
    5. Proxima conversa: memoria aparece no contexto
    """
    pass
```
