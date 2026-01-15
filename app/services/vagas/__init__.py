"""
Services de gestao de vagas.

Sprint 10 - S10.E3.2
Sprint 31 - S31.E5: Adição de EspecialidadeService e filtros
"""
from .repository import (
    buscar_por_id as buscar_vaga_por_id,
    verificar_conflito as verificar_conflito_vaga,
)

from .cache import invalidar as invalidar_cache_vagas

from .preferencias import (
    filtrar_por_preferencias,
    ordenar_por_regiao,
)

from .formatters import (
    formatar_para_mensagem as formatar_vaga_para_mensagem,
    formatar_para_contexto as formatar_vagas_contexto,
)

from .service import (
    buscar_vagas_compativeis,
    buscar_vagas_por_regiao,
    reservar_vaga,
    cancelar_reserva,
    marcar_vaga_realizada,
)

# Sprint 31 - Novos módulos
from .especialidade_service import (
    EspecialidadeService,
    get_especialidade_service,
)

from .filtros import (
    filtrar_por_periodo,
    filtrar_por_dias_semana,
    filtrar_por_conflitos,
    aplicar_filtros,
)


# Compatibilidade: verificar_conflito retorna apenas bool
async def verificar_conflito(cliente_id: str, data: str, periodo_id: str) -> bool:
    """Wrapper para manter compatibilidade."""
    resultado = await verificar_conflito_vaga(cliente_id, data, periodo_id)
    return resultado["conflito"]


__all__ = [
    # Service principal
    "buscar_vagas_compativeis",
    "buscar_vagas_por_regiao",
    "reservar_vaga",
    "cancelar_reserva",
    "marcar_vaga_realizada",
    # Repository
    "buscar_vaga_por_id",
    "verificar_conflito",
    "verificar_conflito_vaga",
    # Cache
    "invalidar_cache_vagas",
    # Preferencias
    "filtrar_por_preferencias",
    "ordenar_por_regiao",
    # Formatters
    "formatar_vaga_para_mensagem",
    "formatar_vagas_contexto",
    # Sprint 31 - EspecialidadeService
    "EspecialidadeService",
    "get_especialidade_service",
    # Sprint 31 - Filtros
    "filtrar_por_periodo",
    "filtrar_por_dias_semana",
    "filtrar_por_conflitos",
    "aplicar_filtros",
]
