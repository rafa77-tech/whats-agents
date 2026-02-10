# Pipeline de Grupos WhatsApp v3 (LLM Unificado)

**Sprints:** 51-53 (Discovery Intelligence Pipeline)
**Versão:** 3.0 (LLM Unificado)
**Status:** Produção (feature flag)

---

## Visão Geral

O Pipeline de Grupos monitora grupos de WhatsApp em busca de ofertas de plantões médicos, extrai dados estruturados e importa vagas automaticamente para o sistema.

### Objetivo

Capturar vagas médicas postadas em grupos WhatsApp de forma automática, reduzindo trabalho manual e aumentando a cobertura de oportunidades disponíveis para Julia oferecer aos médicos.

### Contexto de Mercado

| Aspecto | Realidade |
|---------|-----------|
| Volume | Grupos postam centenas de vagas por dia |
| Qualidade | Mensagens variam muito em formato e clareza |
| Duplicação | Mesma vaga é postada em múltiplos grupos |
| Urgência | Vagas com pouco prazo de preenchimento |

---

## Arquitetura do Pipeline

### Fluxo de Processamento

```
Webhook WhatsApp
    ↓
[1] Ingestão → mensagens_grupo
    ↓
[2] Normalização → Parse inicial, contatos, grupos
    ↓
[3] Classificação (Heurística + LLM)
    ├─ Descartada → Status: ignorada
    └─ Potencial vaga
        ↓
[4] Extração LLM (v3) → Dados estruturados
    ↓
[5] Normalização → Match de hospitais/especialidades
    ↓
[6] Deduplicação → Hash de vaga única
    ├─ Duplicada → Marca como duplicata, registra fonte
    └─ Nova
        ↓
[7] Importação → vagas (tabela principal)
    ├─ Confiança ≥ 85% → Importa automaticamente
    ├─ Confiança 70-85% → Fila de revisão
    └─ Confiança < 70% → Descarta
```

### Estágios

| Estágio | Descrição | Output |
|---------|-----------|--------|
| **Pendente** | Mensagem recebida via webhook | mensagens_grupo (status: pendente) |
| **Heurística** | Filtro rápido por keywords | score_heuristica, passou_heuristica |
| **Classificação** | LLM confirma se é oferta | confianca_classificacao, eh_oferta |
| **Extração** | LLM extrai dados estruturados | vagas_grupo (dados brutos) |
| **Normalização** | Match com entidades do banco | hospital_id, especialidade_id |
| **Deduplicação** | Detecta vagas repetidas | hash_dedup, eh_duplicada |
| **Importação** | Cria vaga na tabela principal | vagas (status: aberta) |

---

## Módulos do Sistema

### 1. Ingestão (`ingestor.py`)

**Responsabilidade:** Receber mensagens do webhook e persistir no banco.

#### Funções Principais

```python
async def ingerir_mensagem_grupo(
    mensagem: MensagemRecebida,
    dados_raw: dict
) -> Optional[UUID]
```

**Fluxo:**
1. Extrai JID do grupo e remetente
2. Cria/atualiza registro de grupo (`grupos_whatsapp`)
3. Cria/atualiza registro de contato (`contatos_grupo`)
4. Salva mensagem (`mensagens_grupo`)
5. Enfileira para processamento se status = pendente

#### Detalhes Importantes

- **Resolução de LID:** Quando o remetente usa LID (LinkedIn ID), tenta resolver para telefone real via API
- **Separação nome/empresa:** Detecta padrões como "João Silva - SMPV" e separa em campos distintos
- **Contadores:** Atualiza contadores de mensagens por grupo e contato

#### Status de Mensagem

| Status | Descrição |
|--------|-----------|
| `pendente` | Mensagem válida para processamento |
| `ignorada_midia` | Contém mídia (imagem, áudio, etc) |
| `ignorada_curta` | Menos de 5 caracteres |
| `heuristica_passou` | Passou pela heurística |
| `heuristica_rejeitou` | Descartada pela heurística |
| `classificada_oferta` | LLM confirmou como oferta |
| `classificada_nao_oferta` | LLM descartou |

