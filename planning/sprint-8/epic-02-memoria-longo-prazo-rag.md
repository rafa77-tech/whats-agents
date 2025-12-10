# Epic 02: Memoria de Longo Prazo (RAG)

## Prioridade: P0 (Critico)

## Objetivo

> **Implementar busca semantica no doctor_context para que Julia lembre informacoes de conversas anteriores.**

Atualmente, mesmo com a tool salvar_memoria (Epic 01), a Julia nao consulta essas memorias. Este epic fecha o ciclo: salvar -> buscar -> usar no contexto.

---

## Problema

Sem RAG implementado:
1. Memorias sao salvas mas nunca consultadas
2. Julia "esquece" tudo entre conversas
3. Experiencia parece robos sem continuidade
4. Medico precisa repetir preferencias toda vez

---

## Fluxo Desejado

```
CONVERSA ANTERIOR (salvo em doctor_context):
- "Prefere plantoes noturnos por causa dos filhos"
- "Nao gosta do Hospital Sao Luiz"
- "Mora em Santo Andre"

NOVA CONVERSA:
Medico: "Oi Julia, tem alguma vaga pra mim?"
        │
        ▼
┌──────────────────────────────────────┐
│ 1. Gera embedding da mensagem        │
│ 2. Busca memorias similares          │
│ 3. Retorna top 5 mais relevantes     │
└──────────────────────────────────────┘
        │
        ▼
CONTEXTO ENRIQUECIDO:
- Mensagem: "Oi Julia, tem alguma vaga pra mim?"
- Memorias relevantes:
  * "Prefere plantoes noturnos por causa dos filhos"
  * "Mora em Santo Andre"
        │
        ▼
JULIA RESPONDE:
"Oi! Deixa eu ver aqui... achei uma vaga noturna no Hospital Brasil,
fica pertinho de Santo Andre! O que acha?"
```

---

## Stories

---

# S8.E2.1 - Criar funcao de busca semantica

## Objetivo

> **Implementar busca por similaridade no doctor_context usando pgvector.**

## Contexto Tecnico

Supabase ja tem pgvector habilitado. Precisamos:
1. Criar funcao SQL para busca por similaridade
2. Criar wrapper Python para chamar a funcao
3. Retornar memorias ordenadas por relevancia

## Codigo Esperado

**Migration SQL:** `20251208_busca_semantica_doctor_context.sql`

```sql
-- Funcao para buscar memorias similares
CREATE OR REPLACE FUNCTION buscar_memorias_similares(
    p_cliente_id UUID,
    p_embedding vector(1024),  -- Voyage AI usa 1024 dimensoes
    p_limite INT DEFAULT 5,
    p_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    tipo VARCHAR(50),
    similaridade FLOAT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.content,
        dc.tipo,
        1 - (dc.embedding <=> p_embedding) AS similaridade,
        dc.created_at
    FROM doctor_context dc
    WHERE dc.cliente_id = p_cliente_id
      AND dc.embedding IS NOT NULL
      AND 1 - (dc.embedding <=> p_embedding) >= p_threshold
    ORDER BY dc.embedding <=> p_embedding
    LIMIT p_limite;
END;
$$;

-- Indice para busca eficiente
CREATE INDEX IF NOT EXISTS idx_doctor_context_embedding
ON doctor_context
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Indice para filtro por cliente
CREATE INDEX IF NOT EXISTS idx_doctor_context_cliente
ON doctor_context (cliente_id);
```

**Arquivo:** `app/services/memoria.py`

