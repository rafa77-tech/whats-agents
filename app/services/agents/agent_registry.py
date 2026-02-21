"""
Agent Registry — Stores available agents with capabilities.

Sprint 70+ — Chunk 26.
"""

import logging
from typing import Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Informações sobre um agente registrado."""

    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    active: bool = True


class AgentRegistry:
    """
    Registro de agentes AI disponíveis.

    Mantém catálogo de agentes com suas capacidades
    para roteamento inteligente de conversas.
    """

    def __init__(self):
        self._agents: dict[str, AgentInfo] = {}
        self._registrar_agentes_padrao()

    def _registrar_agentes_padrao(self):
        """Registra agentes padrão do sistema."""
        self.registrar(
            AgentInfo(
                name="julia",
                description="Escalista virtual - prospecção e gestão de médicos",
                capabilities=[
                    "prospeccao",
                    "oferta_vagas",
                    "negociacao",
                    "confirmacao",
                    "followup",
                ],
            )
        )
        self.registrar(
            AgentInfo(
                name="helena",
                description="Agente de analytics e gestão via Slack",
                capabilities=[
                    "metricas",
                    "relatorios",
                    "status_sistema",
                    "gestao_chips",
                ],
            )
        )
        self.registrar(
            AgentInfo(
                name="human",
                description="Operador humano via Chatwoot",
                capabilities=["atendimento_complexo", "juridico", "financeiro"],
            )
        )

    def registrar(self, agent: AgentInfo) -> None:
        """Registra um novo agente."""
        self._agents[agent.name] = agent
        logger.debug("[AgentRegistry] Agente '%s' registrado", agent.name)

    def esta_registrado(self, name: str) -> bool:
        """Verifica se agente está registrado."""
        return name in self._agents

    def obter(self, name: str) -> Optional[AgentInfo]:
        """Obtém informações do agente."""
        return self._agents.get(name)

    def listar(self, apenas_ativos: bool = True) -> List[AgentInfo]:
        """Lista todos os agentes."""
        agents = list(self._agents.values())
        if apenas_ativos:
            agents = [a for a in agents if a.active]
        return agents

    def encontrar_por_capacidade(self, capability: str) -> List[AgentInfo]:
        """Encontra agentes com determinada capacidade."""
        return [
            a
            for a in self._agents.values()
            if a.active and capability in a.capabilities
        ]


# Singleton
agent_registry = AgentRegistry()
