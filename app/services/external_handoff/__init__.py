"""
External Handoff - Ponte Automatica Medico-Divulgador.

Sprint 20 - Marketplace Assistido.

Este modulo gerencia a ponte entre medicos interessados em vagas
e divulgadores externos (donos das vagas de grupo).
"""
from app.services.external_handoff.tokens import (
    gerar_token_confirmacao,
    gerar_par_links,
    validar_token,
    marcar_token_usado,
)
from app.services.external_handoff.service import (
    criar_ponte_externa,
    buscar_divulgador_por_vaga_grupo,
)
from app.services.external_handoff.repository import (
    criar_handoff,
    buscar_handoff_por_id,
    buscar_handoff_pendente_por_telefone,
    atualizar_status_handoff,
    listar_handoffs_pendentes,
)

__all__ = [
    # Tokens
    "gerar_token_confirmacao",
    "gerar_par_links",
    "validar_token",
    "marcar_token_usado",
    # Service
    "criar_ponte_externa",
    "buscar_divulgador_por_vaga_grupo",
    # Repository
    "criar_handoff",
    "buscar_handoff_por_id",
    "buscar_handoff_pendente_por_telefone",
    "atualizar_status_handoff",
    "listar_handoffs_pendentes",
]
