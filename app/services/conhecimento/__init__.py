"""
Módulo de conhecimento dinâmico para Julia.

Sprint 13: Sistema de RAG para injeção de conhecimento nos prompts.
"""

from .indexador import IndexadorConhecimento, ParserMarkdown, ChunkConhecimento
from .buscador import BuscadorConhecimento, ResultadoBusca
from .detector_objecao import DetectorObjecao, TipoObjecao, ResultadoDeteccao
from .detector_perfil import DetectorPerfil, PerfilMedico, ResultadoPerfil
from .detector_objetivo import DetectorObjetivo, ObjetivoConversa, ResultadoObjetivo
from .orquestrador import OrquestradorConhecimento, ContextoSituacao

__all__ = [
    # E01 - Indexação
    "IndexadorConhecimento",
    "ParserMarkdown",
    "ChunkConhecimento",
    "BuscadorConhecimento",
    "ResultadoBusca",
    # E02 - Detectores
    "DetectorObjecao",
    "TipoObjecao",
    "ResultadoDeteccao",
    "DetectorPerfil",
    "PerfilMedico",
    "ResultadoPerfil",
    "DetectorObjetivo",
    "ObjetivoConversa",
    "ResultadoObjetivo",
    "OrquestradorConhecimento",
    "ContextoSituacao",
]
