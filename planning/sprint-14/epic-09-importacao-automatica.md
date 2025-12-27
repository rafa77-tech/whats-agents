# E09 - Importação Automática

## Objetivo

Importar vagas do pipeline de grupos para a tabela principal de vagas com regras de confiança.

## Contexto

Após deduplicação, vagas com alta confiança devem ir automaticamente para `vagas`. Vagas com confiança média vão para fila de revisão. Vagas com baixa confiança são descartadas.

**Regras de importação:**
- Confiança >= 90%: Importa automaticamente
- Confiança 70-90%: Fila de revisão
- Confiança < 70%: Descarta (marca como baixa_confiança)

## Stories

### S09.1 - Calcular confiança geral da vaga

**Descrição:** Função para calcular score de confiança consolidado.

```python
# app/services/grupos/importador.py

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class ScoreConfianca:
    """Scores de confiança da vaga."""
    hospital: float = 0.0
    especialidade: float = 0.0
    data: float = 0.0
    periodo: float = 0.0
    valor: float = 0.0
    geral: float = 0.0
    detalhes: dict = None


def calcular_confianca_geral(vaga: dict) -> ScoreConfianca:
    """
    Calcula score de confiança consolidado.

    Pesos:
    - Hospital: 30%
    - Especialidade: 30%
    - Data: 25%
    - Período: 10%
    - Valor: 5%
    """
    scores = ScoreConfianca(detalhes={})

    # Hospital (30%)
    scores.hospital = vaga.get("hospital_match_score", 0.0)
    scores.detalhes["hospital"] = scores.hospital

    # Especialidade (30%)
    scores.especialidade = vaga.get("especialidade_match_score", 0.0)
    scores.detalhes["especialidade"] = scores.especialidade

    # Data (25%) - baseado em confiança da extração
    scores.data = vaga.get("data_confianca", 0.0) if vaga.get("data") else 0.0
    scores.detalhes["data"] = scores.data

    # Período (10%)
    scores.periodo = 1.0 if vaga.get("periodo_id") else 0.5
    scores.detalhes["periodo"] = scores.periodo

    # Valor (5%)
    valor = vaga.get("valor")
    if valor and 100 <= valor <= 10000:
        scores.valor = 1.0
    elif valor:
        scores.valor = 0.5
    else:
        scores.valor = 0.3  # Sem valor não é crítico
    scores.detalhes["valor"] = scores.valor

    # Cálculo ponderado
    scores.geral = (
        scores.hospital * 0.30 +
        scores.especialidade * 0.30 +
        scores.data * 0.25 +
        scores.periodo * 0.10 +
        scores.valor * 0.05
    )

    return scores
```

**Estimativa:** 1h

---

### S09.2 - Validar dados mínimos para importação

**Descrição:** Verificar se vaga tem dados suficientes para importar.

```python
@dataclass
class ResultadoValidacao:
    """Resultado da validação de vaga."""
    valido: bool
    erros: list
    avisos: list


def validar_para_importacao(vaga: dict) -> ResultadoValidacao:
    """
    Valida se vaga pode ser importada.

    Requisitos obrigatórios:
    - hospital_id
    - especialidade_id
    - data (futuro)

    Avisos (não bloqueiam):
    - Sem período
    - Sem valor
    - Data muito distante
    """
    erros = []
    avisos = []

    # Obrigatórios
    if not vaga.get("hospital_id"):
        erros.append("hospital_id ausente")

    if not vaga.get("especialidade_id"):
        erros.append("especialidade_id ausente")

    if not vaga.get("data"):
        erros.append("data ausente")
    else:
        # Validar data
        from datetime import datetime, timedelta
        try:
            data_vaga = datetime.strptime(vaga["data"], "%Y-%m-%d").date()
            hoje = datetime.now().date()

            if data_vaga < hoje:
                erros.append("data no passado")
            elif data_vaga > hoje + timedelta(days=90):
                avisos.append("data muito distante (>90 dias)")

        except ValueError:
            erros.append("data em formato inválido")

    # Avisos
    if not vaga.get("periodo_id"):
        avisos.append("período não identificado")

    if not vaga.get("valor"):
        avisos.append("valor não informado")

    return ResultadoValidacao(
        valido=len(erros) == 0,
        erros=erros,
        avisos=avisos
    )
```

**Estimativa:** 1h

---

### S09.3 - Criar vaga na tabela principal

