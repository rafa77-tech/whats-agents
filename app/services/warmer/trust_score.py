"""
Trust Score Engine - Calculo multiparametrico de confianca.

O Trust Score substitui triggers binarios por um score continuo 0-100
que determina permissoes dinamicas para cada chip.

Fatores considerados:
- Idade do chip (dias desde criacao)
- Taxa de resposta (mensagens recebidas / enviadas)
- Taxa de delivery (mensagens entregues com sucesso)
- Diversidade de midia (tipos diferentes usados)
- Erros recentes (falhas nas ultimas 24h)
- Conversas bidirecionais (interacoes reais)
- Dias sem incidente (estabilidade)
- Fase de warmup (progressao)
"""
import logging
from enum import Enum
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class TrustLevel(str, Enum):
    """Niveis de confianca do chip."""
    VERDE = "verde"       # 80-100: Excelente, todas permissoes
    AMARELO = "amarelo"   # 60-79: Bom, maioria das permissoes
    LARANJA = "laranja"   # 40-59: Atencao, permissoes reduzidas
    VERMELHO = "vermelho" # 20-39: Alerta, modo restrito
    CRITICO = "critico"   # 0-19: Critico, apenas resposta


@dataclass
class TrustFactors:
    """Fatores que compoem o Trust Score."""
    idade_dias: int = 0
    taxa_resposta: float = 0.0
    taxa_delivery: float = 1.0
    taxa_block: float = 0.0
    diversidade_midia: int = 0
    erros_24h: int = 0
    conversas_bidirecionais: int = 0
    dias_sem_erro: int = 0
    fase_warmup: str = "repouso"
    msgs_enviadas_total: int = 0
    msgs_recebidas_total: int = 0
    grupos_count: int = 0


@dataclass
class Permissoes:
    """Permissoes calculadas do Trust Score."""
    pode_prospectar: bool = False
    pode_followup: bool = False
    pode_responder: bool = True
    limite_hora: int = 5
    limite_dia: int = 30
    delay_minimo_segundos: int = 120


