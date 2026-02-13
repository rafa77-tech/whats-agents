"""
Tools relacionadas a vagas e plantoes.

Sprint 31 - S31.E5: Refatorado para usar services
Sprint 58 - E5: Separado em modulos (1 arquivo por tool)

Este __init__.py re-exporta todos os simbolos publicos para manter
compatibilidade total com imports existentes:
    from app.tools.vagas import handle_buscar_vagas, TOOL_BUSCAR_VAGAS, ...

Tambem importa dependencias de servico no namespace do pacote para que
patches em testes (ex: patch("app.tools.vagas.supabase")) continuem
funcionando apos a refatoracao em modulos.
"""

# ---- Dependencias de servico (expostas no namespace para patch paths) -------
from app.core.timezone import agora_brasilia  # noqa: F401
from app.services.vagas import (  # noqa: F401
    buscar_vagas_compativeis,
    buscar_vagas_por_regiao,
    reservar_vaga,
    formatar_vaga_para_mensagem,
    formatar_vagas_contexto,
    verificar_conflito,
    get_especialidade_service,
    aplicar_filtros,
    filtrar_por_conflitos,
)
from app.services.supabase import supabase  # noqa: F401
from app.tools.response_formatter import (  # noqa: F401
    get_vagas_formatter,
    get_reserva_formatter,
)

# ---- Tool definitions -------------------------------------------------------
from .definitions import (
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
    TOOL_BUSCAR_INFO_HOSPITAL,
    TOOLS_VAGAS,
)

# ---- Tool handlers -----------------------------------------------------------
from .buscar_vagas import handle_buscar_vagas
from .reservar_plantao import handle_reservar_plantao
from .buscar_info import handle_buscar_info_hospital

# ---- Helpers (backward compat) -----------------------------------------------
from ._helpers import (
    _buscar_especialidade_id_por_nome,
    _limpar_especialidade_input,
    _preparar_medico_com_preferencias,
    _formatar_valor_display,
    _construir_instrucao_confirmacao,
    _construir_instrucao_ponte_externa,
    _filtrar_por_periodo,
    _filtrar_por_dias_semana,
    _buscar_vagas_base,
    _construir_resposta_sem_vagas,
    _construir_resposta_com_vagas,
)

__all__ = [
    # Definitions
    "TOOL_BUSCAR_VAGAS",
    "TOOL_RESERVAR_PLANTAO",
    "TOOL_BUSCAR_INFO_HOSPITAL",
    "TOOLS_VAGAS",
    # Handlers
    "handle_buscar_vagas",
    "handle_reservar_plantao",
    "handle_buscar_info_hospital",
    # Helpers (deprecated, backward compat)
    "_buscar_especialidade_id_por_nome",
    "_limpar_especialidade_input",
    "_preparar_medico_com_preferencias",
    "_formatar_valor_display",
    "_construir_instrucao_confirmacao",
    "_construir_instrucao_ponte_externa",
    "_filtrar_por_periodo",
    "_filtrar_por_dias_semana",
]
