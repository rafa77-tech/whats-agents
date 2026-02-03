# Epic 1: Investigacao Profunda do Pipeline de Grupos

**Status:** 🟢 Concluida
**Data:** 02/02/2026

---

## Objetivo

Mapear completamente o pipeline de extracao de vagas dos grupos WhatsApp, identificando:
- Fluxo atual de dados
- Pontos de falha
- Gaps entre especificacao e implementacao

---

## Descobertas

### 1. Fluxo de Chegada das Mensagens

```
Evolution API
    │
    └─→ POST /webhook/evolution
        │
        └─→ processar_mensagem_pipeline(data)
            │
            └─→ IngestaoGrupoProcessor (prioridade 5)
                │
                ├─ É grupo (@g.us)? SIM → Ingere e PARA
                │
                └─ É grupo? NAO → Continua pipeline Julia
```

**Arquivo:** `app/api/routes/webhook.py` (linhas 25-169)

### 2. Ingestao de Mensagens de Grupo

**Arquivo:** `app/services/grupos/ingestor.py` (linhas 327-407)

```python
async def ingerir_mensagem_grupo(mensagem, dados_raw):
    # 1. Cria/obtem grupo
    grupo = await obter_ou_criar_grupo(jid)

    # 2. Cria/obtem contato
    contato = await obter_ou_criar_contato(jid, nome)

    # 3. Salva mensagem
    mensagem_id = await salvar_mensagem_grupo(...)
    # STATUS: 'pendente'
    # passou_heuristica: NULL
    # eh_oferta: NULL

    # 4. Enfileira para processamento
    await enfileirar_mensagem(mensagem_id)
    # ESTAGIO: 'pendente'
```

**Problema:** Campos `passou_heuristica` e `eh_oferta` inicializados como NULL e nunca atualizados.

### 3. Estagios do Pipeline

**Arquivo:** `app/services/grupos/fila.py`

```python
class EstagioPipeline(str, Enum):
    PENDENTE = "pendente"
    HEURISTICA = "heuristica"
    CLASSIFICACAO = "classificacao"
    EXTRACAO = "extracao"
    NORMALIZACAO = "normalizacao"
    DEDUPLICACAO = "deduplicacao"
    IMPORTACAO = "importacao"
    FINALIZADO = "finalizado"
    DESCARTADO = "descartado"
    ERRO = "erro"
```

### 4. Heuristica (Filtro Rapido)

**Arquivo:** `app/services/grupos/heuristica.py`

**Keywords Positivas:**
- Plantao: `\bplant[aã]o\b`, `\bvaga\b`, `\bescala\b`, `\bcobertura\b`
- Financeiro: `\breais\b`, `\bvalor\b`, `\bpago\b`, `\bPJ\b`, `\bPF\b`
- Horarios: `\bnoturno\b`, `\bdiurno\b`, `\b12h\b`, `\b24h\b`
- Datas: `\bdia\s+\d{1,2}\b`, `\d{1,2}/\d{1,2}`, `\bamanh[aã]\b`
- Medico: `\bm[eé]dico\b`, `\bCRM\b`, `\bplantoni[sz]ta\b`
- Hospitais: `\bhospital\b`, `\bUPA\b`, `\bPS\b`, `\bclínica\b`
- Especialidades: `\bcardio\b`, `\bpediatria\b`, `\bgineco\b`, `\bUTI\b`

**Keywords Negativas:**
- Cumprimentos: `^bom\s*dia\b`, `^boa\s*(tarde|noite)\b`, `^ol[aá]\b`
- Agradecimentos: `\bobrigad[oa]\b`, `\bvaleu\b`, `\btmj\b`
- Confirmacoes: `^ok\b`, `^beleza\b`, `^blz\b`, `^show\b`

**Scoring:**
- Threshold padrao: 0.5
- Threshold alto (pula LLM): 0.75

### 5. Funcoes de Atualizacao (NAO UTILIZADAS)

**Arquivo:** `app/services/grupos/classificador.py`

