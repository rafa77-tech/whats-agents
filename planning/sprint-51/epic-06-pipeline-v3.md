# Epic 6: Pipeline de Grupos v3 (Enterprise-Grade)

**Status:** 📋 Planejado
**Sprint Alvo:** 52+
**Dependencias:** Epic 2 (Correcoes v2) deve ser concluido primeiro

---

## Sumario Executivo

O pipeline atual (v2) possui 7 estagios sequenciais, multiplas chamadas LLM, e problemas de observabilidade. A v3 propoe uma arquitetura simplificada com 4 estagios, uma unica chamada LLM unificada, dedup no inicio (antes de gastar tokens), e observabilidade completa.

---

## Problemas do Pipeline Atual (v2)

| Problema | Impacto | Custo |
|----------|---------|-------|
| 7 estagios sequenciais | Latencia alta (~5-10s/mensagem) | Experiencia |
| 2 chamadas LLM (classificacao + extracao) | Custo dobrado de tokens | ~$0.003/msg |
| Dedup no final (estagio 5) | Tokens gastos em duplicatas | ~30% desperdicado |
| Sem trace_id | Impossivel rastrear mensagem end-to-end | Debug |
| Logs nao estruturados | Dificil monitorar e alertar | Operacao |
| Modelo de dados fragmentado | 5 tabelas para uma vaga | Complexidade |
| Especialidades nao extraidas | 100% descarte na normalizacao | Zero output |

---

## Arquitetura Proposta v3

### Pipeline Simplificado (4 Estagios)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PIPELINE v3                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ENTRADA                                                             │
│     │                                                                │
│     ▼                                                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ESTAGIO 1: INGESTAO + DEDUP PRECOCE                          │   │
│  │                                                               │   │
│  │  1. Recebe mensagem do webhook                                │   │
│  │  2. Gera content_hash (MD5 do texto normalizado)              │   │
│  │  3. Verifica duplicata no Redis/banco (TTL 24h)               │   │
│  │  4. Se duplicata → PARA (nao gasta tokens)                    │   │
│  │  5. Se nova → Persiste e enfileira                            │   │
│  │                                                               │   │
│  │  Output: mensagem_id, trace_id                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│     │                                                                │
│     ▼                                                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ESTAGIO 2: HEURISTICA (FILTRO RAPIDO)                        │   │
│  │                                                               │   │
│  │  1. Aplica regex e keywords                                   │   │
│  │  2. Score < 0.3 → DESCARTA (nao e oferta)                     │   │
│  │  3. Score >= 0.3 → Continua                                   │   │
│  │                                                               │   │
│  │  Tempo: <5ms                                                  │   │
│  │  Output: score, keywords_matched                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│     │                                                                │
│     ▼                                                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ESTAGIO 3: LLM UNIFICADO (CLASSIFICA + EXTRAI)               │   │
│  │                                                               │   │
│  │  UMA UNICA CHAMADA LLM QUE:                                   │
│  │  1. Classifica se e oferta de plantao                         │   │
│  │  2. Se sim, extrai TODOS os campos estruturados               │   │
│  │  3. Retorna JSON tipado                                       │   │
│  │                                                               │   │
│  │  Modelo: claude-3-haiku (default) ou sonnet (config)          │   │
│  │  Tempo: 200-500ms                                             │   │
│  │  Custo: ~$0.001/msg                                           │   │
│  │  Output: ResultadoLLMUnificado                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│     │                                                                │
│     ▼                                                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ ESTAGIO 4: PERSISTENCIA + NORMALIZACAO                       │   │
│  │                                                               │   │
│  │  1. Normaliza entidades (hospital, especialidade)             │   │
│  │  2. Valida campos obrigatorios                                │   │
│  │  3. Persiste em tabela unica (pipeline_vagas)                 │   │
│  │  4. Atualiza metricas e emite eventos                         │   │
│  │                                                                │   │
│  │  Output: vaga_id, status_final                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│     │                                                                │
│     ▼                                                                │
│  SAIDA: Vaga pronta para uso                                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Comparacao v2 vs v3

| Aspecto | v2 (Atual) | v3 (Proposto) |
|---------|------------|---------------|
| Estagios | 7 | 4 |
| Chamadas LLM | 2 | 1 |
| Dedup | Final (estagio 5) | Inicio (estagio 1) |
| Tempo total | 5-10s | 1-2s |
| Custo/msg | ~$0.003 | ~$0.001 |
| Trace | Nenhum | trace_id completo |
| Tabelas | 5+ | 1 principal |

---

## Story 1: Modelo de Dados Simplificado

**Prioridade:** P0
**Estimativa:** 3 pontos

### Objetivo

Uma unica tabela principal (`pipeline_vagas`) com todos os dados necessarios, eliminando JOINs complexos e fragmentacao.

### Schema SQL

