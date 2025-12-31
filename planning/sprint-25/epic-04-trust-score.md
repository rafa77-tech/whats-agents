# Epic 04: Trust Score Engine

## Objetivo

Implementar sistema **Trust Score multiparametrico** que substitui o Health Score binario:
- Score continuo 0-100
- Niveis com permissoes dinamicas
- Calculo baseado em multiplos fatores
- Atualizacao em tempo real

## Contexto

**Mudanca de Paradigma:**

| Health Score (antes) | Trust Score (agora) |
|---------------------|---------------------|
| Score simples 0-100 | Score com niveis e permissoes |
| Threshold fixo (85) | Thresholds por nivel |
| Triggers binarios | Permissoes dinamicas |
| Calculo esporadico | Calculo continuo |

### Niveis de Trust Score

| Nivel | Score | Permissoes |
|-------|-------|------------|
| Verde | 80-100 | Prospeccao + Follow-up + Respostas (full) |
| Amarelo | 60-79 | Prospeccao reduzida + Follow-up + Respostas |
| Laranja | 40-59 | Sem prospeccao + Follow-up + Respostas |
| Vermelho | 20-39 | Apenas respostas |
| Critico | 0-19 | Pausa total |

---

## Story 4.1: Data Classes

### Objetivo
Criar estruturas de dados para Trust Score.

### Implementacao

**Arquivo:** `app/services/trust_score/models.py`

```python
"""
Trust Score Models.

Estruturas de dados para calculo e armazenamento.
"""
from dataclasses import dataclass, field, asdict
from typing import Literal
from enum import Enum


class TrustLevel(str, Enum):
    """Niveis de Trust Score."""
    VERDE = "verde"
    AMARELO = "amarelo"
    LARANJA = "laranja"
    VERMELHO = "vermelho"
    CRITICO = "critico"


@dataclass
class TrustFactors:
    """
    Fatores que compoem o Trust Score.

    Cada fator tem peso diferente no calculo final.
    """
    # ══════════════════════════════════════════
    # FATORES DE TEMPO
    # ══════════════════════════════════════════
    idade_dias: int = 0              # Dias desde criacao
    dias_sem_erro: int = 0           # Dias consecutivos sem erro
    dias_em_operacao: int = 0        # Dias em status active/warming

    # ══════════════════════════════════════════
    # FATORES DE VOLUME
    # ══════════════════════════════════════════
    msgs_enviadas_total: int = 0
    msgs_recebidas_total: int = 0
    msgs_enviadas_24h: int = 0
    msgs_recebidas_24h: int = 0

    # ══════════════════════════════════════════
    # FATORES DE QUALIDADE
    # ══════════════════════════════════════════
    taxa_resposta: float = 0.0       # % de msgs que obtiveram resposta
    taxa_delivery: float = 1.0       # % de msgs entregues
    taxa_block: float = 0.0          # % de usuarios que bloquearam

    # ══════════════════════════════════════════
    # FATORES DE ENGAJAMENTO
    # ══════════════════════════════════════════
    conversas_bidirecionais: int = 0 # Conversas com ida e volta
    grupos_count: int = 0            # Grupos onde participa
    tipos_midia_usados: int = 0      # Variedade de midia (text, audio, image, etc)

    # ══════════════════════════════════════════
    # FATORES DE PROBLEMAS
    # ══════════════════════════════════════════
    erros_24h: int = 0               # Erros nas ultimas 24h
    warnings_7d: int = 0             # Warnings nos ultimos 7 dias
    spam_errors_7d: int = 0          # Erros de spam nos ultimos 7 dias

    def to_dict(self) -> dict:
        """Converte para dicionario."""
        return asdict(self)

    @property
    def msgs_ratio(self) -> float:
        """Proporcao enviadas/recebidas (ideal ~1.0)."""
        if self.msgs_recebidas_total == 0:
            return float(self.msgs_enviadas_total) if self.msgs_enviadas_total > 0 else 0.0
        return self.msgs_enviadas_total / self.msgs_recebidas_total


@dataclass
class TrustPermissions:
    """
    Permissoes derivadas do Trust Score.

    Definem o que o chip pode fazer.
    """
    pode_prospectar: bool = False
    pode_followup: bool = False
    pode_responder: bool = True

    limite_hora: int = 5
    limite_dia: int = 30

    delay_minimo_segundos: int = 120  # 2 min

    def to_dict(self) -> dict:
        """Converte para dicionario."""
        return asdict(self)


@dataclass
class TrustResult:
    """Resultado completo do calculo de Trust Score."""
    score: int
    level: TrustLevel
    factors: TrustFactors
    permissions: TrustPermissions
    breakdown: dict = field(default_factory=dict)  # Detalhamento do calculo

    def to_dict(self) -> dict:
        """Converte para dicionario."""
        return {
            "score": self.score,
            "level": self.level.value,
            "factors": self.factors.to_dict(),
            "permissions": self.permissions.to_dict(),
            "breakdown": self.breakdown,
        }
```