**Descrição:** Inserir vaga do grupo na tabela `vagas`.

```python
from app.services.supabase import supabase


async def criar_vaga_principal(vaga_grupo: dict) -> UUID:
    """
    Cria vaga na tabela principal a partir de vaga do grupo.

    Args:
        vaga_grupo: Dados da vaga_grupo normalizada

    Returns:
        UUID da vaga criada
    """
    # Mapear campos
    dados_vaga = {
        "hospital_id": vaga_grupo["hospital_id"],
        "especialidade_id": vaga_grupo["especialidade_id"],
        "data": vaga_grupo["data"],
        "periodo_id": vaga_grupo.get("periodo_id"),
        "setor_id": vaga_grupo.get("setor_id"),
        "tipos_vaga_id": vaga_grupo.get("tipo_vaga_id"),
        "valor": vaga_grupo.get("valor"),
        "hora_inicio": vaga_grupo.get("hora_inicio"),
        "hora_fim": vaga_grupo.get("hora_fim"),
        "observacoes": vaga_grupo.get("observacoes_raw"),
        "status": "disponivel",
        "origem": "grupo_whatsapp",
        "vaga_grupo_id": vaga_grupo["id"],  # Referência à origem
    }

    # Remover None
    dados_vaga = {k: v for k, v in dados_vaga.items() if v is not None}

    result = supabase.table("vagas").insert(dados_vaga).execute()

    return UUID(result.data[0]["id"])


async def atualizar_vaga_grupo_importada(
    vaga_grupo_id: UUID,
    vaga_id: UUID
) -> None:
    """Marca vaga_grupo como importada."""

    supabase.table("vagas_grupo") \
        .update({
            "status": "importada",
            "vaga_importada_id": str(vaga_id),
            "importada_em": "now()",
        }) \
        .eq("id", str(vaga_grupo_id)) \
        .execute()
```

**Estimativa:** 1.5h

---

### S09.4 - Implementar regras de decisão

**Descrição:** Aplicar regras de confiança para decidir ação.

```python
from enum import Enum


class AcaoImportacao(Enum):
    IMPORTAR = "importar"
    REVISAR = "revisar"
    DESCARTAR = "descartar"


THRESHOLD_IMPORTAR = 0.90
THRESHOLD_REVISAR = 0.70


def decidir_acao(score: ScoreConfianca, validacao: ResultadoValidacao) -> AcaoImportacao:
    """
    Decide ação baseado em confiança e validação.

    Regras:
    - Inválido: DESCARTAR
    - Confiança >= 90%: IMPORTAR
    - Confiança 70-90%: REVISAR
    - Confiança < 70%: DESCARTAR
    """
    if not validacao.valido:
        return AcaoImportacao.DESCARTAR

    if score.geral >= THRESHOLD_IMPORTAR:
        return AcaoImportacao.IMPORTAR

    if score.geral >= THRESHOLD_REVISAR:
        return AcaoImportacao.REVISAR

    return AcaoImportacao.DESCARTAR


async def aplicar_acao(
    vaga_grupo_id: UUID,
    acao: AcaoImportacao,
    score: ScoreConfianca,
    validacao: ResultadoValidacao
) -> dict:
    """Aplica a ação decidida na vaga."""

    resultado = {
        "vaga_grupo_id": str(vaga_grupo_id),
        "acao": acao.value,
        "score": score.geral,
    }

    if acao == AcaoImportacao.IMPORTAR:
        # Buscar dados completos
        vaga = supabase.table("vagas_grupo") \
            .select("*") \
            .eq("id", str(vaga_grupo_id)) \
            .single() \
            .execute()

        vaga_id = await criar_vaga_principal(vaga.data)
        await atualizar_vaga_grupo_importada(vaga_grupo_id, vaga_id)

        resultado["vaga_id"] = str(vaga_id)
        resultado["status"] = "importada"

    elif acao == AcaoImportacao.REVISAR:
        # Mover para fila de revisão
        supabase.table("vagas_grupo") \
            .update({
                "status": "aguardando_revisao",
                "confianca_geral": score.geral,
                "motivo_status": "confianca_media",
            }) \
            .eq("id", str(vaga_grupo_id)) \
            .execute()

        resultado["status"] = "aguardando_revisao"

    else:  # DESCARTAR
        motivo = "baixa_confianca"
        if not validacao.valido:
            motivo = f"validacao_falhou: {', '.join(validacao.erros)}"

        supabase.table("vagas_grupo") \
            .update({
                "status": "descartada",
                "confianca_geral": score.geral,
                "motivo_status": motivo,
            }) \
            .eq("id", str(vaga_grupo_id)) \
            .execute()

        resultado["status"] = "descartada"
        resultado["motivo"] = motivo

    return resultado
```

