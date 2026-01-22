"""
Modulo de campanhas.

Estrutura:
- repository: Acesso ao banco de dados
- types: Tipos e enums

Sprint 35 - Epic 03
"""
from app.services.campanhas.repository import CampanhaRepository, campanha_repository
from app.services.campanhas.types import (
    AudienceFilters,
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)

__all__ = [
    "CampanhaRepository",
    "campanha_repository",
    "TipoCampanha",
    "StatusCampanha",
    "AudienceFilters",
    "CampanhaData",
]