---

### 2. Normalização (`normalizador.py`)

**Responsabilidade:** Fazer match de dados brutos com entidades do banco.

#### Estratégias de Match

**Hospital:**
1. Busca alias exato (`hospitais_alias.alias_normalizado`)
2. Busca por similaridade (pg_trgm) com threshold = 0.3
3. Fallback: ILIKE parcial

**Especialidade:**
1. Busca alias exato (`especialidades_alias.alias_normalizado`)
2. Busca por similaridade com threshold = 0.3

**Período:**
1. Busca em mapa de termos (`MAPA_PERIODOS`)
2. Inferência por horário se não extraído

**Inferência de Período por Horário:**
```python
def inferir_periodo_por_horario(hora_inicio: str) -> Optional[str]:
    # 19:00-06:00 = Noturno
    if h_inicio >= 19 or h_inicio < 6:
        return "Noturno"
    # 06:00-13:00 = Diurno
    elif 6 <= h_inicio < 13:
        return "Diurno"
    # 13:00-19:00 = Vespertino
    else:
        return "Vespertino"
```

#### Normalização de Texto

```python
def normalizar_para_busca(texto: str) -> str:
    """
    - Lowercase
    - Remove parênteses e conteúdo
    - Remove acentos
    - Remove caracteres especiais
    - Remove espaços extras
    """
```

#### Criação Automática de Hospitais

Quando hospital não é encontrado, cria registro automaticamente:
- Nome a partir do texto bruto
- Ativo = false (requer validação)
- Flag `hospital_criado = true` na vaga

---

### 3. Classificação (`classificador.py` + `classificador_llm.py`)

**Responsabilidade:** Determinar se mensagem é uma oferta de plantão.

#### Estratégia Híbrida (2 camadas)

**Camada 1: Heurística (rápida, barata)**
- Keywords positivas: plantão, vaga, urgente, hospital
- Keywords negativas: cancelado, coberto, fechado
- Score de 0 a 1

**Thresholds:**
- Score < 0.4: Descarta direto
- Score ≥ 0.7: Pula LLM, vai direto para extração
- Score 0.4-0.7: Envia para LLM

**Camada 2: LLM (precisa, custo controlado)**
- Claude Haiku 3.5
- Prompt específico para classificação
- Retorna: `{eh_oferta, confianca, motivo}`

#### Cache Redis

Ambas camadas usam cache:
- TTL: 7 dias (classificação), 24h (extração)
- Chave: Hash MD5 do texto normalizado
- Hit rate esperado: ~40% (mensagens similares)

---

### 4. Extração

#### Pipeline v2 (Regex - padrão)

**Módulos:**
- `parser_mensagem.py`: Separa seções por emoji/contexto
- `extrator_hospitais.py`: Extrai nomes de hospitais
- `extrator_datas.py`: Extrai datas e períodos
- `extrator_valores.py`: Extrai valores e regras (seg-sex, sab-dom)
- `extrator_contato.py`: Extrai nome e WhatsApp
- `extrator_especialidades.py`: Extrai especialidades
- `gerador_vagas.py`: Combina tudo em vagas atômicas

**Feature Flag:** `EXTRATOR_V2_ENABLED=true` (padrão)

**Vantagens:**
- Rápido (sem chamada LLM)
- Determinístico
- Bom para formatos padronizados

**Limitações:**
- Bug R$ 202 (captura "202" de "19/01/2026")
- Perde contexto semântico
- Não normaliza especialidades

---

#### Pipeline v3 (LLM Unificado - Sprint 52)

**Módulo:** `extrator_llm.py`

**Feature Flag:** `PIPELINE_V3_ENABLED=true`

**Diferenciais:**

1. **Classificação + Extração em 1 chamada**
   - v2: 2 chamadas LLM (classificar → extrair)
   - v3: 1 chamada LLM (tudo junto)

