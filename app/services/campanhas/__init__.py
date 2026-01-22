"""
Modulo de campanhas.

Estrutura:
- repository: Acesso ao banco de dados
- executor: Execucao de campanhas
- types: Tipos e enums

Sprint 35 - Epic 03/04
"""
from app.services.campanhas.executor import CampanhaExecutor, campanha_executor
from app.services.campanhas.repository import CampanhaRepository, campanha_repository
from app.services.campanhas.types import (
    AudienceFilters,
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)

__all__ = [
    "CampanhaExecutor",
    "campanha_executor",
    "CampanhaRepository",
    "campanha_repository",
    "TipoCampanha",
    "StatusCampanha",
    "AudienceFilters",
    "CampanhaData",
]