```sql
-- =============================================================================
-- TABELA PRINCIPAL: pipeline_vagas
-- =============================================================================
--
-- Substitui: mensagens_grupo + vagas_grupo + vagas_grupo_fontes
-- Mantem historico completo em uma unica linha
-- =============================================================================

CREATE TABLE IF NOT EXISTS pipeline_vagas (
    -- Identificadores
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL,  -- Rastreabilidade end-to-end

    -- Origem
    grupo_jid TEXT NOT NULL,
    grupo_nome TEXT,
    sender_jid TEXT NOT NULL,
    sender_nome TEXT,
    mensagem_raw TEXT NOT NULL,
    mensagem_timestamp TIMESTAMPTZ NOT NULL,

    -- Deduplicacao (precoce)
    content_hash TEXT NOT NULL,  -- MD5 do texto normalizado
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of UUID REFERENCES pipeline_vagas(id),

    -- Heuristica
    heuristica_score NUMERIC(3,2),
    heuristica_keywords JSONB,
    heuristica_passed BOOLEAN,
    heuristica_at TIMESTAMPTZ,

    -- LLM Unificado
    llm_is_oferta BOOLEAN,
    llm_confidence NUMERIC(3,2),
    llm_model TEXT,
    llm_tokens_in INTEGER,
    llm_tokens_out INTEGER,
    llm_latency_ms INTEGER,
    llm_at TIMESTAMPTZ,

    -- Dados Extraidos (flattened - sem JSONB aninhado)
    hospital_raw TEXT,
    hospital_id UUID REFERENCES hospitais(id),
    hospital_confianca NUMERIC(3,2),

    especialidade_raw TEXT,
    especialidade_id UUID REFERENCES especialidades(id),
    especialidade_confianca NUMERIC(3,2),

    data_plantao DATE,
    dia_semana TEXT,
    periodo TEXT,  -- manha, tarde, noite, diurno, noturno, cinderela
    hora_inicio TIME,
    hora_fim TIME,

    valor INTEGER,
    valor_tipo TEXT CHECK (valor_tipo IN ('fixo', 'faixa', 'a_combinar')),
    valor_minimo INTEGER,
    valor_maximo INTEGER,

    contato_nome TEXT,
    contato_whatsapp TEXT,

    -- Normalizacao
    normalizacao_status TEXT,
    normalizacao_erros JSONB,
    normalizacao_at TIMESTAMPTZ,

    -- Status Final
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',           -- Aguardando processamento
        'duplicate',         -- Duplicata detectada (estagio 1)
        'filtered',          -- Filtrado pela heuristica (estagio 2)
        'not_offer',         -- Nao e oferta (LLM, estagio 3)
        'extraction_failed', -- Falha na extracao (estagio 3)
        'validation_failed', -- Falha na validacao (estagio 4)
        'ready',             -- Pronta para uso
        'imported',          -- Importada para sistema principal
        'error'              -- Erro nao tratado
    )),
    status_reason TEXT,

    -- Metricas
    processing_time_ms INTEGER,  -- Tempo total do pipeline
    retry_count INTEGER DEFAULT 0,

    -- Auditoria
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,

    -- Indices
    CONSTRAINT uq_content_hash_24h UNIQUE (content_hash, DATE(mensagem_timestamp))
);

-- Indices para performance
CREATE INDEX idx_pipeline_vagas_status ON pipeline_vagas(status);
CREATE INDEX idx_pipeline_vagas_trace_id ON pipeline_vagas(trace_id);
CREATE INDEX idx_pipeline_vagas_content_hash ON pipeline_vagas(content_hash);
CREATE INDEX idx_pipeline_vagas_created_at ON pipeline_vagas(created_at DESC);
CREATE INDEX idx_pipeline_vagas_grupo_jid ON pipeline_vagas(grupo_jid);
CREATE INDEX idx_pipeline_vagas_data_plantao ON pipeline_vagas(data_plantao);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_pipeline_vagas_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_pipeline_vagas_updated_at
    BEFORE UPDATE ON pipeline_vagas
    FOR EACH ROW
    EXECUTE FUNCTION update_pipeline_vagas_updated_at();

-- =============================================================================
-- VIEW: Metricas Agregadas por Dia
-- =============================================================================

CREATE OR REPLACE VIEW v_pipeline_metricas_diarias AS
SELECT
    DATE(created_at) as data,
    COUNT(*) as total_mensagens,
    COUNT(*) FILTER (WHERE is_duplicate) as duplicatas,
    COUNT(*) FILTER (WHERE status = 'filtered') as filtradas,
    COUNT(*) FILTER (WHERE status = 'not_offer') as nao_ofertas,
    COUNT(*) FILTER (WHERE status = 'ready') as prontas,
    COUNT(*) FILTER (WHERE status = 'error') as erros,
    AVG(processing_time_ms) as tempo_medio_ms,
    SUM(llm_tokens_in + llm_tokens_out) as tokens_total,
    AVG(llm_latency_ms) as llm_latency_avg_ms
FROM pipeline_vagas
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY data DESC;

-- =============================================================================
-- VIEW: Fontes por Vaga (para compatibilidade)
-- =============================================================================

CREATE OR REPLACE VIEW v_pipeline_vagas_fontes AS
SELECT
    p.id as vaga_id,
    p.hospital_raw,
    p.especialidade_raw,
    p.data_plantao,
    p.valor,
    COUNT(d.id) + 1 as qtd_fontes,
    ARRAY_AGG(DISTINCT d.grupo_jid) FILTER (WHERE d.grupo_jid IS NOT NULL) as grupos
FROM pipeline_vagas p
LEFT JOIN pipeline_vagas d ON d.duplicate_of = p.id
WHERE p.is_duplicate = FALSE
GROUP BY p.id, p.hospital_raw, p.especialidade_raw, p.data_plantao, p.valor;
```

### Criterios de Aceite

- [ ] Tabela `pipeline_vagas` criada em producao
- [ ] Indices otimizados para queries frequentes
- [ ] Views de metricas funcionando
- [ ] Migracao de dados historicos planejada

---

## Story 2: Dedup Precoce (Estagio 1)

**Prioridade:** P0
**Estimativa:** 2 pontos

### Objetivo

Detectar duplicatas ANTES de gastar tokens com LLM. Economia estimada: ~30% dos custos atuais.

### Implementacao

```python
# app/services/grupos_v3/dedup_precoce.py

import hashlib
import re
from datetime import datetime, timedelta, UTC
from typing import Optional, Tuple
from uuid import UUID, uuid4

from app.core.logging import get_logger
from app.services.redis import cache_get, cache_set
from app.services.supabase import supabase

logger = get_logger(__name__)

# Configuracao
DEDUP_TTL_HORAS = 24
DEDUP_CACHE_PREFIX = "pipeline:dedup:"


def normalizar_texto_para_hash(texto: str) -> str:
    """
    Normaliza texto antes de calcular hash.

    Remove:
    - Espacos extras
    - Acentos
    - Emojis
    - Horarios variaveis
    - Numeros de contato
    """
    texto = texto.lower()

    # Remove espacos multiplos
    texto = re.sub(r'\s+', ' ', texto)

    # Remove emojis (mantendo texto)
    texto = re.sub(r'[\U00010000-\U0010ffff]', '', texto)

    # Remove telefones (variam por mensagem)
    texto = re.sub(r'\d{10,11}', '[TEL]', texto)

    # Remove horarios exatos (podem ter pequenas variacoes)
    texto = re.sub(r'\d{1,2}:\d{2}', '[HORA]', texto)

    return texto.strip()


def calcular_content_hash(texto: str) -> str:
    """Calcula hash MD5 do texto normalizado."""
    texto_norm = normalizar_texto_para_hash(texto)
    return hashlib.md5(texto_norm.encode()).hexdigest()


async def verificar_duplicata_redis(
    content_hash: str,
    grupo_jid: str
) -> Optional[UUID]:
    """
    Verifica duplicata no Redis (cache rapido).

    Returns:
        UUID da mensagem original se duplicata, None se nova
    """
    chave = f"{DEDUP_CACHE_PREFIX}{content_hash}"

    try:
        cached = await cache_get(chave)
        if cached:
            logger.debug(f"Duplicata encontrada no Redis: {content_hash[:8]}")
            return UUID(cached)
    except Exception as e:
        logger.warning(f"Erro ao verificar Redis: {e}")

    return None


async def verificar_duplicata_banco(
    content_hash: str,
    excluir_id: Optional[UUID] = None
) -> Optional[UUID]:
    """
    Verifica duplicata no banco (fallback).

    Returns:
        UUID da mensagem original se duplicata, None se nova
    """
    limite_tempo = datetime.now(UTC) - timedelta(hours=DEDUP_TTL_HORAS)

    query = supabase.table("pipeline_vagas") \
        .select("id") \
        .eq("content_hash", content_hash) \
        .eq("is_duplicate", False) \
        .gte("created_at", limite_tempo.isoformat())

    if excluir_id:
        query = query.neq("id", str(excluir_id))

    result = query.limit(1).execute()

    if result.data:
        return UUID(result.data[0]["id"])

    return None


async def registrar_no_cache(content_hash: str, mensagem_id: UUID) -> None:
    """Registra hash no Redis para consultas futuras."""
    chave = f"{DEDUP_CACHE_PREFIX}{content_hash}"

    try:
        await cache_set(
            chave,
            str(mensagem_id),
            ttl=DEDUP_TTL_HORAS * 3600
        )
    except Exception as e:
        logger.warning(f"Erro ao registrar no Redis: {e}")


async def processar_dedup_precoce(
    texto: str,
    grupo_jid: str,
    trace_id: UUID
) -> Tuple[bool, Optional[UUID], str]:
    """
    Processa dedup precoce (estagio 1).

    Returns:
        (is_duplicate, original_id, content_hash)
    """
    content_hash = calcular_content_hash(texto)

    # 1. Verifica Redis (rapido, <1ms)
    original_id = await verificar_duplicata_redis(content_hash, grupo_jid)

    if original_id:
        logger.info(
            f"[{trace_id}] Duplicata detectada (Redis)",
            extra={
                "trace_id": str(trace_id),
                "content_hash": content_hash[:8],
                "original_id": str(original_id)
            }
        )
        return True, original_id, content_hash

    # 2. Verifica banco (fallback, ~10ms)
    original_id = await verificar_duplicata_banco(content_hash)

    if original_id:
        # Atualiza Redis para proxima vez
        await registrar_no_cache(content_hash, original_id)

        logger.info(
            f"[{trace_id}] Duplicata detectada (banco)",
            extra={
                "trace_id": str(trace_id),
                "content_hash": content_hash[:8],
                "original_id": str(original_id)
            }
        )
        return True, original_id, content_hash

    # 3. Mensagem nova
    return False, None, content_hash
```

