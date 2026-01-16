"""
Sistema de prompts dinamicos.

Permite carregar, versionar e testar prompts sem deploy.

Sprint 32 E02: Adicionado suporte a contexto de campanha.
"""
from .loader import (
    carregar_prompt,
    carregar_prompt_especialidade,
    invalidar_cache_prompt,
    buscar_prompt_por_tipo_campanha,
    TIPOS_CAMPANHA_VALIDOS,
)
from .builder import (
    PromptBuilder,
    construir_prompt_julia,
    CampaignType,
    _formatar_escopo_vagas,
    _formatar_margem_negociacao,
)

__all__ = [
    # Loader
    "carregar_prompt",
    "carregar_prompt_especialidade",
    "invalidar_cache_prompt",
    "buscar_prompt_por_tipo_campanha",
    "TIPOS_CAMPANHA_VALIDOS",
    # Builder
    "PromptBuilder",
    "construir_prompt_julia",
    "CampaignType",
    # Formatadores (Sprint 32 E02)
    "_formatar_escopo_vagas",
    "_formatar_margem_negociacao",
]
