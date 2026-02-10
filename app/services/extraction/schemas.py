"""
Schemas para o serviço de extração de dados.

Sprint 53: Discovery Intelligence Pipeline.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class Interesse(str, Enum):
    """Classificação de interesse do médico."""

    POSITIVO = "positivo"
    NEGATIVO = "negativo"
    NEUTRO = "neutro"
    INCERTO = "incerto"


class ProximoPasso(str, Enum):
    """Ação sugerida após análise da conversa."""

    ENVIAR_VAGAS = "enviar_vagas"
    AGENDAR_FOLLOWUP = "agendar_followup"
    AGUARDAR_RESPOSTA = "aguardar_resposta"
    ESCALAR_HUMANO = "escalar_humano"
    MARCAR_INATIVO = "marcar_inativo"
    SEM_ACAO = "sem_acao"


class TipoObjecao(str, Enum):
    """Tipos de objeção que o médico pode apresentar."""

    PRECO = "preco"
    TEMPO = "tempo"
    CONFIANCA = "confianca"
    DISTANCIA = "distancia"
    DISPONIBILIDADE = "disponibilidade"
    EMPRESA_ATUAL = "empresa_atual"
    PESSOAL = "pessoal"
    OUTRO = "outro"


class SeveridadeObjecao(str, Enum):
    """Severidade da objeção detectada."""

    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


@dataclass
class Objecao:
    """Representa uma objeção detectada na conversa."""

    tipo: TipoObjecao
    descricao: str
    severidade: SeveridadeObjecao


@dataclass
class ExtractionContext:
    """Contexto de entrada para extração de dados."""

    mensagem_medico: str
    resposta_julia: str
    nome_medico: str
    especialidade_cadastrada: Optional[str] = None
    regiao_cadastrada: Optional[str] = None
    campanha_id: Optional[int] = None
    tipo_campanha: Optional[str] = None
    conversa_id: Optional[str] = None
    cliente_id: Optional[str] = None


@dataclass
class ExtractionResult:
    """Resultado da extração de dados da conversa."""

    # Classificação
    interesse: Interesse
    interesse_score: float  # 0.0 a 1.0

    # Dados extraídos
    especialidade_mencionada: Optional[str] = None
    regiao_mencionada: Optional[str] = None
    disponibilidade_mencionada: Optional[str] = None

    # Objeção (se detectada)
    objecao: Optional[Objecao] = None

    # Listas
    preferencias: List[str] = field(default_factory=list)
    restricoes: List[str] = field(default_factory=list)

    # Dados a corrigir no cadastro
    dados_corrigidos: Dict[str, Any] = field(default_factory=dict)

    # Próximo passo sugerido
    proximo_passo: ProximoPasso = ProximoPasso.SEM_ACAO

    # Metadados
    confianca: float = 0.0
    raw_json: Optional[Dict] = None

    # Métricas
    tokens_input: int = 0
    tokens_output: int = 0
    latencia_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário (para serialização)."""
        result = {
            "interesse": self.interesse.value,
            "interesse_score": self.interesse_score,
            "especialidade_mencionada": self.especialidade_mencionada,
            "regiao_mencionada": self.regiao_mencionada,
            "disponibilidade_mencionada": self.disponibilidade_mencionada,
            "preferencias": self.preferencias,
            "restricoes": self.restricoes,
            "dados_corrigidos": self.dados_corrigidos,
            "proximo_passo": self.proximo_passo.value,
            "confianca": self.confianca,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "latencia_ms": self.latencia_ms,
        }

        if self.objecao:
            result["objecao"] = {
                "tipo": self.objecao.tipo.value,
                "descricao": self.objecao.descricao,
                "severidade": self.objecao.severidade.value,
            }
        else:
            result["objecao"] = None

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionResult":
        """Cria instância a partir de dicionário."""
        objecao = None
        if data.get("objecao"):
            objecao_data = data["objecao"]
            objecao = Objecao(
                tipo=TipoObjecao(objecao_data["tipo"]),
                descricao=objecao_data.get("descricao", ""),
                severidade=SeveridadeObjecao(objecao_data.get("severidade", "media")),
            )

        return cls(
            interesse=Interesse(data.get("interesse", "incerto")),
            interesse_score=float(data.get("interesse_score", 0.5)),
            especialidade_mencionada=data.get("especialidade_mencionada"),
            regiao_mencionada=data.get("regiao_mencionada"),
            disponibilidade_mencionada=data.get("disponibilidade_mencionada"),
            objecao=objecao,
            preferencias=data.get("preferencias", []),
            restricoes=data.get("restricoes", []),
            dados_corrigidos=data.get("dados_corrigidos", {}),
            proximo_passo=ProximoPasso(data.get("proximo_passo", "sem_acao")),
            confianca=float(data.get("confianca", 0.5)),
            tokens_input=data.get("tokens_input", 0),
            tokens_output=data.get("tokens_output", 0),
            latencia_ms=data.get("latencia_ms", 0),
        )
