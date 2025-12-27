"""
Módulo de classificação - módulos neutros para evitar circular imports.

Sprint 15 - Policy Engine
"""

from .severity_mapper import (
    ObjectionSeverity,
    map_severity,
    is_opt_out,
    is_handoff_required,
    GRAVE_KEYWORDS,
    HIGH_KEYWORDS,
    SEVERITY_BY_TYPE,
)

__all__ = [
    "ObjectionSeverity",
    "map_severity",
    "is_opt_out",
    "is_handoff_required",
    "GRAVE_KEYWORDS",
    "HIGH_KEYWORDS",
    "SEVERITY_BY_TYPE",
]
