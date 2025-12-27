"""
Módulo de processamento de mensagens de grupos WhatsApp.

Responsável por:
- Ingestão de mensagens
- Classificação de ofertas
- Extração de dados estruturados
- Normalização com entidades do banco
- Deduplicação de vagas
- Importação para tabela de vagas
"""

from app.services.grupos.ingestor import ingerir_mensagem_grupo
from app.services.grupos.heuristica import calcular_score_heuristica, ResultadoHeuristica
from app.services.grupos.classificador import (
    classificar_batch_heuristica,
    classificar_mensagem_individual,
)

__all__ = [
    # Ingestão
    "ingerir_mensagem_grupo",
    # Heurística
    "calcular_score_heuristica",
    "ResultadoHeuristica",
    # Classificador
    "classificar_batch_heuristica",
    "classificar_mensagem_individual",
]