**Estimativa:** 2h

---

### S09.5 - Processador de importação

**Descrição:** Orquestra o processo de importação.

```python
async def processar_importacao(vaga_grupo_id: UUID) -> dict:
    """
    Processa importação de uma vaga do grupo.

    Fluxo:
    1. Buscar vaga
    2. Calcular confiança
    3. Validar dados
    4. Decidir ação
    5. Aplicar ação
    """
    # Buscar vaga
    vaga = supabase.table("vagas_grupo") \
        .select("*") \
        .eq("id", str(vaga_grupo_id)) \
        .single() \
        .execute()

    if not vaga.data:
        return {"erro": "vaga_nao_encontrada"}

    dados = vaga.data

    # Verificar se já foi processada
    if dados.get("status") in ["importada", "descartada"]:
        return {"erro": "vaga_ja_processada", "status": dados["status"]}

    # Verificar se é duplicada
    if dados.get("eh_duplicada"):
        return {"erro": "vaga_duplicada"}

    # Calcular confiança
    score = calcular_confianca_geral(dados)

    # Validar
    validacao = validar_para_importacao(dados)

    # Decidir e aplicar
    acao = decidir_acao(score, validacao)
    resultado = await aplicar_acao(vaga_grupo_id, acao, score, validacao)

    return resultado


async def processar_batch_importacao(limite: int = 50) -> dict:
    """Processa batch de vagas prontas para importação."""

    # Buscar vagas normalizadas e deduplicadas
    vagas = supabase.table("vagas_grupo") \
        .select("id") \
        .eq("status", "normalizada") \
        .eq("eh_duplicada", False) \
        .is_("vaga_importada_id", "null") \
        .limit(limite) \
        .execute()

    stats = {
        "total": len(vagas.data),
        "importadas": 0,
        "revisao": 0,
        "descartadas": 0,
        "erros": 0,
    }

    for vaga in vagas.data:
        try:
            resultado = await processar_importacao(UUID(vaga["id"]))

            if resultado.get("status") == "importada":
                stats["importadas"] += 1
            elif resultado.get("status") == "aguardando_revisao":
                stats["revisao"] += 1
            elif resultado.get("status") == "descartada":
                stats["descartadas"] += 1
            else:
                stats["erros"] += 1

        except Exception as e:
            logger.error(f"Erro ao importar vaga {vaga['id']}: {e}")
            stats["erros"] += 1

    return stats
```

**Estimativa:** 2h

---

### S09.6 - Adicionar coluna de referência em vagas

**Descrição:** Migração para adicionar referência à vaga de grupo.

```sql
-- Adicionar referência à origem
ALTER TABLE vagas
ADD COLUMN origem VARCHAR(50) DEFAULT 'manual',
ADD COLUMN vaga_grupo_id UUID REFERENCES vagas_grupo(id);

-- Índice
CREATE INDEX idx_vagas_vaga_grupo_id ON vagas(vaga_grupo_id);

-- Comentário
COMMENT ON COLUMN vagas.origem IS 'Origem da vaga: manual, grupo_whatsapp, api';
```

**Estimativa:** 0.5h

---

### S09.7 - Testes de importação

**Estimativa:** 2h

---

## Resumo

| Story | Descrição | Estimativa |
|-------|-----------|------------|
| S09.1 | Cálculo de confiança | 1h |
| S09.2 | Validação para importação | 1h |
| S09.3 | Criar vaga principal | 1.5h |
| S09.4 | Regras de decisão | 2h |
| S09.5 | Processador de importação | 2h |
| S09.6 | Migração vagas | 0.5h |
| S09.7 | Testes | 2h |

**Total:** 10h (~1.25 dias)

## Dependências

- E06 (Fuzzy Match) - scores de match
- E08 (Deduplicação) - vagas deduplicadas

## Entregáveis

- Cálculo de confiança ponderado
- Validação de dados mínimos
- Regras de decisão automáticas
- Importação para tabela principal
- Rastreabilidade de origem