2. **Contexto Semântico**
   - Entende "R$ 10.000 pelos 5 plantões" → divide por 5
   - Distingue "02/2026" (data) de "R$ 202" (valor)
   - Normaliza "GO" → "Ginecologia e Obstetrícia"

3. **Normalização Automática de Especialidades**
   - Prompt inclui lista de 64 especialidades válidas
   - LLM retorna especialidade normalizada
   - Reduz erros de match

**Prompt (simplificado):**
```
Analise a mensagem e extraia vagas de plantão médico.

REGRAS CRÍTICAS:
1. VALOR é o preço POR PLANTÃO, não o total
   - "R$ 10.000 por 5 plantões" → valor = 2000
2. NUNCA confunda datas com valores
   - "19/01/2026" são DATAS, não valores
3. ESPECIALIDADE deve ser normalizada:
   - "GO" → "Ginecologia e Obstetrícia"
   - "CM" → "Clínica Médica"

Retorne JSON:
{
  "eh_vaga": true/false,
  "vagas": [
    {
      "hospital": "...",
      "especialidade": "...",
      "data": "YYYY-MM-DD",
      "valor": int ou null
    }
  ]
}
```

**Resultado:**
```python
@dataclass
class ResultadoExtracaoLLM:
    eh_vaga: bool
    confianca: float
    motivo_descarte: Optional[str]
    vagas: List[dict]  # Já estruturados
    tokens_usados: int
```

**Conversão para VagaAtomica:**
- LLM retorna JSON genérico
- `converter_para_vagas_atomicas()` mapeia para `VagaAtomica`
- Compatível com resto do pipeline

---

### 5. Deduplicação (`deduplicador.py`)

**Responsabilidade:** Detectar vagas postadas em múltiplos grupos.

#### Estratégia

**Hash de Deduplicação:**
```python
def calcular_hash_dedup(
    hospital_id: UUID,
    data: str,  # YYYY-MM-DD
    periodo_id: Optional[UUID],
    especialidade_id: UUID
) -> str:
    """MD5 de: hospital + data + período + especialidade"""
```

**Janela Temporal:** 48 horas

#### Fluxo

1. Calcula hash da vaga
2. Busca vaga com mesmo hash (últimas 48h)
3. Se encontrou:
   - Marca vaga atual como duplicada
   - Registra como fonte adicional (`vagas_grupo_fontes`)
   - Incrementa `qtd_fontes` na vaga principal
4. Se não encontrou:
   - Registra como vaga principal (fonte 1)
   - Marca `pronta_importacao`

#### Modelo de Fontes

```sql
-- Vaga principal
vagas_grupo (id, qtd_fontes=3, ...)

-- Fontes (cada grupo que postou)
vagas_grupo_fontes
  - vaga_grupo_id (FK)
  - mensagem_id (FK)
  - grupo_id (FK)
  - ordem (1, 2, 3...)
  - texto_original
  - valor_informado (se diferente)
```

**Benefícios:**
- Rastreia origem de cada vaga
- Detecta variação de valores entre grupos
- Aumenta confiança (mais fontes = mais confiável)

---

### 6. Importação (`importador.py`)

**Responsabilidade:** Criar vaga na tabela principal com decisão automática.

#### Score de Confiança

**Pesos:**
- Hospital: 30%
- Especialidade: 30%
- Data: 25%
- Período: 10%
- Valor: 5%

**Cálculo:**
```python
score_geral = (
    hospital_match_score * 0.30 +
    especialidade_match_score * 0.30 +
    confianca_data * 0.25 +
    (1.0 se tem periodo else 0.5) * 0.10 +
    confianca_valor * 0.05
)
```

#### Regras de Decisão

| Score | Ação | Motivo |
|-------|------|--------|
| ≥ 85% | **Importar** | Alta confiança, dados completos |
| 70-85% | **Revisar** | Confiança média, requer validação humana |
| < 70% | **Descartar** | Baixa confiança ou dados incompletos |