```python
"""
Servico de memoria de longo prazo usando RAG.
"""
import logging
from typing import Optional

from app.services.supabase import get_supabase
from app.services.embedding import gerar_embedding

logger = logging.getLogger(__name__)


async def buscar_memorias_relevantes(
    cliente_id: str,
    mensagem: str,
    limite: int = 5,
    threshold: float = 0.7  # Threshold mais alto para evitar memorias irrelevantes
) -> list[dict]:
    """
    Busca memorias relevantes para uma mensagem.

    Args:
        cliente_id: ID do medico
        mensagem: Mensagem atual da conversa
        limite: Maximo de memorias a retornar
        threshold: Similaridade minima (0-1)

    Returns:
        Lista de memorias ordenadas por relevancia
    """
    try:
        # Gerar embedding da mensagem
        embedding = await gerar_embedding(mensagem)

        if not embedding:
            logger.warning("Nao foi possivel gerar embedding para busca")
            return []

        # Chamar funcao do Supabase
        supabase = get_supabase()
        response = supabase.rpc(
            "buscar_memorias_similares",
            {
                "p_cliente_id": cliente_id,
                "p_embedding": embedding,
                "p_limite": limite,
                "p_threshold": threshold
            }
        ).execute()

        if response.data:
            logger.info(
                f"Encontradas {len(response.data)} memorias "
                f"para cliente {cliente_id[:8]}"
            )
            return response.data

        return []

    except Exception as e:
        logger.error(f"Erro ao buscar memorias: {e}")
        return []


async def buscar_memorias_por_tipo(
    cliente_id: str,
    tipo: str,
    limite: int = 10
) -> list[dict]:
    """
    Busca memorias de um tipo especifico (sem semantica).

    Util para carregar todas as preferencias ou restricoes.

    Args:
        cliente_id: ID do medico
        tipo: Tipo de memoria (preferencia, restricao, etc)
        limite: Maximo de memorias

    Returns:
        Lista de memorias do tipo especificado
    """
    try:
        supabase = get_supabase()
        response = (
            supabase.table("doctor_context")
            .select("id, content, tipo, created_at")
            .eq("cliente_id", cliente_id)
            .eq("tipo", tipo)
            .order("created_at", desc=True)
            .limit(limite)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar memorias por tipo: {e}")
        return []


async def carregar_contexto_medico_completo(cliente_id: str) -> dict:
    """
    Carrega todo o contexto disponivel do medico.

    Returns:
        Dict com:
        - preferencias: lista de preferencias
        - restricoes: lista de restricoes
        - info_pessoal: lista de infos pessoais
        - disponibilidade: lista de disponibilidades
    """
    try:
        # Buscar todos os tipos em paralelo
        import asyncio

        preferencias, restricoes, info_pessoal, disponibilidade = await asyncio.gather(
            buscar_memorias_por_tipo(cliente_id, "preferencia"),
            buscar_memorias_por_tipo(cliente_id, "restricao"),
            buscar_memorias_por_tipo(cliente_id, "info_pessoal"),
            buscar_memorias_por_tipo(cliente_id, "disponibilidade"),
        )

        return {
            "preferencias": [m["content"] for m in preferencias],
            "restricoes": [m["content"] for m in restricoes],
            "info_pessoal": [m["content"] for m in info_pessoal],
            "disponibilidade": [m["content"] for m in disponibilidade],
        }

    except Exception as e:
        logger.error(f"Erro ao carregar contexto completo: {e}")
        return {
            "preferencias": [],
            "restricoes": [],
            "info_pessoal": [],
            "disponibilidade": [],
        }
```

## Criterios de Aceite

1. **Funcao SQL criada:** `buscar_memorias_similares` funciona
2. **Indice criado:** Busca eficiente com ivfflat
3. **Threshold respeitado:** Nao retorna memorias irrelevantes
4. **Ordenacao correta:** Mais similar primeiro
5. **Fallback gracioso:** Retorna lista vazia se erro

## DoD

- [ ] Migration SQL executada no Supabase
- [ ] Funcao `buscar_memorias_relevantes()` implementada
- [ ] Funcao `buscar_memorias_por_tipo()` implementada
- [ ] Funcao `carregar_contexto_medico_completo()` implementada
- [ ] Indice ivfflat criado para performance
- [ ] Logs de quantidade de memorias encontradas
- [ ] Tratamento de erro quando embedding falha

## Testes