```python
# Funcao existe mas NAO e chamada pelo pipeline atual!
async def atualizar_resultado_heuristica(mensagem_id, resultado):
    supabase.table("mensagens_grupo").update({
        "status": novo_status,
        "passou_heuristica": resultado.passou,  # ← DEVERIA PREENCHER AQUI
        "score_heuristica": resultado.score,
        "keywords_encontradas": resultado.keywords_encontradas,
    }).eq("id", str(mensagem_id)).execute()
```

```python
# Funcao existe mas NAO e chamada pelo pipeline atual!
async def atualizar_resultado_classificacao_llm(mensagem_id, resultado):
    supabase.table("mensagens_grupo").update({
        "status": novo_status,
        "eh_oferta": resultado.eh_oferta,  # ← DEVERIA PREENCHER AQUI
        "confianca_classificacao": resultado.confianca,
    }).eq("id", str(mensagem_id)).execute()
```

### 6. Pipeline Worker (Onde o Problema Ocorre)

**Arquivo:** `app/services/grupos/pipeline_worker.py`

```python
# Linha 64-129
async def processar_pendente(item):
    # Calcula score de heuristica
    resultado = await calcular_score_heuristica(texto)

    # Decide proxima acao baseado no score
    if resultado.score < 0.5:
        return ResultadoPipeline(acao="descartar")
    elif resultado.score >= 0.75:
        return ResultadoPipeline(acao="extrair")
    else:
        return ResultadoPipeline(acao="classificar")

    # ❌ NAO ATUALIZA mensagens_grupo.passou_heuristica!

# Linha 131-182
async def processar_classificacao(item):
    # Chama LLM
    resultado = await classificar_com_llm(texto)

    if resultado.eh_oferta and resultado.confianca >= threshold:
        return ResultadoPipeline(acao="extrair")
    else:
        return ResultadoPipeline(acao="descartar")

    # ❌ NAO ATUALIZA mensagens_grupo.eh_oferta!

# Linha 184-253
async def processar_extracao(item):
    # Extrai vagas
    vagas = await extrair_dados_mensagem(texto)

    # Cria registros em vagas_grupo
    for vaga in vagas:
        await inserir_vaga_grupo(vaga)

    return ResultadoPipeline(acao="normalizar", vagas_criadas=vaga_ids)

    # ✅ Cria vagas corretamente
    # ❌ Mas nao atualiza mensagem original
```

### 7. Worker de Grupos

**Arquivo:** `app/workers/grupos_worker.py` (linhas 69-153)

```python
async def processar_fila():
    while True:
        for estagio in [PENDENTE, CLASSIFICACAO, EXTRACAO, ...]:
            itens = await buscar_proximos(estagio, limite=50)

            for item in itens:
                resultado = await handler(item)
                proximo_estagio = mapear_acao_para_estagio(resultado.acao)

                if resultado.vagas_criadas:
                    # Cria itens para cada vaga
                    await criar_itens_para_vagas(...)
                    await atualizar_estagio(..., FINALIZADO)
                else:
                    await atualizar_estagio(..., proximo_estagio)
```

### 8. Sincronizacao de Status

**Arquivo:** `app/services/grupos/fila.py` (linhas 290-342)

```python
async def _sincronizar_status_mensagem(mensagem_id, estagio):
    mapeamento = {
        FINALIZADO: "processada",
        DESCARTADO: "descartada",
        EXTRACAO: "classificada",
        NORMALIZACAO: "extraida",
    }
    # ❌ NAO atualiza passou_heuristica ou eh_oferta!
```

---

## Diagrama do Fluxo Atual

