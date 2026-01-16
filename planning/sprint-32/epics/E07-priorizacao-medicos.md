# E07: Priorização de Médicos

**Fase:** 2 - Julia Autônoma
**Estimativa:** 4h
**Prioridade:** Média
**Dependências:** E06 (Trigger Oferta)

---

## Objetivo

Implementar algoritmo de priorização que ordena médicos para receber ofertas, garantindo que Julia entre em contato primeiro com médicos mais propensos a aceitar.

## Problema

Sem priorização, Julia pode:
- Ofertar para médico que nunca responde
- Perder oportunidade com médico engajado
- Disparar para todos igualmente (ineficiente)

---

## Critérios de Priorização

| Critério | Peso | Descrição |
|----------|------|-----------|
| Histórico positivo | 40% | Já fechou plantão conosco |
| Taxa de resposta | 25% | Responde mensagens (não ignora) |
| Recência | 15% | Interação recente = mais engajado |
| Compatibilidade | 15% | Match com a vaga específica |
| Novos | 5% | Nunca contatado (descoberta) |

---

## Tarefas

### T1: Criar serviço de scoring (60min)

**Arquivo:** `app/services/priorizacao/scoring.py`

```python
"""
Serviço de scoring para priorização de médicos.

Sprint 32 E07 - Algoritmo de priorização.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class ScoreMedico:
    """Score calculado para um médico."""
    cliente_id: str
    score_total: float
    score_historico: float
    score_resposta: float
    score_recencia: float
    score_compatibilidade: float
    score_novo: float
    detalhes: dict


# Pesos dos critérios (soma = 100)
PESO_HISTORICO = 40
PESO_RESPOSTA = 25
PESO_RECENCIA = 15
PESO_COMPATIBILIDADE = 15
PESO_NOVO = 5


async def calcular_score_historico(cliente_id: str) -> tuple[float, dict]:
    """
    Calcula score baseado em histórico de plantões.

    - Fechou plantão conosco = 100 pontos
    - Nunca fechou = 0 pontos
    - Bônus por quantidade de plantões

    Returns:
        (score 0-100, detalhes)
    """
    try:
        # Contar plantões realizados
        response = (
            supabase.table("plantoes_realizados")
            .select("id", count="exact")
            .eq("cliente_id", cliente_id)
            .eq("status", "realizado")
            .execute()
        )

        total_plantoes = response.count or 0

        if total_plantoes == 0:
            return 0, {"plantoes_realizados": 0}

        # Score: 60 pontos base + 10 por plantão (máx 100)
        score = min(60 + (total_plantoes * 10), 100)

        return score, {"plantoes_realizados": total_plantoes}

    except Exception as e:
        logger.warning(f"Erro ao calcular score histórico: {e}")
        return 0, {"erro": str(e)}


async def calcular_score_resposta(cliente_id: str) -> tuple[float, dict]:
    """
    Calcula score baseado em taxa de resposta.

    - Médico que sempre responde = 100
    - Médico que ignora = 0

    Returns:
        (score 0-100, detalhes)
    """
    try:
        # Buscar interações dos últimos 90 dias
        desde = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()

        # Mensagens enviadas para o médico
        enviadas = (
            supabase.table("interacoes")
            .select("id", count="exact")
            .eq("cliente_id", cliente_id)
            .eq("tipo", "saida")
            .gte("created_at", desde)
            .execute()
        )

        total_enviadas = enviadas.count or 0

        if total_enviadas == 0:
            # Nunca enviamos = considera neutro (50)
            return 50, {"msgs_enviadas": 0, "msgs_recebidas": 0, "taxa_resposta": None}

        # Respostas do médico
        recebidas = (
            supabase.table("interacoes")
            .select("id", count="exact")
            .eq("cliente_id", cliente_id)
            .eq("tipo", "entrada")
            .gte("created_at", desde)
            .execute()
        )

        total_recebidas = recebidas.count or 0

        # Taxa de resposta (respostas / enviadas)
        taxa = total_recebidas / total_enviadas if total_enviadas > 0 else 0

        # Score: taxa * 100
        score = min(taxa * 100, 100)

        return score, {
            "msgs_enviadas": total_enviadas,
            "msgs_recebidas": total_recebidas,
            "taxa_resposta": round(taxa, 2),
        }

    except Exception as e:
        logger.warning(f"Erro ao calcular score resposta: {e}")
        return 50, {"erro": str(e)}


async def calcular_score_recencia(cliente_id: str) -> tuple[float, dict]:
    """
    Calcula score baseado em recência da última interação.

    - Interação hoje = 100
    - Interação há 30 dias = 50
    - Interação há 90+ dias = 0

    Returns:
        (score 0-100, detalhes)
    """
    try:
        # Buscar última interação
        response = (
            supabase.table("interacoes")
            .select("created_at")
            .eq("cliente_id", cliente_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            # Nunca interagiu = score baixo
            return 10, {"ultima_interacao": None, "dias_desde": None}

        ultima = datetime.fromisoformat(
            response.data[0]["created_at"].replace("Z", "+00:00")
        )
        dias_desde = (datetime.now(timezone.utc) - ultima).days

        # Score decai linearmente: 100 (hoje) → 0 (90 dias)
        score = max(100 - (dias_desde * 100 / 90), 0)

        return score, {
            "ultima_interacao": ultima.isoformat(),
            "dias_desde": dias_desde,
        }

    except Exception as e:
        logger.warning(f"Erro ao calcular score recência: {e}")
        return 10, {"erro": str(e)}


async def calcular_score_compatibilidade(
    cliente_id: str,
    vaga: dict
) -> tuple[float, dict]:
    """
    Calcula score de compatibilidade com a vaga específica.

    - Mesma especialidade = +50
    - Mesma região = +30
    - Mesmo turno preferido = +20

    Returns:
        (score 0-100, detalhes)
    """
    try:
        # Buscar dados do médico
        medico = (
            supabase.table("clientes")
            .select("especialidade, regiao, turno_preferido")
            .eq("id", cliente_id)
            .single()
            .execute()
        )

        if not medico.data:
            return 0, {"erro": "médico não encontrado"}

        med = medico.data
        score = 0
        matches = []

        # Especialidade (obrigatório para match)
        if med.get("especialidade") == vaga.get("especialidade"):
            score += 50
            matches.append("especialidade")
        else:
            # Especialidade diferente = score zero
            return 0, {"matches": [], "especialidade_diferente": True}

        # Região
        hospital_info = vaga.get("hospitais", {})
        if med.get("regiao") and med.get("regiao") == hospital_info.get("regiao"):
            score += 30
            matches.append("regiao")

        # Turno preferido
        if med.get("turno_preferido") and med.get("turno_preferido") == vaga.get("turno"):
            score += 20
            matches.append("turno")

        return score, {"matches": matches}

    except Exception as e:
        logger.warning(f"Erro ao calcular compatibilidade: {e}")
        return 0, {"erro": str(e)}


async def calcular_score_novo(cliente_id: str) -> tuple[float, dict]:
    """
    Calcula bônus para médicos nunca contatados.

    - Nunca recebeu mensagem = 100 (máximo bônus)
    - Já recebeu = 0

    Returns:
        (score 0-100, detalhes)
    """
    try:
        response = (
            supabase.table("interacoes")
            .select("id", count="exact")
            .eq("cliente_id", cliente_id)
            .eq("tipo", "saida")
            .execute()
        )

        total = response.count or 0

        if total == 0:
            return 100, {"nunca_contatado": True}

        return 0, {"nunca_contatado": False, "msgs_enviadas": total}

    except Exception as e:
        logger.warning(f"Erro ao calcular score novo: {e}")
        return 0, {"erro": str(e)}


async def calcular_score_total(
    cliente_id: str,
    vaga: Optional[dict] = None
) -> ScoreMedico:
    """
    Calcula score total do médico.

    Args:
        cliente_id: ID do médico
        vaga: Dados da vaga (opcional, para compatibilidade)

    Returns:
        ScoreMedico com todos os scores
    """
    # Calcular cada componente
    score_hist, det_hist = await calcular_score_historico(cliente_id)
    score_resp, det_resp = await calcular_score_resposta(cliente_id)
    score_rec, det_rec = await calcular_score_recencia(cliente_id)
    score_novo, det_novo = await calcular_score_novo(cliente_id)

    # Compatibilidade só se vaga fornecida
    if vaga:
        score_compat, det_compat = await calcular_score_compatibilidade(cliente_id, vaga)
    else:
        score_compat, det_compat = 50, {"sem_vaga": True}

    # Calcular total ponderado
    total = (
        (score_hist * PESO_HISTORICO / 100) +
        (score_resp * PESO_RESPOSTA / 100) +
        (score_rec * PESO_RECENCIA / 100) +
        (score_compat * PESO_COMPATIBILIDADE / 100) +
        (score_novo * PESO_NOVO / 100)
    )

    return ScoreMedico(
        cliente_id=cliente_id,
        score_total=round(total, 2),
        score_historico=round(score_hist, 2),
        score_resposta=round(score_resp, 2),
        score_recencia=round(score_rec, 2),
        score_compatibilidade=round(score_compat, 2),
        score_novo=round(score_novo, 2),
        detalhes={
            "historico": det_hist,
            "resposta": det_resp,
            "recencia": det_rec,
            "compatibilidade": det_compat,
            "novo": det_novo,
        },
    )
```