### DoD

- [ ] TrustLevel enum criado
- [ ] TrustFactors dataclass
- [ ] TrustPermissions dataclass
- [ ] TrustResult dataclass

---

## Story 4.2: Coleta de Fatores

### Objetivo
Coletar todos os fatores do banco para calculo.

### Implementacao

**Arquivo:** `app/services/trust_score/collector.py`

```python
"""
Trust Score Collector.

Coleta fatores do banco de dados para calculo.
"""
import logging
from datetime import datetime, timedelta, timezone

from app.services.supabase import supabase
from app.services.trust_score.models import TrustFactors

logger = logging.getLogger(__name__)


async def coletar_fatores(chip_id: str) -> TrustFactors:
    """
    Coleta todos os fatores do banco para calculo do Trust Score.

    Args:
        chip_id: UUID do chip

    Returns:
        TrustFactors preenchido
    """
    # Buscar chip
    result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

    if not result.data:
        logger.warning(f"[TrustCollector] Chip nao encontrado: {chip_id}")
        return TrustFactors()

    chip = result.data
    now = datetime.now(timezone.utc)

    # ══════════════════════════════════════════
    # FATORES DE TEMPO
    # ══════════════════════════════════════════

    # Idade em dias
    created = datetime.fromisoformat(chip["created_at"].replace("Z", "+00:00"))
    idade_dias = (now - created).days

    # Dias sem erro
    dias_sem_erro = chip.get("dias_sem_erro", 0)

    # Dias em operacao (warming ou active)
    warming_started = chip.get("warming_started_at")
    if warming_started:
        ws = datetime.fromisoformat(warming_started.replace("Z", "+00:00"))
        dias_em_operacao = (now - ws).days
    else:
        dias_em_operacao = 0

    # ══════════════════════════════════════════
    # FATORES DE VOLUME (do chip)
    # ══════════════════════════════════════════

    msgs_enviadas_total = chip.get("msgs_enviadas_total", 0)
    msgs_recebidas_total = chip.get("msgs_recebidas_total", 0)
    msgs_enviadas_24h = chip.get("msgs_enviadas_hoje", 0)
    msgs_recebidas_24h = chip.get("msgs_recebidas_hoje", 0)

    # ══════════════════════════════════════════
    # FATORES DE QUALIDADE (do chip)
    # ══════════════════════════════════════════

    taxa_resposta = float(chip.get("taxa_resposta", 0))
    taxa_delivery = float(chip.get("taxa_delivery", 1))
    taxa_block = float(chip.get("taxa_block", 0))

    # ══════════════════════════════════════════
    # FATORES DE ENGAJAMENTO
    # ══════════════════════════════════════════

    # Conversas bidirecionais (ultimos 7 dias)
    sete_dias_atras = (now - timedelta(days=7)).isoformat()
    conv_result = supabase.table("chip_interactions").select(
        "*", count="exact"
    ).eq(
        "chip_id", chip_id
    ).eq(
        "tipo", "msg_enviada"
    ).eq(
        "obteve_resposta", True
    ).gte(
        "created_at", sete_dias_atras
    ).execute()

    conversas_bidirecionais = conv_result.count or 0

    grupos_count = chip.get("grupos_count", 0)
    tipos_midia = len(chip.get("tipos_midia_usados", []))

    # ══════════════════════════════════════════
    # FATORES DE PROBLEMAS
    # ══════════════════════════════════════════

    erros_24h = chip.get("erros_ultimas_24h", 0)

    # Warnings nos ultimos 7 dias
    warnings_result = supabase.table("chip_alerts").select(
        "*", count="exact"
    ).eq(
        "chip_id", chip_id
    ).eq(
        "severity", "warning"
    ).gte(
        "created_at", sete_dias_atras
    ).execute()

    warnings_7d = warnings_result.count or 0

    # Erros de spam nos ultimos 7 dias
    spam_result = supabase.table("chip_alerts").select(
        "*", count="exact"
    ).eq(
        "chip_id", chip_id
    ).eq(
        "tipo", "spam_detected"
    ).gte(
        "created_at", sete_dias_atras
    ).execute()

    spam_errors_7d = spam_result.count or 0

    return TrustFactors(
        idade_dias=idade_dias,
        dias_sem_erro=dias_sem_erro,
        dias_em_operacao=dias_em_operacao,
        msgs_enviadas_total=msgs_enviadas_total,
        msgs_recebidas_total=msgs_recebidas_total,
        msgs_enviadas_24h=msgs_enviadas_24h,
        msgs_recebidas_24h=msgs_recebidas_24h,
        taxa_resposta=taxa_resposta,
        taxa_delivery=taxa_delivery,
        taxa_block=taxa_block,
        conversas_bidirecionais=conversas_bidirecionais,
        grupos_count=grupos_count,
        tipos_midia_usados=tipos_midia,
        erros_24h=erros_24h,
        warnings_7d=warnings_7d,
        spam_errors_7d=spam_errors_7d,
    )
```