**Nota:** Threshold foi reduzido de 90% para 85% na Sprint 29, pois Julia pode intermediar ofertas mesmo com dados parciais.

#### Validação

**Requisitos Obrigatórios:**
- `hospital_id` presente
- `especialidade_id` presente
- `data` presente e futura

**Avisos (não bloqueiam):**
- Sem período identificado
- Sem valor informado
- Data muito distante (>90 dias)

---

### 7. Pipeline Worker (`pipeline_worker.py` + `grupos_worker.py`)

**Responsabilidade:** Orquestrar execução de todos os estágios.

#### Classe PipelineGrupos

Cada estágio tem um método:
```python
class PipelineGrupos:
    async def processar_pendente(item: dict) -> ResultadoPipeline
    async def processar_classificacao(item: dict) -> ResultadoPipeline
    async def processar_extracao(item: dict) -> ResultadoPipeline
    async def processar_normalizacao(item: dict) -> ResultadoPipeline
    async def processar_deduplicacao(item: dict) -> ResultadoPipeline
    async def processar_importacao(item: dict) -> ResultadoPipeline
```

**ResultadoPipeline:**
```python
@dataclass
class ResultadoPipeline:
    acao: str  # "descartar", "classificar", "extrair", "normalizar", ...
    mensagem_id: Optional[UUID]
    vaga_grupo_id: Optional[UUID]
    motivo: Optional[str]
    score: Optional[float]
    vagas_criadas: Optional[List[str]]  # Para extração com múltiplas vagas
```

#### Classe GruposWorker

Executor assíncrono com paralelismo controlado:
```python
class GruposWorker:
    def __init__(
        batch_size: int = 50,
        intervalo_segundos: int = 10,
        max_workers: int = 5
    )

    async def start()  # Loop contínuo
    async def processar_ciclo()  # Um ciclo de todas as filas
```

**Fluxo de um Ciclo:**
1. Para cada estágio (em ordem):
2. Busca `batch_size` itens pendentes
3. Processa em paralelo (máx `max_workers`)
4. Atualiza estágio conforme `ResultadoPipeline.acao`
5. Se extração criou múltiplas vagas:
   - Cria itens separados na fila para cada vaga
   - Marca item original como finalizado

**Paralelismo:**
- Usa `asyncio.Semaphore` para limitar workers
- Cada item processado independentemente
- Erros não travam o batch (retry mantém no mesmo estágio)

---

## Sistema de Filas

### Tabela: fila_pipeline_grupos

```sql
CREATE TABLE fila_pipeline_grupos (
  id UUID PRIMARY KEY,
  mensagem_id UUID REFERENCES mensagens_grupo,
  vaga_grupo_id UUID REFERENCES vagas_grupo,  -- NULL até extração
  estagio TEXT NOT NULL,  -- enum EstagioPipeline
  tentativas INT DEFAULT 0,
  erro TEXT,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

**Índices:**
- `(estagio, updated_at)` - Busca de pendentes por estágio
- `(mensagem_id)` - Rastreabilidade
- `(vaga_grupo_id)` - Rastreabilidade

### EstagioPipeline (Enum)

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

### Funções de Gestão

```python
# Buscar próximos N itens pendentes
async def buscar_proximos_pendentes(
    estagio: EstagioPipeline,
    limite: int = 50
) -> List[dict]

# Atualizar estágio de um item
async def atualizar_estagio(
    item_id: UUID,
    novo_estagio: EstagioPipeline,
    vaga_grupo_id: Optional[UUID] = None,
    erro: Optional[str] = None
)

# Criar itens para múltiplas vagas (após extração)
async def criar_itens_para_vagas(
    mensagem_id: UUID,
    vagas_ids: List[str]
)