### T2: Criar função de ordenação (30min)

**Arquivo:** `app/services/priorizacao/ordenacao.py`

```python
"""
Funções de ordenação de médicos por prioridade.

Sprint 32 E07.
"""
import logging
from typing import Optional
import asyncio

from app.services.priorizacao.scoring import calcular_score_total, ScoreMedico

logger = logging.getLogger(__name__)


async def ordenar_medicos_por_prioridade(
    medicos: list[dict],
    vaga: Optional[dict] = None,
    limit: Optional[int] = None
) -> list[dict]:
    """
    Ordena lista de médicos por score de prioridade.

    Args:
        medicos: Lista de dicts com dados dos médicos
        vaga: Dados da vaga para calcular compatibilidade
        limit: Limite de resultados (None = todos)

    Returns:
        Lista ordenada por score (maior primeiro)
    """
    if not medicos:
        return []

    # Calcular scores em paralelo
    tasks = [
        calcular_score_total(m["id"], vaga)
        for m in medicos
    ]

    scores: list[ScoreMedico] = await asyncio.gather(*tasks)

    # Criar mapa id -> score
    score_map = {s.cliente_id: s for s in scores}

    # Ordenar médicos por score total
    medicos_ordenados = sorted(
        medicos,
        key=lambda m: score_map.get(m["id"], ScoreMedico(
            cliente_id=m["id"],
            score_total=0,
            score_historico=0,
            score_resposta=0,
            score_recencia=0,
            score_compatibilidade=0,
            score_novo=0,
            detalhes={}
        )).score_total,
        reverse=True
    )

    # Adicionar score aos dados do médico
    for med in medicos_ordenados:
        score = score_map.get(med["id"])
        if score:
            med["_score"] = {
                "total": score.score_total,
                "historico": score.score_historico,
                "resposta": score.score_resposta,
                "recencia": score.score_recencia,
                "compatibilidade": score.score_compatibilidade,
                "novo": score.score_novo,
            }

    if limit:
        return medicos_ordenados[:limit]

    return medicos_ordenados


async def selecionar_top_medicos(
    vaga: dict,
    quantidade: int = 5
) -> list[dict]:
    """
    Seleciona os top N médicos para uma vaga específica.

    Fluxo completo:
    1. Busca médicos compatíveis (especialidade, região)
    2. Calcula score de cada um
    3. Retorna os top N

    Args:
        vaga: Dados da vaga
        quantidade: Quantidade de médicos a selecionar

    Returns:
        Lista dos top médicos com scores
    """
    from app.services.gatilhos.oferta import buscar_medicos_compativeis

    # Buscar médicos compatíveis
    medicos = await buscar_medicos_compativeis(vaga, limit=quantidade * 3)

    if not medicos:
        return []

    # Ordenar por prioridade
    ordenados = await ordenar_medicos_por_prioridade(medicos, vaga, limit=quantidade)

    logger.info(
        f"Top {len(ordenados)} médicos para vaga: "
        f"{[m.get('nome', m['id'][:8]) for m in ordenados]}"
    )

    return ordenados
```