```python
@pytest.mark.asyncio
async def test_buscar_memorias_relevantes():
    # Precisa de medico com memorias salvas
    cliente_id = "123"
    mensagem = "tem vaga noturna?"

    memorias = await buscar_memorias_relevantes(cliente_id, mensagem)

    # Deve retornar lista (pode ser vazia se nao tiver dados)
    assert isinstance(memorias, list)

@pytest.mark.asyncio
async def test_buscar_memorias_por_tipo():
    cliente_id = "123"

    memorias = await buscar_memorias_por_tipo(cliente_id, "preferencia")

    assert isinstance(memorias, list)
    for m in memorias:
        assert m["tipo"] == "preferencia"
```

---

# S8.E2.2 - Integrar RAG no contexto do agente

## Objetivo

> **Modificar montagem de contexto para incluir memorias relevantes.**

## Contexto Tecnico

O arquivo `app/services/contexto.py` monta o contexto enviado ao LLM. Precisamos:
1. Buscar memorias relevantes para a mensagem atual
2. Formatar memorias para o prompt
3. Incluir no contexto sem poluir demais

## Codigo Esperado

**Arquivo:** `app/services/contexto.py` (modificar)

```python
from app.services.memoria import (
    buscar_memorias_relevantes,
    carregar_contexto_medico_completo
)


async def montar_contexto_completo(
    medico: dict,
    conversa: dict,
    vagas: list[dict] = None,
    mensagem_atual: str = ""  # NOVO PARAMETRO
) -> dict:
    """
    Monta contexto completo para o agente.

    Args:
        medico: Dados do medico
        conversa: Dados da conversa
        vagas: Lista de vagas disponiveis (opcional)
        mensagem_atual: Mensagem do medico para busca semantica

    Returns:
        Dict com todos os contextos formatados
    """
    # ... codigo existente ...

    # NOVO: Buscar memorias de longo prazo
    memorias_contexto = ""
    if mensagem_atual:
        # Busca semantica baseada na mensagem
        memorias_relevantes = await buscar_memorias_relevantes(
            cliente_id=medico["id"],
            mensagem=mensagem_atual,
            limite=5,
            threshold=0.7  # Threshold mais alto para evitar ruido
        )

        if memorias_relevantes:
            memorias_contexto = formatar_memorias_para_prompt(memorias_relevantes)

    # Se nao encontrou por semantica, carrega contexto geral
    if not memorias_contexto:
        contexto_completo = await carregar_contexto_medico_completo(medico["id"])
        memorias_contexto = formatar_contexto_completo_para_prompt(contexto_completo)

    return {
        "medico": contexto_medico_str,
        "especialidade": contexto_especialidade_str,
        "historico": historico,
        "historico_raw": historico_raw,
        "vagas": formatar_contexto_vagas(vagas) if vagas else "",
        "primeira_msg": primeira_msg,
        "controlled_by": conversa.get("controlled_by", "ai"),
        "data_hora_atual": agora.strftime("%Y-%m-%d %H:%M"),
        "dia_semana": dia_semana,
        "handoff_recente": contexto_handoff,
        "diretrizes": contexto_diretrizes,
        "memorias": memorias_contexto,  # NOVO
    }


def formatar_memorias_para_prompt(memorias: list[dict]) -> str:
    """
    Formata memorias para incluir no prompt.

    Formato conciso e util para o LLM.
    """
    if not memorias:
        return ""

    linhas = ["## Informacoes que voce ja sabe sobre este medico:"]

    for m in memorias:
        tipo = m.get("tipo", "info")
        conteudo = m.get("content", "")
        similaridade = m.get("similaridade", 0)

        # So inclui se similaridade razoavel (threshold 0.7)
        if similaridade >= 0.7:
            emoji = {
                "preferencia": "👍",
                "restricao": "🚫",
                "info_pessoal": "ℹ️",
                "disponibilidade": "📅"
            }.get(tipo, "•")

            linhas.append(f"{emoji} {conteudo}")

    if len(linhas) == 1:  # So tem o header
        return ""

    linhas.append("")
    linhas.append("Use essas informacoes para personalizar sua resposta.")

    return "\n".join(linhas)


def formatar_contexto_completo_para_prompt(contexto: dict) -> str:
    """
    Formata contexto completo (quando nao tem busca semantica).
    """
    linhas = []

    if contexto.get("preferencias"):
        linhas.append("**Preferencias conhecidas:**")
        for p in contexto["preferencias"][:3]:  # Limita a 3
            linhas.append(f"- {p}")

    if contexto.get("restricoes"):
        linhas.append("\n**Restricoes:**")
        for r in contexto["restricoes"][:3]:
            linhas.append(f"- {r}")

    if contexto.get("info_pessoal"):
        linhas.append("\n**Info pessoal:**")
        for i in contexto["info_pessoal"][:2]:
            linhas.append(f"- {i}")

    if contexto.get("disponibilidade"):
        linhas.append("\n**Disponibilidade:**")
        for d in contexto["disponibilidade"][:2]:
            linhas.append(f"- {d}")

    if not linhas:
        return ""

    return "\n".join(linhas)
```