```
WEBHOOK (Evolution)
    │
    └─→ IngestaoGrupoProcessor
        │
        ├─ Salva em mensagens_grupo
        │  (status=pendente, passou_heuristica=NULL, eh_oferta=NULL)
        │
        └─ Enfileira em fila_processamento_grupos
           (estagio=pendente)

        ↓↓↓ WORKER GRUPOS ↓↓↓

Estagio: PENDENTE
    └─ processar_pendente()
        ├─ Calcula score_heuristica ← CALCULA mas NAO salva
        ├─ Se score < 0.5 → DESCARTAR
        ├─ Se score >= 0.75 → EXTRAIR
        └─ Se 0.5 <= score < 0.75 → CLASSIFICAR

Estagio: CLASSIFICACAO
    └─ processar_classificacao()
        ├─ Chama LLM ← CLASSIFICA mas NAO salva eh_oferta
        └─ Decide EXTRAIR ou DESCARTAR

Estagio: EXTRACAO
    └─ processar_extracao()
        ├─ Extrai dados estruturados
        └─ INSERT vagas_grupo ← FUNCIONA

Estagio: NORMALIZACAO → DEDUPLICACAO → IMPORTACAO
    └─ Fluxo continua...
        └─ ❌ IMPORTACAO parece nao executar
```

---

## Gaps Identificados

| # | Gap | Impacto |
|---|-----|---------|
| 1 | `passou_heuristica` nunca e preenchido | Dashboard mostra 0 |
| 2 | `eh_oferta` nunca e preenchido | Dashboard mostra 0 |
| 3 | `score_heuristica` nao e salvo | Sem auditoria |
| 4 | `keywords_encontradas` nao e salvo | Sem debug |
| 5 | `confianca_classificacao` nao e salvo | Sem qualidade |
| 6 | Vagas nao chegam a IMPORTACAO | 0 importadas |
| 7 | Funcoes de atualizacao existem mas nao sao chamadas | Codigo morto |

---

## Evidencias no Banco

```sql
-- Todas as mensagens com campos NULL
SELECT passou_heuristica, eh_oferta, COUNT(*)
FROM mensagens_grupo
GROUP BY passou_heuristica, eh_oferta;

-- Resultado:
-- NULL, NULL: 22.514
-- NULL, true: 1
```

```sql
-- Vagas criadas sem classificacao
SELECT COUNT(*) FROM vagas_grupo
WHERE created_at >= NOW() - INTERVAL '24 hours';

-- Resultado: 3.467 vagas criadas
-- MAS as mensagens originais tem passou_heuristica = NULL
```

---

## Descoberta Adicional: Bug no Extrator v2 (CRITICO!)

### O Problema

O extrator v2 **nao extrai especialidades**, causando 100% de descarte das vagas.

**Arquivo:** `app/services/grupos/extrator_v2/pipeline.py`

**Evidencia:**
```python
# Linha 143-150: especialidades NAO sao passadas!
vagas = gerar_vagas(
    hospitais=hospitais,
    datas_periodos=datas_periodos,
    valores=valores,
    contato=contato,
    mensagem_id=mensagem_id,
    grupo_id=grupo_id,
    # especialidades=???  ← FALTANDO!
)
```

### Implementacao Incompleta

| Arquivo | Status |
|---------|--------|
| `types.py` | ✅ `EspecialidadeExtraida` definido |
| `parser_mensagem.py` | ✅ `secoes_especialidade` extraido |
| `extrator_especialidades.py` | ❌ NAO EXISTE |
| `pipeline.py` | ❌ Nao processa especialidades |
| `gerar_vagas()` | ⚠️ Aceita param mas recebe None |

### Resultado

```
Mensagem: "VAGA PARA MÉDICO - GINECOLOGIA E OBSTETRÍCIA"
Parser: secoes_especialidade = ["GINECOLOGIA E OBSTETRÍCIA"]
Extrator: NAO IMPLEMENTADO
Vaga: especialidade_raw = NULL
Validacao: DESCARTADA (especialidade_id ausente)
```

---

## Proximos Passos

### Prioridade 0 (URGENTE)
1. **S51.E2.0:** Criar `extrator_especialidades.py` ou extrair inline
2. **S51.E2.0:** Conectar ao pipeline.py
3. **S51.E2.0:** Testar com mensagens reais

### Prioridade 1
4. **S51.E2.1:** Corrigir chamadas para `atualizar_resultado_heuristica()`
5. **S51.E2.2:** Corrigir chamadas para `atualizar_resultado_classificacao_llm()`

### Prioridade 2
6. **S51.E3:** Adicionar logs estruturados
7. **S51.E3:** Criar metricas de observabilidade