### DoD

- [ ] Coleta de tempo funcionando
- [ ] Coleta de volume funcionando
- [ ] Coleta de qualidade funcionando
- [ ] Coleta de problemas funcionando

---

## Story 4.3: Calculo do Score

### Objetivo
Implementar algoritmo de calculo multiparametrico.

### Implementacao

**Arquivo:** `app/services/trust_score/calculator.py`

```python
"""
Trust Score Calculator.

Algoritmo multiparametrico para calculo do Trust Score.
"""
import logging
from typing import Tuple

from app.services.trust_score.models import (
    TrustFactors, TrustLevel, TrustPermissions, TrustResult
)
from app.services.trust_score.collector import coletar_fatores

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# PESOS DOS FATORES
# ══════════════════════════════════════════════════════════════════

WEIGHTS = {
    # Positivos (max total ~70 pontos)
    "idade_dias": {"per": 2, "max": 14},           # +2/dia, max +14
    "msgs_enviadas": {"per": 10, "max": 10},       # +1/10msgs, max +10
    "msgs_recebidas": {"per": 10, "max": 10},      # +1/10msgs, max +10
    "conversas_bidi": {"per": 1, "max": 12},       # +3/conv, max +12
    "grupos": {"per": 1, "max": 9},                # +3/grupo, max +9
    "tipos_midia": {"per": 1, "max": 8},           # +2/tipo, max +8
    "dias_sem_erro": {"per": 1, "max": 7},         # +1/dia, max +7

    # Negativos (podem zerar o score)
    "spam_errors": -20,                            # -20/erro de spam
    "warnings": -8,                                # -8/warning
    "erros_24h": -5,                               # -5/erro
    "taxa_block_alta": -15,                        # Se taxa_block > 2%
    "proporcao_ruim": -10,                         # Se msgs_ratio > 3
    "taxa_resposta_baixa": -10,                    # Se taxa_resposta < 20%
}


# ══════════════════════════════════════════════════════════════════
# THRESHOLDS POR NIVEL
# ══════════════════════════════════════════════════════════════════

LEVEL_THRESHOLDS = {
    TrustLevel.VERDE: 80,
    TrustLevel.AMARELO: 60,
    TrustLevel.LARANJA: 40,
    TrustLevel.VERMELHO: 20,
    TrustLevel.CRITICO: 0,
}


def calcular_score(factors: TrustFactors) -> Tuple[int, dict]:
    """
    Calcula Trust Score baseado nos fatores.

    Args:
        factors: Fatores coletados

    Returns:
        Tupla (score, breakdown)
    """
    breakdown = {}
    score = 40  # Base

    # ══════════════════════════════════════════
    # FATORES POSITIVOS
    # ══════════════════════════════════════════

    # Idade
    bonus_idade = min(factors.idade_dias * 2, WEIGHTS["idade_dias"]["max"])
    score += bonus_idade
    breakdown["idade"] = f"+{bonus_idade} ({factors.idade_dias} dias)"

    # Mensagens enviadas
    bonus_env = min(factors.msgs_enviadas_total // 10, WEIGHTS["msgs_enviadas"]["max"])
    score += bonus_env
    breakdown["msgs_enviadas"] = f"+{bonus_env} ({factors.msgs_enviadas_total} total)"

    # Mensagens recebidas
    bonus_rec = min(factors.msgs_recebidas_total // 10, WEIGHTS["msgs_recebidas"]["max"])
    score += bonus_rec
    breakdown["msgs_recebidas"] = f"+{bonus_rec} ({factors.msgs_recebidas_total} total)"

    # Conversas bidirecionais
    bonus_conv = min(factors.conversas_bidirecionais * 3, WEIGHTS["conversas_bidi"]["max"])
    score += bonus_conv
    breakdown["conversas_bidi"] = f"+{bonus_conv} ({factors.conversas_bidirecionais} convs)"

    # Grupos
    bonus_grupos = min(factors.grupos_count * 3, WEIGHTS["grupos"]["max"])
    score += bonus_grupos
    breakdown["grupos"] = f"+{bonus_grupos} ({factors.grupos_count} grupos)"

    # Tipos de midia
    bonus_midia = min(factors.tipos_midia_usados * 2, WEIGHTS["tipos_midia"]["max"])
    score += bonus_midia
    breakdown["midia"] = f"+{bonus_midia} ({factors.tipos_midia_usados} tipos)"

    # Dias sem erro
    bonus_estabilidade = min(factors.dias_sem_erro, WEIGHTS["dias_sem_erro"]["max"])
    score += bonus_estabilidade
    breakdown["estabilidade"] = f"+{bonus_estabilidade} ({factors.dias_sem_erro} dias sem erro)"

    # Taxa de resposta alta (bonus)
    if factors.taxa_resposta > 0.5:
        score += 5
        breakdown["taxa_resposta_bonus"] = f"+5 (taxa {factors.taxa_resposta:.1%})"

    # ══════════════════════════════════════════
    # FATORES NEGATIVOS
    # ══════════════════════════════════════════

    # Erros de spam (CRITICO)
    if factors.spam_errors_7d > 0:
        penalidade = factors.spam_errors_7d * abs(WEIGHTS["spam_errors"])
        score -= penalidade
        breakdown["spam_errors"] = f"-{penalidade} ({factors.spam_errors_7d} erros)"

    # Warnings
    if factors.warnings_7d > 0:
        penalidade = factors.warnings_7d * abs(WEIGHTS["warnings"])
        score -= penalidade
        breakdown["warnings"] = f"-{penalidade} ({factors.warnings_7d} warnings)"

    # Erros nas 24h
    if factors.erros_24h > 0:
        penalidade = factors.erros_24h * abs(WEIGHTS["erros_24h"])
        score -= penalidade
        breakdown["erros_24h"] = f"-{penalidade} ({factors.erros_24h} erros)"

    # Taxa de bloqueio alta
    if factors.taxa_block > 0.02:  # > 2%
        score -= abs(WEIGHTS["taxa_block_alta"])
        breakdown["taxa_block"] = f"-{abs(WEIGHTS['taxa_block_alta'])} (taxa {factors.taxa_block:.1%})"

    # Proporcao enviadas/recebidas ruim
    if factors.msgs_ratio > 3:
        score -= abs(WEIGHTS["proporcao_ruim"])
        breakdown["proporcao"] = f"-{abs(WEIGHTS['proporcao_ruim'])} (ratio {factors.msgs_ratio:.1f})"

    # Taxa de resposta baixa
    if factors.taxa_resposta < 0.2 and factors.msgs_enviadas_total > 10:
        score -= abs(WEIGHTS["taxa_resposta_baixa"])
        breakdown["taxa_resposta_baixa"] = f"-{abs(WEIGHTS['taxa_resposta_baixa'])} (taxa {factors.taxa_resposta:.1%})"

    # Garantir range 0-100
    score = max(0, min(100, score))

    return score, breakdown


def determinar_nivel(score: int) -> TrustLevel:
    """
    Determina nivel baseado no score.

    Args:
        score: Trust Score (0-100)

    Returns:
        TrustLevel correspondente
    """
    if score >= LEVEL_THRESHOLDS[TrustLevel.VERDE]:
        return TrustLevel.VERDE
    elif score >= LEVEL_THRESHOLDS[TrustLevel.AMARELO]:
        return TrustLevel.AMARELO
    elif score >= LEVEL_THRESHOLDS[TrustLevel.LARANJA]:
        return TrustLevel.LARANJA
    elif score >= LEVEL_THRESHOLDS[TrustLevel.VERMELHO]:
        return TrustLevel.VERMELHO
    else:
        return TrustLevel.CRITICO


def calcular_permissoes(level: TrustLevel) -> TrustPermissions:
    """
    Calcula permissoes baseado no nivel.

    Args:
        level: Nivel do Trust Score

    Returns:
        TrustPermissions correspondentes
    """
    if level == TrustLevel.VERDE:
        return TrustPermissions(
            pode_prospectar=True,
            pode_followup=True,
            pode_responder=True,
            limite_hora=20,
            limite_dia=100,
            delay_minimo_segundos=45,
        )
    elif level == TrustLevel.AMARELO:
        return TrustPermissions(
            pode_prospectar=True,  # Mas com limite reduzido
            pode_followup=True,
            pode_responder=True,
            limite_hora=10,
            limite_dia=50,
            delay_minimo_segundos=60,
        )
    elif level == TrustLevel.LARANJA:
        return TrustPermissions(
            pode_prospectar=False,
            pode_followup=True,
            pode_responder=True,
            limite_hora=5,
            limite_dia=30,
            delay_minimo_segundos=90,
        )
    elif level == TrustLevel.VERMELHO:
        return TrustPermissions(
            pode_prospectar=False,
            pode_followup=False,
            pode_responder=True,
            limite_hora=3,
            limite_dia=15,
            delay_minimo_segundos=120,
        )
    else:  # CRITICO
        return TrustPermissions(
            pode_prospectar=False,
            pode_followup=False,
            pode_responder=False,  # Pausa total
            limite_hora=0,
            limite_dia=0,
            delay_minimo_segundos=300,
        )


async def calcular_trust_score(chip_id: str) -> TrustResult:
    """
    Calcula Trust Score completo para um chip.

    Args:
        chip_id: UUID do chip

    Returns:
        TrustResult com score, level, factors, permissions
    """
    # 1. Coletar fatores
    factors = await coletar_fatores(chip_id)

    # 2. Calcular score
    score, breakdown = calcular_score(factors)

    # 3. Determinar nivel
    level = determinar_nivel(score)

    # 4. Calcular permissoes
    permissions = calcular_permissoes(level)

    logger.debug(
        f"[TrustCalculator] Chip {chip_id[:8]}: "
        f"score={score}, level={level.value}"
    )

    return TrustResult(
        score=score,
        level=level,
        factors=factors,
        permissions=permissions,
        breakdown=breakdown,
    )
```