### T3: Atualizar busca de médicos no gatilho de oferta (30min)

**Arquivo:** `app/services/gatilhos/oferta.py`

**Modificar `buscar_medicos_compativeis()`:**

```python
from app.services.priorizacao.ordenacao import ordenar_medicos_por_prioridade

async def buscar_medicos_compativeis(
    vaga: dict,
    limit: int = 10
) -> list[dict]:
    """
    Busca médicos compatíveis com a vaga, ordenados por prioridade.

    ATUALIZADO Sprint 32 E07: Agora usa algoritmo de priorização.
    """
    # ... código existente de busca ...

    query = (
        supabase.table("clientes")
        .select("id, nome, telefone, especialidade, regiao, turno_preferido")
        .eq("status_telefone", "validado")
        .eq("opt_out", False)
    )

    # Filtros...
    if vaga.get("especialidade"):
        query = query.eq("especialidade", vaga["especialidade"])

    # Busca mais que o necessário para depois ordenar
    response = query.limit(limit * 5).execute()

    medicos = response.data or []

    if not medicos:
        return []

    # Filtrar quem já recebeu oferta
    # ... código existente ...

    medicos_filtrados = [m for m in medicos if m["id"] not in ids_com_oferta]

    # NOVO: Ordenar por prioridade
    medicos_ordenados = await ordenar_medicos_por_prioridade(
        medicos_filtrados,
        vaga=vaga,
        limit=limit
    )

    return medicos_ordenados
```