### Criterios de Aceite

- [ ] Dedup funciona antes de qualquer chamada LLM
- [ ] Cache Redis com TTL de 24h
- [ ] Fallback para banco de dados
- [ ] Logs estruturados com trace_id
- [ ] Metricas de duplicatas por grupo/dia

---

## Story 3: Prompt LLM Unificado

**Prioridade:** P0
**Estimativa:** 3 pontos

### Objetivo

Um unico prompt que classifica E extrai dados simultaneamente. Economia de 50% em chamadas LLM.

### Prompt Unificado

```python
# app/services/grupos_v3/prompts.py

PROMPT_LLM_UNIFICADO = """
Voce e um assistente especializado em analisar mensagens de grupos WhatsApp de staffing medico.

TAREFA: Analise a mensagem e:
1. Determine se e uma OFERTA de plantao/vaga medica
2. Se for oferta, extraia TODOS os dados estruturados

---

CONSIDERA OFERTA DE PLANTAO:
- Anuncio de vaga/plantao disponivel
- Lista de escalas disponiveis
- Cobertura urgente sendo oferecida
- Hospital/clinica buscando medico para data especifica
- Mensagens com hospital + data + valor/especialidade

NAO CONSIDERA OFERTA:
- Perguntas sobre vagas ("alguem tem vaga?")
- Cumprimentos e conversas sociais
- Medicos se oferecendo para trabalhar ("estou disponivel")
- Discussoes sobre valores de mercado
- Regras do grupo
- Confirmacoes de plantao ja aceito

---

CONTEXTO:
- Data de hoje: {data_hoje}
- Data de amanha: {data_amanha}
- Grupo: {nome_grupo}
- Regiao do grupo: {regiao}
- Quem enviou: {sender}

---

MENSAGEM:
{texto}

---

RESPONDA APENAS COM JSON VALIDO:

Se NAO for oferta:
{{
  "is_oferta": false,
  "confidence": 0.95,
  "reason": "cumprimento/pergunta/medico oferecendo/etc"
}}

Se FOR oferta, extraia TUDO que conseguir:
{{
  "is_oferta": true,
  "confidence": 0.92,
  "vagas": [
    {{
      "hospital": {{
        "nome": "Hospital Sao Luiz ABC",
        "endereco": "Rua Exemplo, 123",
        "cidade": "Santo Andre",
        "confidence": 0.95
      }},
      "especialidade": {{
        "nome": "Clinica Medica",
        "abreviacao": "CM",
        "confidence": 0.90
      }},
      "data": {{
        "data": "2026-02-05",
        "dia_semana": "quarta",
        "confidence": 1.0
      }},
      "horario": {{
        "periodo": "noturno",
        "hora_inicio": "19:00",
        "hora_fim": "07:00",
        "confidence": 0.95
      }},
      "valor": {{
        "tipo": "fixo",
        "valor": 1800,
        "valor_minimo": null,
        "valor_maximo": null,
        "confidence": 0.90
      }},
      "contato": {{
        "nome": "Ana",
        "whatsapp": "11999998888",
        "confidence": 0.85
      }},
      "setor": "Pronto atendimento",
      "tipo_vaga": "Cobertura",
      "forma_pagamento": "PJ",
      "observacoes": "Necessario RQE"
    }}
  ]
}}

REGRAS DE EXTRACAO:

1. PERIODOS:
   - "manha" = 07:00-13:00
   - "tarde" = 13:00-19:00
   - "noite/noturno" = 19:00-07:00
   - "diurno/SD" = 07:00-19:00
   - "cinderela" = 19:00-01:00

2. VALORES:
   - Se diz "R$ 1.800" ou similar: tipo="fixo", valor=1800
   - Se diz "a combinar", "negociavel": tipo="a_combinar"
   - Se NAO menciona valor: tipo="a_combinar"
   - Se diz "entre X e Y": tipo="faixa", valor_minimo=X, valor_maximo=Y

3. ESPECIALIDADES COMUNS:
   - CM = Clinica Medica
   - GO = Ginecologia e Obstetricia
   - PED = Pediatria
   - CARDIO = Cardiologia
   - ORTO = Ortopedia
   - NEURO = Neurologia
   - UTI = Intensivista

4. MULTIPLAS VAGAS:
   - Uma mensagem pode ter varias vagas
   - Retorne TODAS no array "vagas"

5. DATAS:
   - "hoje" = {data_hoje}
   - "amanha" = {data_amanha}
   - Segunda/Terca/etc = calcule a data correta

6. CAMPOS NULL:
   - Se nao conseguir extrair, use null
   - Apenas hospital E especialidade sao obrigatorios
"""


def formatar_prompt_unificado(
    texto: str,
    nome_grupo: str = "",
    regiao: str = "",
    sender: str = "",
    data_hoje: str = "",
    data_amanha: str = ""
) -> str:
    """Formata o prompt com os dados da mensagem."""
    from datetime import date, timedelta

    hoje = date.today()
    amanha = hoje + timedelta(days=1)

    return PROMPT_LLM_UNIFICADO.format(
        texto=texto,
        nome_grupo=nome_grupo or "Desconhecido",
        regiao=regiao or "Nao informada",
        sender=sender or "Desconhecido",
        data_hoje=data_hoje or hoje.isoformat(),
        data_amanha=data_amanha or amanha.isoformat()
    )
```