### DoD

- [ ] Pesos definidos
- [ ] Thresholds por nivel
- [ ] Calculo de score
- [ ] Calculo de permissoes
- [ ] Breakdown detalhado

---

## Story 4.4: Persistencia e Historico

### Objetivo
Salvar Trust Score e manter historico.

### Implementacao

**Arquivo:** `app/services/trust_score/service.py`

```python
"""
Trust Score Service.

Servico de alto nivel para calculo, persistencia e historico.
"""
import logging
from datetime import datetime, timezone

from app.services.supabase import supabase
from app.services.trust_score.calculator import calcular_trust_score
from app.services.trust_score.models import TrustResult, TrustLevel

logger = logging.getLogger(__name__)


class TrustScoreService:
    """Servico de Trust Score."""

    async def atualizar_trust_score(self, chip_id: str) -> TrustResult:
        """
        Calcula, persiste e retorna Trust Score.

        Args:
            chip_id: UUID do chip

        Returns:
            TrustResult completo
        """
        # 1. Calcular
        result = await calcular_trust_score(chip_id)

        # 2. Atualizar chip
        supabase.table("chips").update({
            "trust_score": result.score,
            "trust_level": result.level.value,
            "trust_factors": result.factors.to_dict(),
            "ultimo_calculo_trust": datetime.now(timezone.utc).isoformat(),
            # Permissoes
            "pode_prospectar": result.permissions.pode_prospectar,
            "pode_followup": result.permissions.pode_followup,
            "pode_responder": result.permissions.pode_responder,
            "limite_hora": result.permissions.limite_hora,
            "limite_dia": result.permissions.limite_dia,
            "delay_minimo_segundos": result.permissions.delay_minimo_segundos,
        }).eq("id", chip_id).execute()

        # 3. Registrar historico
        supabase.table("chip_trust_history").insert({
            "chip_id": chip_id,
            "score": result.score,
            "level": result.level.value,
            "factors": result.factors.to_dict(),
            "permissoes": result.permissions.to_dict(),
        }).execute()

        logger.info(
            f"[TrustScore] Atualizado: chip={chip_id[:8]}, "
            f"score={result.score}, level={result.level.value}"
        )

        return result

    async def obter_trust_score(self, chip_id: str) -> dict:
        """
        Obtem Trust Score atual do chip.

        Args:
            chip_id: UUID do chip

        Returns:
            Dict com score, level, permissoes
        """
        result = supabase.table("chips").select(
            "trust_score, trust_level, trust_factors, "
            "pode_prospectar, pode_followup, pode_responder, "
            "limite_hora, limite_dia, ultimo_calculo_trust"
        ).eq("id", chip_id).single().execute()

        if not result.data:
            return None

        return result.data

    async def obter_historico(
        self,
        chip_id: str,
        dias: int = 7,
        limite: int = 100,
    ) -> list:
        """
        Obtem historico de Trust Score.

        Args:
            chip_id: UUID do chip
            dias: Periodo em dias
            limite: Max registros

        Returns:
            Lista de registros [{score, level, factors, recorded_at}, ...]
        """
        desde = datetime.now(timezone.utc) - timedelta(days=dias)

        result = supabase.table("chip_trust_history").select(
            "score, level, factors, permissoes, recorded_at"
        ).eq(
            "chip_id", chip_id
        ).gte(
            "recorded_at", desde.isoformat()
        ).order(
            "recorded_at", desc=True
        ).limit(limite).execute()

        return result.data or []

    async def analisar_tendencia(self, chip_id: str, dias: int = 3) -> dict:
        """
        Analisa tendencia do Trust Score.

        Args:
            chip_id: UUID do chip
            dias: Periodo para analise

        Returns:
            {
                "tendencia": "subindo" | "estavel" | "caindo",
                "variacao": int,
                "score_atual": int,
                "score_inicio_periodo": int
            }
        """
        historico = await self.obter_historico(chip_id, dias=dias)

        if len(historico) < 2:
            return {
                "tendencia": "estavel",
                "variacao": 0,
                "score_atual": historico[0]["score"] if historico else 0,
                "score_inicio_periodo": historico[0]["score"] if historico else 0,
            }

        score_atual = historico[0]["score"]
        score_antigo = historico[-1]["score"]
        variacao = score_atual - score_antigo

        if variacao > 5:
            tendencia = "subindo"
        elif variacao < -5:
            tendencia = "caindo"
        else:
            tendencia = "estavel"

        return {
            "tendencia": tendencia,
            "variacao": variacao,
            "score_atual": score_atual,
            "score_inicio_periodo": score_antigo,
        }

    async def listar_por_nivel(self, level: TrustLevel) -> list:
        """
        Lista chips por nivel de Trust.

        Args:
            level: Nivel desejado

        Returns:
            Lista de chips
        """
        result = supabase.table("chips").select(
            "id, telefone, instance_name, trust_score, trust_level, status"
        ).eq(
            "trust_level", level.value
        ).order(
            "trust_score", desc=True
        ).execute()

        return result.data or []

    async def listar_criticos(self) -> list:
        """
        Lista chips em nivel critico que precisam atencao.

        Returns:
            Lista de chips criticos
        """
        result = supabase.table("chips").select(
            "id, telefone, instance_name, trust_score, trust_level, status, trust_factors"
        ).in_(
            "trust_level", ["critico", "vermelho"]
        ).in_(
            "status", ["warming", "ready", "active"]
        ).order(
            "trust_score", desc=False
        ).execute()

        return result.data or []


# Singleton
trust_score_service = TrustScoreService()


# Import para usar em outros modulos
from datetime import timedelta
```