## Criterios de Aceite

1. **Busca semantica ativada:** Mensagem atual usada para buscar
2. **Fallback funciona:** Se semantica falha, carrega contexto geral
3. **Formatacao concisa:** Nao polui prompt com memorias demais
4. **Limite respeitado:** Maximo 5 memorias por busca
5. **Threshold minimo:** Nao inclui memorias irrelevantes

## DoD

- [ ] Parametro `mensagem_atual` adicionado em `montar_contexto_completo()`
- [ ] Busca semantica integrada
- [ ] Fallback para contexto geral implementado
- [ ] Funcao `formatar_memorias_para_prompt()` criada
- [ ] Funcao `formatar_contexto_completo_para_prompt()` criada
- [ ] Limite de memorias respeitado
- [ ] Campo "memorias" adicionado no retorno

## Testes

```python
@pytest.mark.asyncio
async def test_contexto_inclui_memorias():
    medico = {"id": "123", "primeiro_nome": "Carlos"}
    conversa = {"id": "456", "controlled_by": "ai"}

    contexto = await montar_contexto_completo(
        medico, conversa,
        mensagem_atual="tem vaga noturna?"
    )

    assert "memorias" in contexto
    # Pode ser string vazia se medico nao tem memorias
    assert isinstance(contexto["memorias"], str)
```

---

# S8.E2.3 - Atualizar prompt para usar memorias

## Objetivo

> **Modificar system prompt para instruir Julia a usar as memorias.**

## Contexto Tecnico

O LLM precisa saber:
1. Que tem memorias disponiveis no contexto
2. Como usar essas memorias para personalizar resposta
3. Quando mencionar que "lembrou" algo

## Codigo Esperado

**Arquivo:** `app/core/prompts.py` (adicionar secao)

```python
INSTRUCOES_MEMORIAS = """
## Memoria do Medico

Voce pode ter acesso a informacoes que ja sabe sobre este medico (preferencias, restricoes, etc).
Essas informacoes aparecem na secao "Informacoes que voce ja sabe sobre este medico".

COMO USAR:
1. Leia as memorias ANTES de responder
2. Use para personalizar sua resposta
3. NAO repita as memorias literalmente
4. Demonstre que conhece o medico naturalmente

EXEMPLOS:

Se voce sabe que medico prefere noturno:
- BOM: "Achei uma vaga noturna que combina com vc!"
- RUIM: "De acordo com minhas anotacoes, voce prefere plantoes noturnos..."

Se voce sabe que medico nao gosta de um hospital:
- BOM: [Nao oferecer vagas desse hospital]
- RUIM: "Sei que vc nao gosta do Hospital X, entao..."

Se voce sabe info pessoal:
- BOM: "Essa vaga e pertinho de Santo Andre, fica facil pra vc"
- RUIM: "Como voce mora em Santo Andre..."

REGRA DE OURO: Use a informacao para AGIR, nao para MOSTRAR que sabe.
"""
```

**Arquivo:** `app/core/prompts.py` (modificar montar_prompt_julia)