### Cliente LLM Unificado

```python
# app/services/grupos_v3/llm_unificado.py

import json
import time
from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.services.grupos_v3.prompts import formatar_prompt_unificado

logger = get_logger(__name__)


@dataclass
class VagaExtraida:
    """Vaga extraida pelo LLM."""
    hospital_nome: Optional[str] = None
    hospital_endereco: Optional[str] = None
    hospital_cidade: Optional[str] = None
    hospital_confidence: float = 0.0

    especialidade_nome: Optional[str] = None
    especialidade_abrev: Optional[str] = None
    especialidade_confidence: float = 0.0

    data_plantao: Optional[str] = None
    dia_semana: Optional[str] = None

    periodo: Optional[str] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None

    valor_tipo: str = "a_combinar"
    valor: Optional[int] = None
    valor_minimo: Optional[int] = None
    valor_maximo: Optional[int] = None

    contato_nome: Optional[str] = None
    contato_whatsapp: Optional[str] = None

    setor: Optional[str] = None
    tipo_vaga: Optional[str] = None
    forma_pagamento: Optional[str] = None
    observacoes: Optional[str] = None


@dataclass
class ResultadoLLMUnificado:
    """Resultado do processamento LLM unificado."""
    is_oferta: bool
    confidence: float
    reason: Optional[str] = None
    vagas: List[VagaExtraida] = None
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    model: str = "claude-3-haiku-20240307"
    erro: Optional[str] = None

    def __post_init__(self):
        if self.vagas is None:
            self.vagas = []


def _parsear_resposta_llm(texto: str) -> dict:
    """Parseia JSON da resposta LLM."""
    texto = texto.strip()

    # Tenta extrair JSON
    if texto.startswith("{"):
        return json.loads(texto)

    # Busca JSON no meio do texto
    import re
    match = re.search(r'\{[\s\S]*\}', texto)
    if match:
        return json.loads(match.group())

    raise json.JSONDecodeError("JSON nao encontrado", texto, 0)


def _converter_vaga(dados: dict) -> VagaExtraida:
    """Converte dict para VagaExtraida."""
    hospital = dados.get("hospital", {})
    especialidade = dados.get("especialidade", {})
    data_info = dados.get("data", {})
    horario = dados.get("horario", {})
    valor_info = dados.get("valor", {})
    contato = dados.get("contato", {})

    return VagaExtraida(
        hospital_nome=hospital.get("nome"),
        hospital_endereco=hospital.get("endereco"),
        hospital_cidade=hospital.get("cidade"),
        hospital_confidence=hospital.get("confidence", 0.0),

        especialidade_nome=especialidade.get("nome"),
        especialidade_abrev=especialidade.get("abreviacao"),
        especialidade_confidence=especialidade.get("confidence", 0.0),

        data_plantao=data_info.get("data"),
        dia_semana=data_info.get("dia_semana"),

        periodo=horario.get("periodo"),
        hora_inicio=horario.get("hora_inicio"),
        hora_fim=horario.get("hora_fim"),

        valor_tipo=valor_info.get("tipo", "a_combinar"),
        valor=valor_info.get("valor"),
        valor_minimo=valor_info.get("valor_minimo"),
        valor_maximo=valor_info.get("valor_maximo"),

        contato_nome=contato.get("nome"),
        contato_whatsapp=contato.get("whatsapp"),

        setor=dados.get("setor"),
        tipo_vaga=dados.get("tipo_vaga"),
        forma_pagamento=dados.get("forma_pagamento"),
        observacoes=dados.get("observacoes")
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
async def _chamar_llm(
    prompt: str,
    model: str = "claude-3-haiku-20240307"
) -> tuple:
    """Chama LLM com retry."""
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = await client.messages.create(
        model=model,
        max_tokens=1500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )

    resposta_texto = response.content[0].text.strip()
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens

    return resposta_texto, tokens_in, tokens_out


async def processar_llm_unificado(
    texto: str,
    trace_id: UUID,
    nome_grupo: str = "",
    regiao: str = "",
    sender: str = "",
    model: str = "claude-3-haiku-20240307"
) -> ResultadoLLMUnificado:
    """
    Processa mensagem com LLM unificado (classifica + extrai).

    Args:
        texto: Texto da mensagem
        trace_id: ID de rastreamento
        nome_grupo: Nome do grupo
        regiao: Regiao do grupo
        sender: Nome de quem enviou
        model: Modelo LLM a usar

    Returns:
        ResultadoLLMUnificado com classificacao e dados extraidos
    """
    inicio = time.time()

    prompt = formatar_prompt_unificado(
        texto=texto,
        nome_grupo=nome_grupo,
        regiao=regiao,
        sender=sender
    )

    try:
        resposta_texto, tokens_in, tokens_out = await _chamar_llm(prompt, model)
        latency_ms = int((time.time() - inicio) * 1000)

        dados = _parsear_resposta_llm(resposta_texto)

        resultado = ResultadoLLMUnificado(
            is_oferta=dados.get("is_oferta", False),
            confidence=dados.get("confidence", 0.0),
            reason=dados.get("reason"),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            model=model
        )

        if resultado.is_oferta and "vagas" in dados:
            resultado.vagas = [
                _converter_vaga(v) for v in dados["vagas"]
            ]

        logger.info(
            f"[{trace_id}] LLM processado",
            extra={
                "trace_id": str(trace_id),
                "is_oferta": resultado.is_oferta,
                "confidence": resultado.confidence,
                "vagas_count": len(resultado.vagas),
                "tokens_total": tokens_in + tokens_out,
                "latency_ms": latency_ms
            }
        )

        return resultado

    except json.JSONDecodeError as e:
        logger.warning(f"[{trace_id}] Erro parse JSON: {e}")
        return ResultadoLLMUnificado(
            is_oferta=False,
            confidence=0.0,
            erro=f"parse_error: {str(e)}",
            latency_ms=int((time.time() - inicio) * 1000),
            model=model
        )
    except anthropic.APIError as e:
        logger.error(f"[{trace_id}] Erro API: {e}")
        return ResultadoLLMUnificado(
            is_oferta=False,
            confidence=0.0,
            erro=f"api_error: {str(e)}",
            latency_ms=int((time.time() - inicio) * 1000),
            model=model
        )
    except Exception as e:
        logger.exception(f"[{trace_id}] Erro inesperado: {e}")
        return ResultadoLLMUnificado(
            is_oferta=False,
            confidence=0.0,
            erro=f"unexpected_error: {str(e)}",
            latency_ms=int((time.time() - inicio) * 1000),
            model=model
        )
```

### Criterios de Aceite

- [ ] Prompt extrai todos os campos necessarios em uma chamada
- [ ] Suporte a multiplas vagas por mensagem
- [ ] Tratamento de erro robusto
- [ ] Metricas de tokens e latencia
- [ ] Testes com 50+ mensagens reais

---

## Story 4: Orquestrador Principal

**Prioridade:** P0
**Estimativa:** 5 pontos

