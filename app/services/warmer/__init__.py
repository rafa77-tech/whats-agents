"""
Warmer Engine - Sistema de aquecimento de chips WhatsApp.

Componentes:
- trust_score: Calculo multiparametrico de confianca
- human_simulator: Simulacao de comportamento humano
- conversation_generator: Geracao de conversas naturais
- pairing_engine: Pareamento de chips para warmup
- scheduler: Agendamento de atividades
- orchestrator: Orquestracao do ciclo de warming
"""

from app.services.warmer.trust_score import (
    TrustScoreEngine,
    TrustLevel,
    calcular_trust_score,
    obter_permissoes,
)

__all__ = [
    "TrustScoreEngine",
    "TrustLevel",
    "calcular_trust_score",
    "obter_permissoes",
]