### T4: Criar job de atualização de scores (45min)

**Arquivo:** `app/workers/score_worker.py`

```python
"""
Worker para atualização periódica de scores.

Sprint 32 E07 - Mantém score_engajamento atualizado.
"""
import logging
from app.services.supabase import supabase
from app.services.priorizacao.scoring import (
    calcular_score_resposta,
    calcular_score_recencia,
)

logger = logging.getLogger(__name__)


async def atualizar_scores_engajamento(limit: int = 500) -> dict:
    """
    Atualiza score_engajamento dos médicos.

    Score de engajamento = média de:
    - Score de resposta (taxa de resposta)
    - Score de recência (interação recente)

    Roda diariamente para manter scores atualizados.
    """
    stats = {"atualizados": 0, "erros": 0}

    # Buscar médicos ativos (com telefone validado)
    response = (
        supabase.table("clientes")
        .select("id")
        .eq("status_telefone", "validado")
        .eq("opt_out", False)
        .limit(limit)
        .execute()
    )

    medicos = response.data or []

    for medico in medicos:
        try:
            score_resp, _ = await calcular_score_resposta(medico["id"])
            score_rec, _ = await calcular_score_recencia(medico["id"])

            # Média ponderada (resposta mais importante)
            score_engajamento = (score_resp * 0.6) + (score_rec * 0.4)

            # Atualizar no banco
            supabase.table("clientes").update({
                "score_engajamento": round(score_engajamento, 2)
            }).eq("id", medico["id"]).execute()

            stats["atualizados"] += 1

        except Exception as e:
            logger.warning(f"Erro ao atualizar score de {medico['id']}: {e}")
            stats["erros"] += 1

    logger.info(f"Scores atualizados: {stats['atualizados']}, erros: {stats['erros']}")

    return stats


# Adicionar ao scheduler:
# {
#     "name": "atualizar_scores",
#     "function": atualizar_scores_engajamento,
#     "cron": "0 3 * * *",  # 3h da manhã, diariamente
#     "description": "Atualiza scores de engajamento dos médicos",
# }
```

### T5: Criar testes (45min)

**Arquivo:** `tests/unit/test_priorizacao.py`