### Objetivo

Orquestrador que executa os 4 estagios em sequencia com observabilidade completa.

### Implementacao

```python
# app/services/grupos_v3/pipeline.py

import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional, List
from uuid import UUID, uuid4

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos_v3.dedup_precoce import (
    processar_dedup_precoce,
    registrar_no_cache
)
from app.services.grupos_v3.heuristica import calcular_score_heuristica
from app.services.grupos_v3.llm_unificado import processar_llm_unificado
from app.services.grupos_v3.normalizador import normalizar_entidades

logger = get_logger(__name__)


# Thresholds
THRESHOLD_HEURISTICA = 0.3  # Mais baixo que v2 (0.5) pois LLM faz segunda triagem
THRESHOLD_LLM_CONFIDENCE = 0.7


@dataclass
class PipelineContext:
    """Contexto do pipeline para uma mensagem."""
    trace_id: UUID = field(default_factory=uuid4)
    inicio: float = field(default_factory=time.time)

    # Dados de entrada
    mensagem_raw: str = ""
    grupo_jid: str = ""
    grupo_nome: str = ""
    sender_jid: str = ""
    sender_nome: str = ""
    mensagem_timestamp: Optional[datetime] = None

    # Estagio 1: Dedup
    content_hash: str = ""
    is_duplicate: bool = False
    duplicate_of: Optional[UUID] = None

    # Estagio 2: Heuristica
    heuristica_score: float = 0.0
    heuristica_keywords: List[str] = field(default_factory=list)
    heuristica_passed: bool = False

    # Estagio 3: LLM
    llm_is_oferta: bool = False
    llm_confidence: float = 0.0
    llm_tokens_in: int = 0
    llm_tokens_out: int = 0
    llm_latency_ms: int = 0
    llm_model: str = ""
    vagas_extraidas: list = field(default_factory=list)

    # Estagio 4: Normalizacao
    hospital_id: Optional[UUID] = None
    especialidade_id: Optional[UUID] = None
    normalizacao_status: str = ""
    normalizacao_erros: list = field(default_factory=list)

    # Status final
    status: str = "pending"
    status_reason: str = ""
    processing_time_ms: int = 0

    def tempo_decorrido_ms(self) -> int:
        return int((time.time() - self.inicio) * 1000)


@dataclass
class PipelineResult:
    """Resultado do pipeline."""
    success: bool
    trace_id: UUID
    status: str
    vagas_criadas: List[UUID] = field(default_factory=list)
    processing_time_ms: int = 0
    error: Optional[str] = None


class PipelineV3:
    """
    Pipeline v3 de processamento de mensagens de grupos.

    Estagios:
    1. Ingestao + Dedup Precoce
    2. Heuristica (filtro rapido)
    3. LLM Unificado (classifica + extrai)
    4. Persistencia + Normalizacao
    """

    async def processar(
        self,
        mensagem: str,
        grupo_jid: str,
        grupo_nome: str = "",
        sender_jid: str = "",
        sender_nome: str = "",
        mensagem_timestamp: Optional[datetime] = None
    ) -> PipelineResult:
        """
        Processa uma mensagem pelo pipeline completo.

        Args:
            mensagem: Texto da mensagem
            grupo_jid: JID do grupo WhatsApp
            grupo_nome: Nome do grupo
            sender_jid: JID de quem enviou
            sender_nome: Nome de quem enviou
            mensagem_timestamp: Timestamp da mensagem

        Returns:
            PipelineResult com status e vagas criadas
        """
        ctx = PipelineContext(
            mensagem_raw=mensagem,
            grupo_jid=grupo_jid,
            grupo_nome=grupo_nome,
            sender_jid=sender_jid,
            sender_nome=sender_nome,
            mensagem_timestamp=mensagem_timestamp or datetime.now(UTC)
        )

        logger.info(
            f"[{ctx.trace_id}] Pipeline iniciado",
            extra={
                "trace_id": str(ctx.trace_id),
                "grupo_jid": grupo_jid,
                "mensagem_len": len(mensagem)
            }
        )

        try:
            # ESTAGIO 1: Dedup Precoce
            await self._estagio_dedup(ctx)
            if ctx.is_duplicate:
                return await self._finalizar(ctx)

            # ESTAGIO 2: Heuristica
            await self._estagio_heuristica(ctx)
            if not ctx.heuristica_passed:
                return await self._finalizar(ctx)

            # ESTAGIO 3: LLM Unificado
            await self._estagio_llm(ctx)
            if not ctx.llm_is_oferta:
                return await self._finalizar(ctx)

            # ESTAGIO 4: Persistencia + Normalizacao
            vagas_ids = await self._estagio_persistencia(ctx)

            ctx.status = "ready"
            ctx.status_reason = f"{len(vagas_ids)} vagas extraidas"

            return await self._finalizar(ctx, vagas_ids)

        except Exception as e:
            logger.exception(f"[{ctx.trace_id}] Erro no pipeline: {e}")
            ctx.status = "error"
            ctx.status_reason = str(e)
            return await self._finalizar(ctx, error=str(e))

    async def _estagio_dedup(self, ctx: PipelineContext) -> None:
        """Estagio 1: Dedup Precoce."""
        is_dup, original_id, content_hash = await processar_dedup_precoce(
            texto=ctx.mensagem_raw,
            grupo_jid=ctx.grupo_jid,
            trace_id=ctx.trace_id
        )

        ctx.content_hash = content_hash
        ctx.is_duplicate = is_dup
        ctx.duplicate_of = original_id

        if is_dup:
            ctx.status = "duplicate"
            ctx.status_reason = f"Duplicata de {original_id}"

    async def _estagio_heuristica(self, ctx: PipelineContext) -> None:
        """Estagio 2: Heuristica."""
        resultado = calcular_score_heuristica(ctx.mensagem_raw)

        ctx.heuristica_score = resultado.score
        ctx.heuristica_keywords = resultado.keywords_encontradas
        ctx.heuristica_passed = resultado.score >= THRESHOLD_HEURISTICA

        if not ctx.heuristica_passed:
            ctx.status = "filtered"
            ctx.status_reason = f"Score {resultado.score:.2f} < {THRESHOLD_HEURISTICA}"

        logger.debug(
            f"[{ctx.trace_id}] Heuristica: {resultado.score:.2f}",
            extra={
                "trace_id": str(ctx.trace_id),
                "score": resultado.score,
                "keywords": resultado.keywords_encontradas,
                "passed": ctx.heuristica_passed
            }
        )

    async def _estagio_llm(self, ctx: PipelineContext) -> None:
        """Estagio 3: LLM Unificado."""
        resultado = await processar_llm_unificado(
            texto=ctx.mensagem_raw,
            trace_id=ctx.trace_id,
            nome_grupo=ctx.grupo_nome,
            regiao="",  # TODO: extrair do grupo
            sender=ctx.sender_nome
        )

        ctx.llm_is_oferta = resultado.is_oferta
        ctx.llm_confidence = resultado.confidence
        ctx.llm_tokens_in = resultado.tokens_in
        ctx.llm_tokens_out = resultado.tokens_out
        ctx.llm_latency_ms = resultado.latency_ms
        ctx.llm_model = resultado.model
        ctx.vagas_extraidas = resultado.vagas

        if not resultado.is_oferta:
            ctx.status = "not_offer"
            ctx.status_reason = resultado.reason or "LLM classificou como nao oferta"
        elif resultado.erro:
            ctx.status = "extraction_failed"
            ctx.status_reason = resultado.erro
        elif not resultado.vagas:
            ctx.status = "extraction_failed"
            ctx.status_reason = "Nenhuma vaga extraida"

    async def _estagio_persistencia(self, ctx: PipelineContext) -> List[UUID]:
        """Estagio 4: Persistencia + Normalizacao."""
        vagas_ids = []

        for vaga in ctx.vagas_extraidas:
            # Normaliza entidades
            hospital_id, especialidade_id, erros = await normalizar_entidades(
                hospital_nome=vaga.hospital_nome,
                especialidade_nome=vaga.especialidade_nome
            )

            # Prepara dados para persistencia
            dados = {
                "trace_id": str(ctx.trace_id),
                "grupo_jid": ctx.grupo_jid,
                "grupo_nome": ctx.grupo_nome,
                "sender_jid": ctx.sender_jid,
                "sender_nome": ctx.sender_nome,
                "mensagem_raw": ctx.mensagem_raw,
                "mensagem_timestamp": ctx.mensagem_timestamp.isoformat(),

                "content_hash": ctx.content_hash,
                "is_duplicate": ctx.is_duplicate,

                "heuristica_score": ctx.heuristica_score,
                "heuristica_keywords": ctx.heuristica_keywords,
                "heuristica_passed": ctx.heuristica_passed,

                "llm_is_oferta": ctx.llm_is_oferta,
                "llm_confidence": ctx.llm_confidence,
                "llm_model": ctx.llm_model,
                "llm_tokens_in": ctx.llm_tokens_in,
                "llm_tokens_out": ctx.llm_tokens_out,
                "llm_latency_ms": ctx.llm_latency_ms,

                "hospital_raw": vaga.hospital_nome,
                "hospital_id": str(hospital_id) if hospital_id else None,
                "hospital_confianca": vaga.hospital_confidence,

                "especialidade_raw": vaga.especialidade_nome,
                "especialidade_id": str(especialidade_id) if especialidade_id else None,
                "especialidade_confianca": vaga.especialidade_confidence,

                "data_plantao": vaga.data_plantao,
                "dia_semana": vaga.dia_semana,
                "periodo": vaga.periodo,
                "hora_inicio": vaga.hora_inicio,
                "hora_fim": vaga.hora_fim,

                "valor": vaga.valor,
                "valor_tipo": vaga.valor_tipo,
                "valor_minimo": vaga.valor_minimo,
                "valor_maximo": vaga.valor_maximo,

                "contato_nome": vaga.contato_nome,
                "contato_whatsapp": vaga.contato_whatsapp,

                "normalizacao_status": "ok" if not erros else "partial",
                "normalizacao_erros": erros,

                "status": "ready" if hospital_id and especialidade_id else "validation_failed",
                "status_reason": "; ".join(erros) if erros else None,
                "processing_time_ms": ctx.tempo_decorrido_ms()
            }

            result = supabase.table("pipeline_vagas").insert(dados).execute()
            vaga_id = UUID(result.data[0]["id"])
            vagas_ids.append(vaga_id)

            # Registra no cache para dedup futuro
            await registrar_no_cache(ctx.content_hash, vaga_id)

        return vagas_ids

    async def _finalizar(
        self,
        ctx: PipelineContext,
        vagas_ids: List[UUID] = None,
        error: str = None
    ) -> PipelineResult:
        """Finaliza pipeline e retorna resultado."""
        ctx.processing_time_ms = ctx.tempo_decorrido_ms()

        logger.info(
            f"[{ctx.trace_id}] Pipeline finalizado",
            extra={
                "trace_id": str(ctx.trace_id),
                "status": ctx.status,
                "processing_time_ms": ctx.processing_time_ms,
                "vagas_count": len(vagas_ids) if vagas_ids else 0
            }
        )

        return PipelineResult(
            success=ctx.status in ("ready", "duplicate", "filtered", "not_offer"),
            trace_id=ctx.trace_id,
            status=ctx.status,
            vagas_criadas=vagas_ids or [],
            processing_time_ms=ctx.processing_time_ms,
            error=error
        )


# Instancia global
pipeline_v3 = PipelineV3()
```

