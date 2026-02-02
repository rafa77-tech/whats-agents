"""
Tipos e enums para campanhas.

Sprint 35 - Epic 03
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class TipoCampanha(str, Enum):
    """Tipos de campanha disponiveis."""

    DISCOVERY = "discovery"
    OFERTA = "oferta"
    OFERTA_PLANTAO = "oferta_plantao"
    REATIVACAO = "reativacao"
    FOLLOWUP = "followup"


class StatusCampanha(str, Enum):
    """Status possiveis de uma campanha."""

    RASCUNHO = "rascunho"
    AGENDADA = "agendada"
    ATIVA = "ativa"
    PAUSADA = "pausada"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


@dataclass
class AudienceFilters:
    """Filtros de audiencia da campanha."""

    regioes: List[str] = field(default_factory=list)
    especialidades: List[str] = field(default_factory=list)
    quantidade_alvo: int = 50
    pressure_score_max: int = 70
    excluir_opt_out: bool = True
    chips_excluidos: List[str] = field(default_factory=list)  # IDs de chips a não usar

    def to_dict(self) -> dict:
        """Converte para dicionario."""
        return {
            "regioes": self.regioes,
            "especialidades": self.especialidades,
            "quantidade_alvo": self.quantidade_alvo,
            "pressure_score_max": self.pressure_score_max,
            "excluir_opt_out": self.excluir_opt_out,
            "chips_excluidos": self.chips_excluidos,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AudienceFilters":
        """Cria a partir de dicionario."""
        if not data:
            return cls()
        return cls(
            regioes=data.get("regioes", []),
            especialidades=data.get("especialidades", []),
            quantidade_alvo=data.get("quantidade_alvo", 50),
            pressure_score_max=data.get("pressure_score_max", 70),
            excluir_opt_out=data.get("excluir_opt_out", True),
            chips_excluidos=data.get("chips_excluidos", []),
        )


@dataclass
class CampanhaData:
    """Dados de uma campanha."""

    id: int
    nome_template: str
    tipo_campanha: TipoCampanha
    corpo: Optional[str] = None
    tom: Optional[str] = None
    status: StatusCampanha = StatusCampanha.RASCUNHO
    agendar_para: Optional[datetime] = None
    audience_filters: Optional[AudienceFilters] = None
    pode_ofertar: bool = False
    total_destinatarios: int = 0
    enviados: int = 0
    entregues: int = 0
    respondidos: int = 0
    objetivo: Optional[str] = None
    regras: Optional[dict] = None
    escopo_vagas: Optional[dict] = None
    created_at: Optional[datetime] = None
    iniciada_em: Optional[datetime] = None
    concluida_em: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row: dict) -> "CampanhaData":
        """Cria a partir de linha do banco."""
        # Parse tipo_campanha com fallback
        tipo_raw = row.get("tipo_campanha", "oferta_plantao")
        # Normalizar aliases em português
        tipo_aliases = {
            "descoberta": "discovery",
            "oferta_plantão": "oferta_plantao",
            "reativação": "reativacao",
        }
        tipo_raw = tipo_aliases.get(tipo_raw, tipo_raw)
        try:
            tipo = TipoCampanha(tipo_raw)
        except ValueError:
            tipo = TipoCampanha.OFERTA_PLANTAO

        # Parse status com fallback
        status_raw = row.get("status", "rascunho")
        try:
            status = StatusCampanha(status_raw)
        except ValueError:
            status = StatusCampanha.RASCUNHO

        return cls(
            id=row["id"],
            nome_template=row.get("nome_template", ""),
            tipo_campanha=tipo,
            corpo=row.get("corpo"),
            tom=row.get("tom"),
            status=status,
            agendar_para=row.get("agendar_para"),
            audience_filters=AudienceFilters.from_dict(row.get("audience_filters")),
            pode_ofertar=row.get("pode_ofertar", False),
            total_destinatarios=row.get("total_destinatarios", 0),
            enviados=row.get("enviados", 0),
            entregues=row.get("entregues", 0),
            respondidos=row.get("respondidos", 0),
            objetivo=row.get("objetivo"),
            regras=row.get("regras"),
            escopo_vagas=row.get("escopo_vagas"),
            created_at=row.get("created_at"),
            iniciada_em=row.get("iniciada_em"),
            concluida_em=row.get("concluida_em"),
        )

    def to_dict(self) -> dict:
        """Converte para dicionario."""
        return {
            "id": self.id,
            "nome_template": self.nome_template,
            "tipo_campanha": self.tipo_campanha.value,
            "corpo": self.corpo,
            "tom": self.tom,
            "status": self.status.value,
            "audience_filters": self.audience_filters.to_dict() if self.audience_filters else {},
            "pode_ofertar": self.pode_ofertar,
            "total_destinatarios": self.total_destinatarios,
            "enviados": self.enviados,
            "entregues": self.entregues,
            "respondidos": self.respondidos,
            "objetivo": self.objetivo,
            "regras": self.regras,
            "escopo_vagas": self.escopo_vagas,
        }