```python
import pytest
from unittest.mock import patch, AsyncMock
from app.services.priorizacao.scoring import (
    calcular_score_historico,
    calcular_score_resposta,
    calcular_score_recencia,
    calcular_score_total,
)
from app.services.priorizacao.ordenacao import ordenar_medicos_por_prioridade


class TestScoring:
    """Testes para cálculo de scores."""

    @pytest.mark.asyncio
    async def test_score_historico_com_plantoes(self):
        """Médico com plantões deve ter score alto."""
        with patch("app.services.priorizacao.scoring.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.count = 5

            score, detalhes = await calcular_score_historico("med-1")

            assert score >= 60  # Base
            assert detalhes["plantoes_realizados"] == 5

    @pytest.mark.asyncio
    async def test_score_historico_sem_plantoes(self):
        """Médico sem plantões deve ter score zero."""
        with patch("app.services.priorizacao.scoring.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.count = 0

            score, _ = await calcular_score_historico("med-1")

            assert score == 0

    @pytest.mark.asyncio
    async def test_score_resposta_alta_taxa(self):
        """Médico que sempre responde deve ter score alto."""
        with patch("app.services.priorizacao.scoring.supabase") as mock_supabase:
            # Configurar mocks para enviadas e recebidas
            mock_enviadas = AsyncMock()
            mock_enviadas.count = 10

            mock_recebidas = AsyncMock()
            mock_recebidas.count = 8  # 80% taxa

            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.side_effect = [
                mock_enviadas,
                mock_recebidas,
            ]

            score, detalhes = await calcular_score_resposta("med-1")

            assert score >= 70
            assert detalhes["taxa_resposta"] == 0.8


class TestOrdenacao:
    """Testes para ordenação de médicos."""

    @pytest.mark.asyncio
    async def test_ordena_por_score_decrescente(self):
        """Deve ordenar médicos do maior para menor score."""
        medicos = [
            {"id": "med-1", "nome": "João"},
            {"id": "med-2", "nome": "Maria"},
            {"id": "med-3", "nome": "Pedro"},
        ]

        with patch("app.services.priorizacao.ordenacao.calcular_score_total") as mock_calc:
            # Maria tem maior score
            mock_calc.side_effect = [
                AsyncMock(cliente_id="med-1", score_total=50, score_historico=50, score_resposta=50, score_recencia=50, score_compatibilidade=50, score_novo=0, detalhes={}),
                AsyncMock(cliente_id="med-2", score_total=80, score_historico=80, score_resposta=80, score_recencia=80, score_compatibilidade=80, score_novo=0, detalhes={}),
                AsyncMock(cliente_id="med-3", score_total=30, score_historico=30, score_resposta=30, score_recencia=30, score_compatibilidade=30, score_novo=0, detalhes={}),
            ]

            ordenados = await ordenar_medicos_por_prioridade(medicos)

            # Maria deve vir primeiro
            assert ordenados[0]["nome"] == "Maria"
            assert ordenados[1]["nome"] == "João"
            assert ordenados[2]["nome"] == "Pedro"
```

---

## Definition of Done (DoD)

### Critérios Obrigatórios

- [ ] **Funções de scoring implementadas**
  - [ ] `calcular_score_historico()` funciona
  - [ ] `calcular_score_resposta()` funciona
  - [ ] `calcular_score_recencia()` funciona
  - [ ] `calcular_score_compatibilidade()` funciona
  - [ ] `calcular_score_novo()` funciona
  - [ ] `calcular_score_total()` combina todos

- [ ] **Ordenação funciona**
  - [ ] `ordenar_medicos_por_prioridade()` ordena corretamente
  - [ ] `selecionar_top_medicos()` retorna top N

- [ ] **Integração com gatilho de oferta**
  - [ ] `buscar_medicos_compativeis()` usa ordenação
  - [ ] Médicos com maior score recebem oferta primeiro

- [ ] **Job de atualização**
  - [ ] `atualizar_scores_engajamento()` roda diariamente
  - [ ] Coluna `score_engajamento` atualizada

- [ ] **Testes passando**
  - [ ] `uv run pytest tests/unit/test_priorizacao.py -v` = OK

### Verificação Manual

```python
# Testar score de um médico
from app.services.priorizacao.scoring import calcular_score_total

score = await calcular_score_total("uuid-do-medico")
print(f"Score total: {score.score_total}")
print(f"Detalhes: {score.detalhes}")

# Testar ordenação
from app.services.priorizacao.ordenacao import selecionar_top_medicos

vaga = {"id": "...", "especialidade": "cardiologia", "hospitais": {"regiao": "sp"}}
top = await selecionar_top_medicos(vaga, quantidade=5)
for m in top:
    print(f"{m['nome']}: {m['_score']['total']}")
```

---

## Notas para o Desenvolvedor

1. **Performance:**
   - Calcular scores em paralelo (asyncio.gather)
   - Usar `score_engajamento` pré-calculado quando possível
   - Job noturno atualiza scores para evitar cálculo real-time

2. **Pesos ajustáveis:**
   - Pesos podem ser configurados por campanha no futuro
   - Default favorece médicos com histórico positivo

3. **Médicos novos:**
   - 5% de peso para "nunca contatado"
   - Garante que novos médicos também recebam ofertas

4. **Compatibilidade crítica:**
   - Se especialidade diferente = score compatibilidade = 0
   - Evita ofertar vaga errada