### DoD

- [ ] Atualizacao funcionando
- [ ] Historico sendo registrado
- [ ] Analise de tendencia
- [ ] Listagem por nivel

---

## Story 4.5: Job de Atualizacao

### Objetivo
Job para recalcular Trust Scores periodicamente.

### Implementacao

**Arquivo:** `app/workers/trust_score_updater.py`

```python
"""
Job para atualizar Trust Scores.

Roda periodicamente para manter scores atualizados.
"""
import asyncio
import logging

from app.services.supabase import supabase
from app.services.trust_score.service import trust_score_service
from app.services.notificacoes import notificar_slack

logger = logging.getLogger(__name__)


async def atualizar_todos_trust_scores():
    """
    Atualiza Trust Score de todos os chips ativos.

    Roda a cada 15 minutos.
    """
    logger.info("[TrustUpdater] Iniciando atualizacao em massa")

    # Buscar chips que precisam de atualizacao
    result = supabase.table("chips").select("id, telefone").in_(
        "status", ["warming", "ready", "active", "degraded"]
    ).execute()

    chips = result.data or []
    logger.info(f"[TrustUpdater] {len(chips)} chips para atualizar")

    criticos_novos = []

    for chip in chips:
        try:
            result = await trust_score_service.atualizar_trust_score(chip["id"])

            # Detectar novos criticos
            if result.level.value == "critico":
                criticos_novos.append({
                    "telefone": chip["telefone"],
                    "score": result.score,
                })

        except Exception as e:
            logger.error(f"[TrustUpdater] Erro ao atualizar {chip['id']}: {e}")

        # Pequeno delay para nao sobrecarregar
        await asyncio.sleep(0.1)

    # Notificar sobre criticos
    if criticos_novos:
        msg = ":rotating_light: *Chips em nivel CRITICO*\n"
        for c in criticos_novos:
            msg += f"- `{c['telefone']}` (score: {c['score']})\n"

        await notificar_slack(msg, canal="alertas")

    logger.info(f"[TrustUpdater] Atualizacao concluida. {len(criticos_novos)} criticos.")


# Registrar no scheduler
# scheduler.add_job(atualizar_todos_trust_scores, 'interval', minutes=15)
```