# Estatísticas da fila
async def obter_estatisticas_fila() -> dict
```

---

## Diferenças v2 vs v3

| Aspecto | v2 (Regex) | v3 (LLM Unificado) |
|---------|------------|---------------------|
| **Classificação** | LLM separado | Junto com extração |
| **Extração** | 6 módulos regex | 1 chamada LLM |
| **Chamadas LLM** | 2 (classificar + extrair) | 1 (tudo junto) |
| **Contexto semântico** | Não | Sim |
| **Bug R$ 202** | Presente | Resolvido |
| **Normalização especialidades** | Manual (post-processing) | Automática (no prompt) |
| **Tokens usados** | ~500 (classificação) + 1000 (extração) | ~1200 (total) |
| **Custo** | 2 chamadas × $0.25/1M | 1 chamada × $0.25/1M |
| **Velocidade** | Rápido (regex) + 2 chamadas API | 1 chamada API |
| **Precisão valores** | Regex ingênuo | Compreensão total/por plantão |
| **Manutenção** | 6 módulos + regras | 1 prompt |

### Quando Usar Cada Versão

**v2 (Regex):**
- Grupos com formato muito padronizado
- Volume altíssimo (reduz custo)
- Mensagens simples (1 vaga por mensagem)

**v3 (LLM):**
- Grupos com formato variado
- Mensagens complexas (múltiplas vagas)
- Quando precisão de valores é crítica
- Quando especialidades vêm abreviadas

---

## Monitoramento e Métricas

### Métricas de Pipeline

```python
async def obter_estatisticas_fila() -> dict:
    """
    Retorna:
    {
      "pendente": 120,
      "heuristica": 45,
      "classificacao": 30,
      "extracao": 15,
      "normalizacao": 10,
      "deduplicacao": 5,
      "importacao": 3,
      "finalizado": 1850,
      "descartado": 620,
      "erro": 8
    }
    """
```

### Métricas de Extração (v3)

**Logs estruturados:**
```python
logger.info(
    f"[Pipeline v3] SUCESSO mensagem_id={msg_id} "
    f"vagas_criadas={len(vagas)} "
    f"tempo_ms={tempo} tokens={tokens}"
)
```

**Campos rastreados:**
- `tempo_processamento_ms` - Latência total
- `tokens_usados` - Custo por mensagem
- `warnings` - Alertas (hospital extraído do texto completo, etc)
- `do_cache` - Hit/miss de cache

### Métricas de Deduplicação

```python
async def obter_estatisticas_dedup() -> dict:
    """
    {
      "total_vagas": 2500,
      "vagas_unicas": 1800,
      "vagas_duplicadas": 700,
      "vagas_multi_fonte": 350,
      "taxa_duplicacao": 28.0  # %
    }
    """
```

### Métricas de Importação

```python
async def obter_estatisticas_importacao() -> dict:
    """
    {
      "total_vagas_grupo": 1800,
      "importadas": 1200,
      "aguardando_revisao": 350,
      "descartadas": 250,
      "prontas_importacao": 120,
      "taxa_importacao": 66.7  # %
    }
    """
```

### Health Check

```python
async def obter_status_worker() -> dict:
    """
    {
      "status": "healthy",  # healthy, degraded, unhealthy
      "fila": {...},
      "travados": 12,  # Itens sem atualização >1h
      "timestamp": "2026-02-10T15:30:00Z"
    }
    """
```

**Critérios de Status:**
- `healthy`: < 100 itens travados
- `degraded`: 100-500 itens travados
- `unhealthy`: > 500 itens travados

---

## Troubleshooting

### Problemas Comuns

#### 1. Mensagens não processadas (fila crescendo)

**Sintomas:**
- Estágio `pendente` com muitos itens
- Worker não consome fila

**Diagnóstico:**
```python
# Verificar worker
status = await obter_status_worker()
print(status["fila"])