```python
def montar_prompt_julia(
    contexto_medico: str = "",
    contexto_vagas: str = "",
    historico: str = "",
    primeira_msg: bool = False,
    data_hora_atual: str = "",
    dia_semana: str = "",
    contexto_especialidade: str = "",
    contexto_handoff: str = "",
    memorias: str = ""  # NOVO PARAMETRO
) -> str:
    """Monta o system prompt completo para a Julia."""
    contexto_parts = []

    # ... codigo existente ...

    # NOVO: Adicionar memorias se existirem
    if memorias:
        contexto_parts.append(memorias)

    contexto = "\n\n".join(contexto_parts) if contexto_parts else "Nenhum contexto adicional."

    # Adicionar instrucoes de memoria ao prompt
    prompt = JULIA_SYSTEM_PROMPT.format(contexto=contexto)
    prompt += "\n\n" + INSTRUCOES_MEMORIAS

    # ... resto do codigo ...
```

## Criterios de Aceite

1. **Instrucoes claras:** LLM entende como usar memorias
2. **Exemplos concretos:** Mostra uso correto vs incorreto
3. **Naturalidade:** Instrui a nao parecer robos lendo anotacoes
4. **Integracao:** Memorias aparecem no contexto formatado

## DoD

- [ ] Constante `INSTRUCOES_MEMORIAS` adicionada
- [ ] Parametro `memorias` adicionado em `montar_prompt_julia()`
- [ ] Memorias incluidas no contexto do prompt
- [ ] Instrucoes explicam como usar naturalmente
- [ ] Exemplos de uso correto e incorreto

## Teste Manual

```
SETUP: Medico com memoria "Prefere plantoes noturnos por causa dos filhos"

INPUT: "Oi Julia, tem alguma vaga pra mim?"

ESPERADO (BOM):
"Oi Dr Carlos! Tenho uma vaga noturna no Hospital Brasil, sabado.
Acho que combina com vc! Quer saber mais?"

NAO ESPERADO (RUIM):
"Oi Dr Carlos! Vi aqui nas minhas anotacoes que voce prefere
plantoes noturnos. Tenho uma vaga..."
```

---

# S8.E2.4 - Atualizar chamada do agente

## Objetivo

> **Passar mensagem atual para montagem de contexto.**

## Contexto Tecnico

O `processar_mensagem_completo` em `agente.py` precisa passar a mensagem para o contexto poder fazer busca semantica.

## Codigo Esperado

**Arquivo:** `app/services/agente.py` (modificar)

```python
async def processar_mensagem_completo(
    mensagem_texto: str,
    medico: dict,
    conversa: dict,
    vagas: list[dict] = None
) -> Optional[str]:
    """
    Processa mensagem completa: monta contexto e gera resposta.
    """
    from app.services.contexto import montar_contexto_completo

    try:
        # Verificar se conversa esta sob controle da IA
        if conversa.get("controlled_by") != "ai":
            logger.info("Conversa sob controle humano, nao processando")
            return None

        # Montar contexto COM a mensagem para RAG
        contexto = await montar_contexto_completo(
            medico,
            conversa,
            vagas,
            mensagem_atual=mensagem_texto  # NOVO: passa mensagem
        )

        # Gerar resposta
        resposta = await gerar_resposta_julia(
            mensagem_texto,
            contexto,
            medico=medico,
            conversa=conversa
        )

        return resposta

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        return None
```

**Arquivo:** `app/services/agente.py` (modificar gerar_resposta_julia)

```python
async def gerar_resposta_julia(
    mensagem: str,
    contexto: dict,
    medico: dict,
    conversa: dict,
    incluir_historico: bool = True,
    usar_tools: bool = True
) -> str:
    """Gera resposta da Julia para uma mensagem."""

    # Montar system prompt COM memorias
    system_prompt = montar_prompt_julia(
        contexto_medico=contexto.get("medico", ""),
        contexto_vagas=contexto.get("vagas", ""),
        historico=contexto.get("historico", ""),
        primeira_msg=contexto.get("primeira_msg", False),
        data_hora_atual=contexto.get("data_hora_atual", ""),
        dia_semana=contexto.get("dia_semana", ""),
        contexto_especialidade=contexto.get("especialidade", ""),
        contexto_handoff=contexto.get("handoff_recente", ""),
        memorias=contexto.get("memorias", "")  # NOVO
    )

    # ... resto do codigo ...
```

