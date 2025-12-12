"""
[DEPRECATED] Modulo de compatibilidade para vagas.

Este arquivo foi reorganizado em:
- app/services/vagas/repository.py
- app/services/vagas/cache.py
- app/services/vagas/preferencias.py
- app/services/vagas/formatters.py
- app/services/vagas/service.py

Use: from app.services.vagas import buscar_vagas_compativeis, reservar_vaga
Sprint 10 - S10.E3.2
"""
import warnings

warnings.warn(
    "vaga.py is deprecated. Use app.services.vagas instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-exportar tudo do novo modulo para manter compatibilidade
from app.services.vagas import (
    # Service principal
    buscar_vagas_compativeis,
    buscar_vagas_por_regiao,
    reservar_vaga,
    cancelar_reserva,
    # Repository
    buscar_vaga_por_id,
    verificar_conflito,
    verificar_conflito_vaga,
    # Cache
    invalidar_cache_vagas,
    # Preferencias
    filtrar_por_preferencias,
    # Formatters
    formatar_vaga_para_mensagem,
    formatar_vagas_contexto,
)

__all__ = [
    "buscar_vagas_compativeis",
    "buscar_vagas_por_regiao",
    "reservar_vaga",
    "cancelar_reserva",
    "buscar_vaga_por_id",
    "verificar_conflito",
    "verificar_conflito_vaga",
    "invalidar_cache_vagas",
    "filtrar_por_preferencias",
    "formatar_vaga_para_mensagem",
    "formatar_vagas_contexto",
]