class TrustScoreEngine:
    """Engine de calculo do Trust Score."""

    # Pesos dos fatores (somam 100)
    PESOS = {
        "idade": 15,              # Quanto mais velho, melhor
        "taxa_resposta": 20,      # Respostas indicam engajamento real
        "taxa_delivery": 15,      # Entregas bem-sucedidas
        "taxa_block": -20,        # Bloqueios sao muito negativos
        "diversidade_midia": 10,  # Uso variado e mais natural
        "erros_24h": -10,         # Erros recentes
        "conversas_bi": 15,       # Conversas reais
        "dias_sem_erro": 10,      # Estabilidade
        "fase_bonus": 15,         # Bonus por fase avancada
    }

    # Limites por fase de warmup
    LIMITES_FASE = {
        "repouso": {"hora": 0, "dia": 0},
        "setup": {"hora": 2, "dia": 5},
        "primeiros_contatos": {"hora": 5, "dia": 10},
        "expansao": {"hora": 10, "dia": 30},
        "pre_operacao": {"hora": 15, "dia": 50},
        "teste_graduacao": {"hora": 20, "dia": 70},
        "operacao": {"hora": 30, "dia": 100},
    }

    # Bonus de fase (progressao)
    BONUS_FASE = {
        "repouso": 0,
        "setup": 5,
        "primeiros_contatos": 10,
        "expansao": 20,
        "pre_operacao": 35,
        "teste_graduacao": 45,
        "operacao": 50,
    }

    def calcular_score(self, factors: TrustFactors) -> int:
        """
        Calcula Trust Score baseado nos fatores.

        Returns:
            Score de 0 a 100
        """
        score = 50  # Base inicial

        # Idade (max +15 pontos em 30 dias)
        idade_score = min(factors.idade_dias / 30, 1.0) * self.PESOS["idade"]
        score += idade_score

        # Taxa de resposta (max +20 pontos)
        # 50%+ de resposta e excelente
        resposta_score = min(factors.taxa_resposta / 0.5, 1.0) * self.PESOS["taxa_resposta"]
        score += resposta_score

        # Taxa de delivery (max +15 pontos)
        # 95%+ e excelente
        delivery_score = min(factors.taxa_delivery / 0.95, 1.0) * self.PESOS["taxa_delivery"]
        score += delivery_score

        # Taxa de block (penalidade, max -20 pontos)
        # Qualquer block e ruim
        block_penalty = min(factors.taxa_block * 10, 1.0) * abs(self.PESOS["taxa_block"])
        score -= block_penalty

        # Diversidade de midia (max +10 pontos)
        # 4+ tipos e excelente (text, audio, image, video, sticker)
        midia_score = min(factors.diversidade_midia / 4, 1.0) * self.PESOS["diversidade_midia"]
        score += midia_score

        # Erros nas ultimas 24h (penalidade, max -10 pontos)
        # 5+ erros e muito ruim
        erro_penalty = min(factors.erros_24h / 5, 1.0) * abs(self.PESOS["erros_24h"])
        score -= erro_penalty

        # Conversas bidirecionais (max +15 pontos)
        # 20+ conversas reais e excelente
        conversa_score = min(factors.conversas_bidirecionais / 20, 1.0) * self.PESOS["conversas_bi"]
        score += conversa_score

        # Dias sem erro (max +10 pontos)
        # 7+ dias e excelente
        estabilidade_score = min(factors.dias_sem_erro / 7, 1.0) * self.PESOS["dias_sem_erro"]
        score += estabilidade_score

        # Bonus por fase avancada
        fase_bonus = self.BONUS_FASE.get(factors.fase_warmup, 0) / 50 * self.PESOS["fase_bonus"]
        score += fase_bonus

        # Normalizar entre 0 e 100
        return max(0, min(100, int(score)))

    def determinar_nivel(self, score: int) -> TrustLevel:
        """Determina nivel de confianca baseado no score."""
        if score >= 80:
            return TrustLevel.VERDE
        elif score >= 60:
            return TrustLevel.AMARELO
        elif score >= 40:
            return TrustLevel.LARANJA
        elif score >= 20:
            return TrustLevel.VERMELHO
        else:
            return TrustLevel.CRITICO

    def calcular_permissoes(
        self,
        score: int,
        nivel: TrustLevel,
        fase_warmup: str,
    ) -> Permissoes:
        """
        Calcula permissoes baseado no score, nivel e fase.

        Combina restricoes do nivel com limites da fase.
        """
        # Limites base da fase
        limites_fase = self.LIMITES_FASE.get(fase_warmup, self.LIMITES_FASE["operacao"])

        # Permissoes base por nivel
        if nivel == TrustLevel.VERDE:
            permissoes = Permissoes(
                pode_prospectar=True,
                pode_followup=True,
                pode_responder=True,
                limite_hora=limites_fase["hora"],
                limite_dia=limites_fase["dia"],
                delay_minimo_segundos=45,  # Mais rapido
            )
        elif nivel == TrustLevel.AMARELO:
            permissoes = Permissoes(
                pode_prospectar=True,
                pode_followup=True,
                pode_responder=True,
                limite_hora=int(limites_fase["hora"] * 0.8),  # 80% do limite
                limite_dia=int(limites_fase["dia"] * 0.8),
                delay_minimo_segundos=60,
            )
        elif nivel == TrustLevel.LARANJA:
            permissoes = Permissoes(
                pode_prospectar=False,  # Sem prospeccao
                pode_followup=True,
                pode_responder=True,
                limite_hora=int(limites_fase["hora"] * 0.5),  # 50% do limite
                limite_dia=int(limites_fase["dia"] * 0.5),
                delay_minimo_segundos=90,
            )
        elif nivel == TrustLevel.VERMELHO:
            permissoes = Permissoes(
                pode_prospectar=False,
                pode_followup=False,  # Sem followup
                pode_responder=True,
                limite_hora=int(limites_fase["hora"] * 0.2),  # 20% do limite
                limite_dia=int(limites_fase["dia"] * 0.2),
                delay_minimo_segundos=120,
            )
        else:  # CRITICO
            permissoes = Permissoes(
                pode_prospectar=False,
                pode_followup=False,
                pode_responder=True,  # Apenas resposta
                limite_hora=3,  # Minimo absoluto
                limite_dia=10,
                delay_minimo_segundos=180,  # Bem lento
            )

        return permissoes


# Instancia global
trust_engine = TrustScoreEngine()