## Criterios de Aceite

1. **Mensagem passada:** `mensagem_atual` chega em `montar_contexto_completo`
2. **Memorias no prompt:** Campo `memorias` passado para `montar_prompt_julia`
3. **Fluxo completo:** Mensagem -> Busca RAG -> Contexto -> Prompt -> Resposta

## DoD

- [ ] `processar_mensagem_completo` passa `mensagem_atual`
- [ ] `gerar_resposta_julia` passa `memorias` para prompt
- [ ] Fluxo end-to-end testado
- [ ] Logs mostram memorias encontradas

---

# S8.E2.5 - Extrator de fatos pos-conversa

## Objetivo

> **Criar job que extrai fatos importantes ao final de cada conversa.**

## Contexto Tecnico

Alem de salvar via tool durante a conversa, queremos extrair fatos automaticamente ao final. Isso captura informacoes que a Julia nao salvou explicitamente.

## Codigo Esperado

**Arquivo:** `app/services/memoria.py` (adicionar)

```python
async def extrair_fatos_conversa(conversa_id: str) -> list[dict]:
    """
    Extrai fatos importantes de uma conversa finalizada.

    Usa LLM para identificar preferencias, restricoes e infos
    que devem ser lembradas.

    Args:
        conversa_id: ID da conversa

    Returns:
        Lista de fatos extraidos
    """
    from app.services.interacao import carregar_historico
    from app.services.llm import gerar_resposta

    try:
        # Carregar historico completo
        historico = await carregar_historico(conversa_id, limite=50)

        if len(historico) < 4:  # Conversa muito curta
            return []

        # Formatar historico
        historico_texto = "\n".join([
            f"{'Medico' if i['autor_tipo'] == 'medico' else 'Julia'}: {i['conteudo']}"
            for i in historico
        ])

        # Prompt para extracao
        prompt_extracao = """Analise esta conversa entre Julia (escalista) e um medico.

Extraia APENAS fatos importantes para lembrar em conversas futuras:
- Preferencias de plantao (horarios, valores, regioes)
- Restricoes (dias, hospitais, tipos de plantao)
- Informacoes pessoais relevantes (familia, cidade)
- Disponibilidade mencionada

NAO extraia:
- Detalhes da conversa atual
- Informacoes temporarias
- Coisas obvias (nome, especialidade)

Retorne em JSON:
{
    "fatos": [
        {"tipo": "preferencia|restricao|info_pessoal|disponibilidade", "conteudo": "..."},
        ...
    ]
}

Se nao houver fatos relevantes, retorne: {"fatos": []}

CONVERSA:
"""

        resposta = await gerar_resposta(
            mensagem=historico_texto,
            system_prompt=prompt_extracao,
            max_tokens=500
        )

        # Parsear JSON
        import json
        try:
            dados = json.loads(resposta)
            return dados.get("fatos", [])
        except json.JSONDecodeError:
            logger.warning(f"Resposta nao e JSON valido: {resposta[:100]}")
            return []

    except Exception as e:
        logger.error(f"Erro ao extrair fatos: {e}")
        return []


async def salvar_fatos_extraidos(cliente_id: str, conversa_id: str, fatos: list[dict]):
    """
    Salva fatos extraidos no doctor_context.
    """
    from app.services.embedding import gerar_embedding

    supabase = get_supabase()

    for fato in fatos:
        tipo = fato.get("tipo")
        conteudo = fato.get("conteudo")

        if not tipo or not conteudo:
            continue

        # Verificar duplicata
        existente = await _verificar_memoria_existente(cliente_id, tipo, conteudo)
        if existente:
            continue

        # Gerar embedding
        embedding = await gerar_embedding(conteudo)

        # Salvar
        supabase.table("doctor_context").insert({
            "cliente_id": cliente_id,
            "content": conteudo,
            "embedding": embedding,
            "source": "extraction",  # Diferencia de 'conversation'
            "tipo": tipo,
            "conversa_id": conversa_id
        }).execute()

    logger.info(f"Salvos {len(fatos)} fatos extraidos para {cliente_id[:8]}")
```