### Criterios de Aceite

- [ ] 4 estagios executando em sequencia
- [ ] trace_id em todos os logs
- [ ] Metricas por estagio
- [ ] Fallback gracioso em caso de erro
- [ ] Testes de integracao com todos os estagios

---

## Story 5: Observabilidade e Metricas

**Prioridade:** P1
**Estimativa:** 3 pontos

### Objetivo

Observabilidade completa com logs estruturados, metricas Prometheus-ready, e dashboards.

### Metricas a Coletar

```python
# app/services/grupos_v3/metricas.py

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID

from app.services.supabase import supabase


@dataclass
class MetricasPipeline:
    """Metricas do pipeline."""
    # Contadores
    total_mensagens: int = 0
    total_duplicatas: int = 0
    total_filtradas: int = 0
    total_nao_ofertas: int = 0
    total_prontas: int = 0
    total_erros: int = 0

    # Tempos
    tempo_medio_ms: float = 0.0
    tempo_p50_ms: float = 0.0
    tempo_p95_ms: float = 0.0
    tempo_p99_ms: float = 0.0

    # LLM
    tokens_total: int = 0
    llm_latency_avg_ms: float = 0.0

    # Economia
    duplicatas_evitadas_custo: float = 0.0  # $ economizado

    # Por grupo
    top_grupos: list = None


async def calcular_metricas_periodo(
    inicio: datetime,
    fim: Optional[datetime] = None
) -> MetricasPipeline:
    """Calcula metricas para um periodo."""
    fim = fim or datetime.now(UTC)

    # Query agregada
    result = supabase.rpc(
        "calcular_metricas_pipeline_v3",
        {"p_inicio": inicio.isoformat(), "p_fim": fim.isoformat()}
    ).execute()

    if not result.data:
        return MetricasPipeline()

    dados = result.data[0]

    return MetricasPipeline(
        total_mensagens=dados.get("total_mensagens", 0),
        total_duplicatas=dados.get("total_duplicatas", 0),
        total_filtradas=dados.get("total_filtradas", 0),
        total_nao_ofertas=dados.get("total_nao_ofertas", 0),
        total_prontas=dados.get("total_prontas", 0),
        total_erros=dados.get("total_erros", 0),
        tempo_medio_ms=dados.get("tempo_medio_ms", 0.0),
        tempo_p50_ms=dados.get("tempo_p50_ms", 0.0),
        tempo_p95_ms=dados.get("tempo_p95_ms", 0.0),
        tempo_p99_ms=dados.get("tempo_p99_ms", 0.0),
        tokens_total=dados.get("tokens_total", 0),
        llm_latency_avg_ms=dados.get("llm_latency_avg_ms", 0.0),
        duplicatas_evitadas_custo=dados.get("total_duplicatas", 0) * 0.001  # ~$0.001/chamada
    )


# Stored procedure para metricas
STORED_PROC_METRICAS = """
CREATE OR REPLACE FUNCTION calcular_metricas_pipeline_v3(
    p_inicio TIMESTAMPTZ,
    p_fim TIMESTAMPTZ
) RETURNS TABLE (
    total_mensagens BIGINT,
    total_duplicatas BIGINT,
    total_filtradas BIGINT,
    total_nao_ofertas BIGINT,
    total_prontas BIGINT,
    total_erros BIGINT,
    tempo_medio_ms NUMERIC,
    tempo_p50_ms NUMERIC,
    tempo_p95_ms NUMERIC,
    tempo_p99_ms NUMERIC,
    tokens_total BIGINT,
    llm_latency_avg_ms NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_mensagens,
        COUNT(*) FILTER (WHERE status = 'duplicate')::BIGINT as total_duplicatas,
        COUNT(*) FILTER (WHERE status = 'filtered')::BIGINT as total_filtradas,
        COUNT(*) FILTER (WHERE status = 'not_offer')::BIGINT as total_nao_ofertas,
        COUNT(*) FILTER (WHERE status = 'ready')::BIGINT as total_prontas,
        COUNT(*) FILTER (WHERE status = 'error')::BIGINT as total_erros,
        AVG(processing_time_ms)::NUMERIC as tempo_medio_ms,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY processing_time_ms)::NUMERIC as tempo_p50_ms,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms)::NUMERIC as tempo_p95_ms,
        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY processing_time_ms)::NUMERIC as tempo_p99_ms,
        SUM(COALESCE(llm_tokens_in, 0) + COALESCE(llm_tokens_out, 0))::BIGINT as tokens_total,
        AVG(llm_latency_ms)::NUMERIC as llm_latency_avg_ms
    FROM pipeline_vagas
    WHERE created_at BETWEEN p_inicio AND p_fim;
END;
$$ LANGUAGE plpgsql;
"""
```