async def calcular_trust_score(chip_id: str) -> dict:
    """
    Calcula e atualiza Trust Score de um chip.

    Args:
        chip_id: UUID do chip

    Returns:
        dict com score, nivel e permissoes
    """
    # Buscar dados do chip
    result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

    if not result.data:
        raise ValueError(f"Chip {chip_id} nao encontrado")

    chip = result.data

    # Calcular idade
    created_at = datetime.fromisoformat(chip["created_at"].replace("Z", "+00:00"))
    idade_dias = (datetime.now(created_at.tzinfo) - created_at).days

    # Montar fatores
    factors = TrustFactors(
        idade_dias=idade_dias,
        taxa_resposta=float(chip.get("taxa_resposta", 0)),
        taxa_delivery=float(chip.get("taxa_delivery", 1)),
        taxa_block=float(chip.get("taxa_block", 0)),
        diversidade_midia=len(chip.get("tipos_midia_usados", [])),
        erros_24h=chip.get("erros_ultimas_24h", 0),
        conversas_bidirecionais=chip.get("conversas_bidirecionais", 0),
        dias_sem_erro=chip.get("dias_sem_erro", 0),
        fase_warmup=chip.get("fase_warmup", "repouso"),
        msgs_enviadas_total=chip.get("msgs_enviadas_total", 0),
        msgs_recebidas_total=chip.get("msgs_recebidas_total", 0),
        grupos_count=chip.get("grupos_count", 0),
    )

    # Calcular score e nivel
    score = trust_engine.calcular_score(factors)
    nivel = trust_engine.determinar_nivel(score)
    permissoes = trust_engine.calcular_permissoes(score, nivel, factors.fase_warmup)

    # Atualizar chip no banco
    update_data = {
        "trust_score": score,
        "trust_level": nivel.value,
        "ultimo_calculo_trust": datetime.now().isoformat(),
        "trust_factors": {
            "idade_dias": factors.idade_dias,
            "taxa_resposta": factors.taxa_resposta,
            "taxa_delivery": factors.taxa_delivery,
            "taxa_block": factors.taxa_block,
            "diversidade_midia": factors.diversidade_midia,
            "erros_24h": factors.erros_24h,
            "conversas_bidirecionais": factors.conversas_bidirecionais,
            "dias_sem_erro": factors.dias_sem_erro,
        },
        "pode_prospectar": permissoes.pode_prospectar,
        "pode_followup": permissoes.pode_followup,
        "pode_responder": permissoes.pode_responder,
        "limite_hora": permissoes.limite_hora,
        "limite_dia": permissoes.limite_dia,
        "delay_minimo_segundos": permissoes.delay_minimo_segundos,
    }

    supabase.table("chips").update(update_data).eq("id", chip_id).execute()

    # Registrar historico
    supabase.table("chip_trust_history").insert({
        "chip_id": chip_id,
        "score": score,
        "level": nivel.value,
        "factors": update_data["trust_factors"],
        "permissoes": {
            "pode_prospectar": permissoes.pode_prospectar,
            "pode_followup": permissoes.pode_followup,
            "pode_responder": permissoes.pode_responder,
            "limite_hora": permissoes.limite_hora,
            "limite_dia": permissoes.limite_dia,
        },
    }).execute()

    logger.info(f"[TrustScore] Chip {chip_id}: {score} ({nivel.value})")

    return {
        "chip_id": chip_id,
        "score": score,
        "nivel": nivel.value,
        "permissoes": {
            "pode_prospectar": permissoes.pode_prospectar,
            "pode_followup": permissoes.pode_followup,
            "pode_responder": permissoes.pode_responder,
            "limite_hora": permissoes.limite_hora,
            "limite_dia": permissoes.limite_dia,
            "delay_minimo_segundos": permissoes.delay_minimo_segundos,
        },
        "factors": update_data["trust_factors"],
    }


async def obter_permissoes(chip_id: str) -> Permissoes:
    """
    Obtem permissoes atuais de um chip.

    Args:
        chip_id: UUID do chip

    Returns:
        Permissoes do chip
    """
    result = supabase.table("chips").select(
        "pode_prospectar, pode_followup, pode_responder, "
        "limite_hora, limite_dia, delay_minimo_segundos"
    ).eq("id", chip_id).single().execute()

    if not result.data:
        raise ValueError(f"Chip {chip_id} nao encontrado")

    return Permissoes(
        pode_prospectar=result.data.get("pode_prospectar", False),
        pode_followup=result.data.get("pode_followup", False),
        pode_responder=result.data.get("pode_responder", True),
        limite_hora=result.data.get("limite_hora", 5),
        limite_dia=result.data.get("limite_dia", 30),
        delay_minimo_segundos=result.data.get("delay_minimo_segundos", 120),
    )