# Verificar erros recentes
travados = await obter_itens_travados(horas=1)
```

**Soluções:**
- Aumentar `batch_size` do worker
- Aumentar `max_workers` (paralelismo)
- Verificar se worker está rodando (Railway logs)
- Verificar rate limits da API Anthropic

---

#### 2. Muitas vagas na fila de revisão

**Sintomas:**
- Status `aguardando_revisao` com centenas de vagas
- Taxa de importação automática baixa (<50%)

**Diagnóstico:**
```python
stats = await obter_estatisticas_importacao()
print(f"Taxa importação: {stats['taxa_importacao']}%")

# Verificar scores
vagas_revisao = await listar_vagas_para_revisao(limite=50)
for v in vagas_revisao:
    print(f"{v['confianca_geral']:.2f} - {v['motivo_status']}")
```

**Soluções:**
- Criar aliases para hospitais recorrentes
- Criar aliases para especialidades abreviadas
- Reduzir threshold de importação (se aceitável)
- Melhorar prompt do LLM v3 (normalização)

---

#### 3. Bug de valores (R$ 202)

**Sintomas:**
- Vagas com valor R$ 202, R$ 2026, etc (claramente errado)

**Diagnóstico:**
```sql
-- Buscar vagas com valores suspeitos
SELECT id, valor, texto_original
FROM vagas_grupo
WHERE valor BETWEEN 100 AND 300
  AND texto_original LIKE '%2026%';
```

**Soluções:**
- **Imediato:** Ativar pipeline v3 (`PIPELINE_V3_ENABLED=true`)
- **v2 (temporário):** Adicionar filtro post-processing para valores < 500

---

#### 4. Duplicatas não detectadas

**Sintomas:**
- Mesma vaga criada múltiplas vezes
- `qtd_fontes` sempre = 1

**Diagnóstico:**
```sql
-- Buscar possíveis duplicatas
SELECT hospital_id, data, periodo_id, especialidade_id, COUNT(*)
FROM vagas_grupo
WHERE eh_duplicada = false
GROUP BY 1,2,3,4
HAVING COUNT(*) > 1;
```

**Soluções:**
- Verificar se normalização está funcionando (hospital_id e especialidade_id preenchidos)
- Verificar janela temporal (48h pode ser curta para alguns grupos)
- Verificar se hash está sendo calculado corretamente

---

#### 5. Cache não funcionando (alto custo LLM)

**Sintomas:**
- `do_cache = false` em todas as mensagens
- Tokens usados crescendo linearmente

**Diagnóstico:**
```python
# Testar cache manualmente
from app.services.grupos.extrator_llm import buscar_extracao_cache
cached = await buscar_extracao_cache("texto de teste")
print(f"Cache hit: {cached is not None}")
```

**Soluções:**
- Verificar se Redis está rodando
- Verificar logs de erro do Redis
- Verificar TTL do cache (pode ter expirado)
- Verificar se hash está sendo gerado corretamente

---

#### 6. Especialidades não normalizadas

**Sintomas:**
- `especialidade_match_score` baixo
- Muitas vagas em revisão por "match_incompleto:especialidade"

**Diagnóstico:**
```sql
-- Especialidades não mapeadas
SELECT especialidade_raw, COUNT(*)
FROM vagas_grupo
WHERE especialidade_id IS NULL
  AND especialidade_raw IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC;
```

**Soluções:**
- Criar aliases para abreviações comuns:
  - "GO" → "Ginecologia e Obstetrícia"
  - "CM" → "Clínica Médica"
  - "UTI" → "Medicina Intensiva"
- Ativar pipeline v3 (normaliza automaticamente no prompt)
- Usar ferramenta de criação de alias no dashboard

---

### Comandos Úteis

**Reprocessar mensagens travadas:**
```python
# Resetar itens travados para tentativa 0
await resetar_itens_travados(horas=2)
```

**Processar ciclo manualmente:**
```python
# Via endpoint ou direto
from app.workers.grupos_worker import processar_ciclo_grupos
resultado = await processar_ciclo_grupos(batch_size=100)
```

**Limpar fila de erros:**
```sql
-- Mensagens com erro persistente (>5 tentativas)
DELETE FROM fila_pipeline_grupos
WHERE estagio = 'erro' AND tentativas > 5;
```

**Forçar reprocessamento de mensagem:**
```python
from app.services.grupos.fila import enfileirar_mensagem
await enfileirar_mensagem(mensagem_id, estagio=EstagioPipeline.PENDENTE)
```

---

## Configuração

### Variáveis de Ambiente

```bash
# Feature flags
EXTRATOR_V2_ENABLED=true          # Pipeline v2 (regex)
PIPELINE_V3_ENABLED=false         # Pipeline v3 (LLM unificado)