### Logs Estruturados

```python
# app/services/grupos_v3/logging.py

import json
import structlog
from typing import Any, Dict


def configurar_logging_estruturado():
    """Configura logging estruturado para o pipeline."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# Exemplo de uso:
# logger.info(
#     "Pipeline processado",
#     trace_id=str(trace_id),
#     status="ready",
#     processing_time_ms=150,
#     vagas_count=2
# )
#
# Output JSON:
# {
#     "timestamp": "2026-02-02T12:00:00Z",
#     "level": "info",
#     "event": "Pipeline processado",
#     "trace_id": "abc-123",
#     "status": "ready",
#     "processing_time_ms": 150,
#     "vagas_count": 2
# }
```

### Criterios de Aceite

- [ ] Metricas por estagio (contadores + histogramas)
- [ ] Logs estruturados em JSON
- [ ] Stored procedure para agregacoes
- [ ] Endpoint /metrics para Prometheus
- [ ] Dashboard no Grafana com metricas principais

---

## Story 6: Plano de Migracao v2 para v3

**Prioridade:** P1
**Estimativa:** 3 pontos

### Objetivo

Migrar gradualmente do pipeline v2 para v3 sem downtime.

### Estrategia: Feature Flag + Dual Write

```python
# app/services/grupos_v3/migracao.py

import os
from datetime import datetime
from uuid import UUID

from app.core.logging import get_logger
from app.services.grupos_v3.pipeline import pipeline_v3
from app.services.grupos.pipeline_worker import PipelineGrupos  # v2

logger = get_logger(__name__)


# Feature flags
PIPELINE_V3_ENABLED = os.getenv("PIPELINE_V3_ENABLED", "false").lower() == "true"
PIPELINE_V3_PERCENTAGE = int(os.getenv("PIPELINE_V3_PERCENTAGE", "0"))  # 0-100
PIPELINE_DUAL_WRITE = os.getenv("PIPELINE_DUAL_WRITE", "false").lower() == "true"


def should_use_v3(grupo_jid: str) -> bool:
    """Determina se deve usar pipeline v3 para este grupo."""
    if not PIPELINE_V3_ENABLED:
        return False

    if PIPELINE_V3_PERCENTAGE >= 100:
        return True

    if PIPELINE_V3_PERCENTAGE <= 0:
        return False

    # Hash consistente para rollout gradual
    import hashlib
    hash_value = int(hashlib.md5(grupo_jid.encode()).hexdigest()[:8], 16)
    return (hash_value % 100) < PIPELINE_V3_PERCENTAGE


async def processar_mensagem_hibrido(
    mensagem: str,
    grupo_jid: str,
    grupo_nome: str = "",
    sender_jid: str = "",
    sender_nome: str = "",
    mensagem_timestamp: datetime = None
) -> dict:
    """
    Processa mensagem usando v2 ou v3 baseado em feature flags.

    Suporta:
    - Rollout gradual por porcentagem
    - Dual write para comparacao
    """
    use_v3 = should_use_v3(grupo_jid)

    if use_v3:
        # Usa pipeline v3
        resultado = await pipeline_v3.processar(
            mensagem=mensagem,
            grupo_jid=grupo_jid,
            grupo_nome=grupo_nome,
            sender_jid=sender_jid,
            sender_nome=sender_nome,
            mensagem_timestamp=mensagem_timestamp
        )

        logger.info(
            f"[v3] Processado: {resultado.status}",
            extra={"pipeline_version": "v3", "trace_id": str(resultado.trace_id)}
        )

        return {
            "version": "v3",
            "success": resultado.success,
            "status": resultado.status,
            "vagas_count": len(resultado.vagas_criadas)
        }

    else:
        # Usa pipeline v2 (existente)
        pipeline_v2 = PipelineGrupos()

        # ... codigo existente do v2 ...

        return {
            "version": "v2",
            "success": True,
            "status": "processed"
        }


# Configuracao para rollout gradual:
#
# Fase 1 (Semana 1):
#   PIPELINE_V3_ENABLED=true
#   PIPELINE_V3_PERCENTAGE=5
#   PIPELINE_DUAL_WRITE=true
#
# Fase 2 (Semana 2):
#   PIPELINE_V3_PERCENTAGE=25
#
# Fase 3 (Semana 3):
#   PIPELINE_V3_PERCENTAGE=50
#
# Fase 4 (Semana 4):
#   PIPELINE_V3_PERCENTAGE=100
#   PIPELINE_DUAL_WRITE=false
#
# Fase 5 (Semana 5):
#   Remover codigo v2
```

### Criterios de Aceite