### DoD

- [ ] Job funcionando
- [ ] Notificacao de criticos
- [ ] Logging adequado

---

## Checklist do Epico

- [ ] **E04.1** - Data classes criadas
- [ ] **E04.2** - Coleta de fatores
- [ ] **E04.3** - Calculo do score
- [ ] **E04.4** - Persistencia e historico
- [ ] **E04.5** - Job de atualizacao
- [ ] Testes unitarios
- [ ] Integracao com Orchestrator

---

## Diagrama: Composicao do Trust Score

```
┌─────────────────────────────────────────────────────────────────┐
│                      TRUST SCORE (0-100)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BASE: 40 pontos                                                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ FATORES POSITIVOS (max ~70)                                │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ + Idade da conta      │ +2/dia       │ max +14             │ │
│  │ + Msgs enviadas       │ +1/10 msgs   │ max +10             │ │
│  │ + Msgs recebidas      │ +1/10 msgs   │ max +10             │ │
│  │ + Conversas bidi      │ +3/conv      │ max +12             │ │
│  │ + Grupos              │ +3/grupo     │ max +9              │ │
│  │ + Tipos midia         │ +2/tipo      │ max +8              │ │
│  │ + Dias sem erro       │ +1/dia       │ max +7              │ │
│  │ + Taxa resposta >50%  │ +5           │ bonus               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ FATORES NEGATIVOS                                          │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ - Erros spam          │ -20/erro     │ CRITICO             │ │
│  │ - Warnings            │ -8/warning   │                     │ │
│  │ - Erros 24h           │ -5/erro      │                     │ │
│  │ - Taxa block > 2%     │ -15          │                     │ │
│  │ - Proporcao > 3:1     │ -10          │                     │ │
│  │ - Taxa resposta < 20% │ -10          │                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ NIVEIS E PERMISSOES                                        │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ VERDE (80-100)    │ Prospeccao + Followup + Respostas     │ │
│  │                   │ 20/h, 100/dia, delay 45s              │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ AMARELO (60-79)   │ Prospeccao reduzida + Followup + Resp │ │
│  │                   │ 10/h, 50/dia, delay 60s               │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ LARANJA (40-59)   │ Sem prospeccao + Followup + Respostas │ │
│  │                   │ 5/h, 30/dia, delay 90s                │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ VERMELHO (20-39)  │ Apenas respostas                      │ │
│  │                   │ 3/h, 15/dia, delay 120s               │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ CRITICO (0-19)    │ Pausa total                           │ │
│  │                   │ 0/h, 0/dia                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```