# Thresholds
THRESHOLD_HEURISTICA=0.4          # Mínimo para não descartar
THRESHOLD_HEURISTICA_ALTO=0.7     # Pula LLM se atingir
THRESHOLD_LLM=0.7                 # Confiança mínima do LLM

# Cache
CACHE_TTL_CLASSIFICACAO=604800    # 7 dias
CACHE_TTL_EXTRACAO=86400          # 24 horas

# Importação
THRESHOLD_IMPORTAR=0.85           # Importa automaticamente
THRESHOLD_REVISAR=0.70            # Envia para revisão

# Worker
GRUPOS_BATCH_SIZE=50              # Itens por ciclo
GRUPOS_MAX_WORKERS=5              # Paralelismo
GRUPOS_INTERVALO=10               # Segundos entre ciclos
```

### Thresholds Recomendados

| Ambiente | Heurística | LLM | Importação |
|----------|------------|-----|------------|
| **Desenvolvimento** | 0.3 | 0.6 | 0.80 |
| **Staging** | 0.4 | 0.7 | 0.85 |
| **Produção** | 0.4 | 0.7 | 0.85 |

---

## Roadmap

### Sprint 54 (Planejado)

- [ ] Dashboard de monitoramento em tempo real
- [ ] Alertas Slack para itens travados
- [ ] Auto-scaling de workers baseado em fila
- [ ] Retry exponencial com backoff

### Melhorias Futuras

- [ ] Pipeline v4: Extração multi-modal (OCR de imagens)
- [ ] Aprendizado contínuo (feedback de Julia sobre ofertas)
- [ ] Detecção de padrões de grupos (formato predominante)
- [ ] Sugestão automática de aliases (ML)
- [ ] A/B test v2 vs v3 com métricas de qualidade

---

## Referências

### Código-fonte

- **Ingestão:** `app/services/grupos/ingestor.py`
- **Classificação:** `app/services/grupos/classificador.py`, `classificador_llm.py`
- **Extração v2:** `app/services/grupos/extrator_v2/pipeline.py`
- **Extração v3:** `app/services/grupos/extrator_v2/extrator_llm.py`
- **Normalização:** `app/services/grupos/normalizador.py`
- **Deduplicação:** `app/services/grupos/deduplicador.py`
- **Importação:** `app/services/grupos/importador.py`
- **Pipeline:** `app/services/grupos/pipeline_worker.py`
- **Worker:** `app/workers/grupos_worker.py`

### Documentação Relacionada

- `docs/arquitetura/banco-de-dados.md` - Tabelas do pipeline
- `docs/integracoes/evolution-api-quickref.md` - Webhook WhatsApp
- `planning/sprint-51/` - Correções arquiteturais
- `planning/sprint-52/` - Pipeline v3 (LLM)
- `planning/sprint-53/` - Discovery Intelligence

### Sprints

| Sprint | Tema | Épicos |
|--------|------|--------|
| 14 | Pipeline Grupos v1 | E02-E11 (Ingestão até Worker) |
| 40 | Extrator v2 | E01-E08 (Vagas atômicas) |
| 51 | Revisão Arquitetural | E01-E04 (Correções críticas) |
| 52 | Pipeline v3 | E01-E03 (LLM unificado) |
| 53 | Discovery Intelligence | E01-E04 (Otimizações) |

---

**Última atualização:** 10/02/2026
**Autor:** Documentação técnica gerada a partir do código
**Versão do documento:** 1.0