- [ ] Feature flag PIPELINE_V3_ENABLED funcionando
- [ ] Rollout gradual por porcentagem
- [ ] Hash consistente (mesmo grupo sempre usa mesma versao)
- [ ] Logs identificando versao usada
- [ ] Metricas separadas por versao para comparacao

---

## Story 7: Testes e Validacao

**Prioridade:** P1
**Estimativa:** 3 pontos

### Objetivo

Suite de testes completa para garantir qualidade do pipeline v3.

### Testes Unitarios

```python
# tests/grupos_v3/test_dedup_precoce.py

import pytest
from uuid import uuid4

from app.services.grupos_v3.dedup_precoce import (
    normalizar_texto_para_hash,
    calcular_content_hash,
    processar_dedup_precoce
)


class TestNormalizacaoTexto:
    def test_remove_espacos_extras(self):
        texto = "Hospital   ABC    plantao"
        assert "  " not in normalizar_texto_para_hash(texto)

    def test_remove_emojis(self):
        texto = "🏥 Hospital ABC 📅 28/12"
        normalizado = normalizar_texto_para_hash(texto)
        assert "🏥" not in normalizado
        assert "hospital abc" in normalizado

    def test_normaliza_telefones(self):
        texto = "Contato: 11999998888"
        normalizado = normalizar_texto_para_hash(texto)
        assert "[TEL]" in normalizado
        assert "11999998888" not in normalizado

    def test_normaliza_horarios(self):
        texto = "Plantao 19:00 as 07:00"
        normalizado = normalizar_texto_para_hash(texto)
        assert "[HORA]" in normalizado
        assert "19:00" not in normalizado


class TestContentHash:
    def test_hash_consistente(self):
        texto = "Hospital ABC plantao 28/12"
        hash1 = calcular_content_hash(texto)
        hash2 = calcular_content_hash(texto)
        assert hash1 == hash2

    def test_hash_diferente_para_textos_diferentes(self):
        hash1 = calcular_content_hash("Hospital ABC")
        hash2 = calcular_content_hash("Hospital XYZ")
        assert hash1 != hash2

    def test_hash_mesmo_para_variacoes_normalizadas(self):
        texto1 = "Hospital ABC plantao 11999998888"
        texto2 = "Hospital ABC plantao 11888887777"
        # Telefones sao normalizados, entao hash deve ser igual
        hash1 = calcular_content_hash(texto1)
        hash2 = calcular_content_hash(texto2)
        assert hash1 == hash2


class TestDedupPrecoce:
    @pytest.mark.asyncio
    async def test_nova_mensagem_nao_duplicata(self):
        is_dup, original, hash = await processar_dedup_precoce(
            texto="Mensagem unica " + str(uuid4()),
            grupo_jid="grupo@g.us",
            trace_id=uuid4()
        )
        assert is_dup is False
        assert original is None
        assert len(hash) == 32  # MD5
```

### Testes de Integracao

```python
# tests/grupos_v3/test_pipeline_integracao.py

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from app.services.grupos_v3.pipeline import PipelineV3


class TestPipelineIntegracao:
    @pytest.fixture
    def pipeline(self):
        return PipelineV3()

    @pytest.mark.asyncio
    async def test_mensagem_oferta_completa(self, pipeline):
        resultado = await pipeline.processar(
            mensagem="""
            🏥 Hospital São Luiz ABC
            📅 05/02 - Quarta
            ⏰ Noturno (19h às 7h)
            💰 R$ 1.800 PJ
            👨‍⚕️ Clínica Médica
            📞 11999998888
            """,
            grupo_jid="plantoes-abc@g.us",
            grupo_nome="Plantões ABC",
            sender_jid="admin@s.whatsapp.net",
            sender_nome="Admin"
        )

        assert resultado.success is True
        assert resultado.status == "ready"
        assert len(resultado.vagas_criadas) >= 1

    @pytest.mark.asyncio
    async def test_mensagem_cumprimento_descartada(self, pipeline):
        resultado = await pipeline.processar(
            mensagem="Bom dia pessoal!",
            grupo_jid="plantoes-abc@g.us"
        )

        assert resultado.success is True
        assert resultado.status in ("filtered", "not_offer")
        assert len(resultado.vagas_criadas) == 0

    @pytest.mark.asyncio
    async def test_duplicata_detectada(self, pipeline):
        texto = "Plantao Hospital ABC 28/12 noturno R$ 1800"

        # Primeira vez
        resultado1 = await pipeline.processar(
            mensagem=texto,
            grupo_jid="grupo1@g.us"
        )

        # Segunda vez (duplicata)
        resultado2 = await pipeline.processar(
            mensagem=texto,
            grupo_jid="grupo2@g.us"
        )

        assert resultado2.status == "duplicate"
```

### Criterios de Aceite

- [ ] Cobertura > 80% no codigo do pipeline v3
- [ ] Testes unitarios para cada estagio
- [ ] Testes de integracao end-to-end
- [ ] Testes de carga (100 mensagens/minuto)
- [ ] Testes de comparacao v2 vs v3

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Prompt LLM unificado menos preciso | Media | Alto | Testar com 500+ mensagens reais antes de rollout |
| Dedup precoce perde mensagens legitimas | Baixa | Alto | Ajustar normalizacao, monitorar taxa de dedup |
| Migracao quebra pipeline existente | Media | Critico | Feature flags, rollout gradual 5%→100% |
| Performance pior que v2 | Baixa | Medio | Benchmarks antes do rollout |
| Redis indisponivel | Baixa | Baixo | Fallback para banco, timeout curto |

---

## Cronograma Sugerido

| Semana | Story | Entregas |
|--------|-------|----------|
| 1 | S1: Modelo de Dados | Tabela + indices + views |
| 2 | S2: Dedup Precoce | Estagio 1 funcionando |
| 2 | S3: Prompt LLM | Prompt testado com mensagens reais |
| 3 | S4: Orquestrador | Pipeline completo end-to-end |
| 4 | S5: Observabilidade | Metricas + logs estruturados |
| 4 | S6: Migracao | Feature flags + rollout 5% |
| 5 | S7: Testes | Suite completa + benchmarks |
| 6-8 | Rollout | 5% → 25% → 50% → 100% |

---

## Metricas de Sucesso

| Metrica | v2 (Atual) | v3 (Meta) |
|---------|------------|-----------|
| Tempo medio/msg | 5-10s | < 2s |
| Custo LLM/msg | ~$0.003 | < $0.0015 |
| Taxa duplicatas detectadas | ~70% | > 95% |
| Taxa extracao especialidade | ~0% | > 90% |
| Cobertura de testes | ~40% | > 80% |
| Logs rastreaveismcl | 0% | 100% |

---

## Referencias

- Epic 1: Investigacao Profunda (`epic-01-investigacao.md`)
- Epic 2: Correcoes v2 (`epic-02-correcoes.md`)
- Pipeline v2: `app/services/grupos/extrator_v2/pipeline.py`
- Heuristica: `app/services/grupos/heuristica.py`
- Documentacao LLM: `docs/julia/prompts.md`