**Arquivo:** `app/workers/scheduler.py` (adicionar job)

```python
async def job_extrair_fatos_conversas():
    """
    Job que extrai fatos de conversas finalizadas nas ultimas 24h.

    Roda 1x por dia as 23h.
    """
    from app.services.memoria import extrair_fatos_conversa, salvar_fatos_extraidos
    from app.services.supabase import get_supabase

    supabase = get_supabase()

    # Buscar conversas finalizadas hoje que ainda nao foram processadas
    response = (
        supabase.table("conversations")
        .select("id, cliente_id")
        .eq("status", "completed")
        .gte("updated_at", (datetime.utcnow() - timedelta(hours=24)).isoformat())
        .is_("fatos_extraidos", False)  # Campo para controle
        .limit(50)
        .execute()
    )

    for conversa in response.data or []:
        try:
            fatos = await extrair_fatos_conversa(conversa["id"])

            if fatos:
                await salvar_fatos_extraidos(
                    conversa["cliente_id"],
                    conversa["id"],
                    fatos
                )

            # Marcar como processada
            supabase.table("conversations").update({
                "fatos_extraidos": True
            }).eq("id", conversa["id"]).execute()

        except Exception as e:
            logger.error(f"Erro ao processar conversa {conversa['id']}: {e}")

    logger.info(f"Job extracao concluido: {len(response.data or [])} conversas")
```

## Criterios de Aceite

1. **Extracao funciona:** LLM identifica fatos relevantes
2. **JSON valido:** Parseia resposta corretamente
3. **Sem duplicatas:** Verifica antes de salvar
4. **Source diferente:** Fatos extraidos marcados como 'extraction'
5. **Job agendado:** Roda diariamente as 23h

## DoD

- [ ] Funcao `extrair_fatos_conversa()` implementada
- [ ] Funcao `salvar_fatos_extraidos()` implementada
- [ ] Job `job_extrair_fatos_conversas()` agendado
- [ ] Campo `fatos_extraidos` na tabela conversations
- [ ] Prompt de extracao retorna JSON valido
- [ ] Duplicatas evitadas
- [ ] Logs de quantidade de fatos extraidos

---

## Resumo do Epic

| Story | Descricao | Complexidade |
|-------|-----------|--------------|
| S8.E2.1 | Busca semantica | Alta |
| S8.E2.2 | Integrar no contexto | Media |
| S8.E2.3 | Atualizar prompt | Baixa |
| S8.E2.4 | Atualizar agente | Baixa |
| S8.E2.5 | Extrator de fatos | Alta |

## Ordem de Implementacao

1. S8.E2.1 - Busca semantica (base para tudo)
2. S8.E2.2 - Integrar no contexto (usa busca)
3. S8.E2.3 - Atualizar prompt (instrucoes)
4. S8.E2.4 - Atualizar agente (conecta tudo)
5. S8.E2.5 - Extrator (bonus, pode ser depois)

## Arquivos Criados/Modificados

| Arquivo | Acao |
|---------|------|
| `app/services/memoria.py` | Criar |
| `app/services/contexto.py` | Modificar |
| `app/services/agente.py` | Modificar |
| `app/core/prompts.py` | Modificar |
| `app/workers/scheduler.py` | Modificar |
| Migration SQL | Criar |

## Validacao Final

```python
@pytest.mark.integration
async def test_fluxo_completo_rag():
    """
    Testa fluxo completo de memoria.

    1. Conversa anterior: medico disse "prefiro noturno"
    2. Tool salvar_memoria foi chamada
    3. Nova conversa: medico pergunta "tem vaga?"
    4. RAG busca memoria "prefiro noturno"
    5. Julia oferece vaga noturna primeiro
    """
    pass
```
