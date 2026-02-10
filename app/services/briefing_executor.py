"""
Executor de briefings aprovados.

Sprint 11 - Epic 05: Execucao e Historico

Responsavel por:
1. Executar passos do plano aprovado
2. Mapear passos para tools existentes
3. Atualizar historico no documento
4. Notificar progresso no Slack
"""

import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from app.core.timezone import agora_brasilia
from app.services.supabase import supabase
from app.services.briefing_aprovacao import StatusAprovacao
from app.services.briefing_analyzer import AnaliseResult, PassoPlano
from app.services.google_docs import adicionar_linha_historico
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


# =============================================================================
# TIPOS E ESTRUTURAS
# =============================================================================


class StatusPasso(str, Enum):
    """Status de execucao de um passo."""

    PENDENTE = "pendente"
    EXECUTANDO = "executando"
    CONCLUIDO = "concluido"
    FALHOU = "falhou"
    PULADO = "pulado"
    AGUARDANDO_AJUDA = "aguardando_ajuda"


@dataclass
class PassoResult:
    """Resultado da execucao de um passo."""

    numero: int
    descricao: str
    status: StatusPasso
    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None
    resultado: Optional[dict] = None
    erro: Optional[str] = None
    tool_usada: Optional[str] = None

    def duracao_segundos(self) -> Optional[float]:
        """Calcula duracao em segundos."""
        if self.inicio and self.fim:
            return (self.fim - self.inicio).total_seconds()
        return None


@dataclass
class ExecutionResult:
    """Resultado completo da execucao de um briefing."""

    briefing_id: str
    doc_nome: str
    inicio: datetime
    fim: Optional[datetime] = None
    status: StatusAprovacao = StatusAprovacao.EXECUTANDO
    passos_resultados: list[PassoResult] = field(default_factory=list)
    metricas: dict = field(default_factory=dict)
    erro_global: Optional[str] = None

    def to_dict(self) -> dict:
        """Converte para dicionario."""
        data = asdict(self)
        data["inicio"] = self.inicio.isoformat()
        data["fim"] = self.fim.isoformat() if self.fim else None
        data["status"] = self.status.value
        data["passos_resultados"] = [
            {
                **asdict(p),
                "status": p.status.value,
                "inicio": p.inicio.isoformat() if p.inicio else None,
                "fim": p.fim.isoformat() if p.fim else None,
            }
            for p in self.passos_resultados
        ]
        return data


# =============================================================================
# MAPEAMENTO DE PASSOS PARA TOOLS
# =============================================================================

# Keywords que indicam qual tool usar
TOOL_KEYWORDS = {
    "enviar_mensagem": [
        "enviar",
        "mandar",
        "mensagem",
        "msg",
        "whatsapp",
        "contatar",
        "contactar",
        "falar com",
        "avisar",
    ],
    "buscar_medico": [
        "buscar medico",
        "encontrar medico",
        "achar medico",
        "medico por",
        "informacoes do medico",
    ],
    "listar_medicos": [
        "listar medicos",
        "lista de medicos",
        "medicos da",
        "todos os medicos",
        "medicos que",
        "filtrar medicos",
    ],
    "buscar_vagas": [
        "buscar vagas",
        "procurar vagas",
        "vagas disponiveis",
        "vagas abertas",
        "verificar vagas",
    ],
    "reservar_vaga": ["reservar", "agendar", "marcar vaga", "confirmar vaga"],
    "buscar_metricas": [
        "metricas",
        "estatisticas",
        "relatorio",
        "performance",
        "taxa de resposta",
        "conversao",
    ],
}


def mapear_passo_para_tool(passo: PassoPlano) -> Optional[str]:
    """
    Mapeia um passo do plano para uma tool disponivel.

    Args:
        passo: Passo do plano

    Returns:
        Nome da tool ou None se nao mapeavel
    """
    descricao_lower = passo.descricao.lower()

    for tool_name, keywords in TOOL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in descricao_lower:
                return tool_name

    return None


def extrair_parametros_passo(passo: PassoPlano, tool_name: str) -> dict:
    """
    Extrai parametros do passo para a tool.

    Por enquanto retorna parametros vazios - em versoes futuras
    usara LLM para extrair parametros da descricao.

    Args:
        passo: Passo do plano
        tool_name: Nome da tool

    Returns:
        Dict com parametros para a tool
    """
    # TODO: Usar LLM para extrair parametros da descricao
    # Por enquanto, retorna parametros vazios
    return {}


# =============================================================================
# EXECUTOR
# =============================================================================


class BriefingExecutor:
    """Executor de briefings aprovados."""

    def __init__(self, channel_id: str, user_id: str):
        """
        Inicializa executor.

        Args:
            channel_id: Canal Slack para notificacoes
            user_id: Usuario que aprovou
        """
        self.channel_id = channel_id
        self.user_id = user_id

    async def executar(self, briefing_id: str, plano: AnaliseResult) -> ExecutionResult:
        """
        Executa os passos de um briefing aprovado.

        Args:
            briefing_id: ID do briefing
            plano: Plano de analise aprovado

        Returns:
            ExecutionResult com resultados
        """
        logger.info(f"Iniciando execucao do briefing: {plano.doc_nome}")

        resultado = ExecutionResult(
            briefing_id=briefing_id, doc_nome=plano.doc_nome, inicio=agora_brasilia()
        )

        # Atualizar status para executando
        await self._atualizar_status_briefing(briefing_id, StatusAprovacao.EXECUTANDO)

        try:
            # Executar cada passo
            for passo in plano.passos:
                passo_result = await self._executar_passo(passo, plano.doc_id)
                resultado.passos_resultados.append(passo_result)

                # Notificar progresso
                await self._notificar_progresso(plano.doc_nome, passo, passo_result)

                # Se falhou e era critico, parar
                if passo_result.status == StatusPasso.FALHOU:
                    logger.warning(f"Passo {passo.numero} falhou: {passo_result.erro}")
                    # Continuar para proximos passos (nao abortar)

            # Calcular metricas finais
            resultado.fim = agora_brasilia()
            resultado.metricas = self._calcular_metricas(resultado)

            # Determinar status final
            passos_falhos = sum(
                1 for p in resultado.passos_resultados if p.status == StatusPasso.FALHOU
            )
            passos_aguardando = sum(
                1 for p in resultado.passos_resultados if p.status == StatusPasso.AGUARDANDO_AJUDA
            )

            if passos_aguardando > 0:
                resultado.status = StatusAprovacao.AGUARDANDO
            elif passos_falhos == 0:
                resultado.status = StatusAprovacao.CONCLUIDO
            elif passos_falhos < len(plano.passos):
                resultado.status = StatusAprovacao.CONCLUIDO  # Parcialmente
            else:
                resultado.status = StatusAprovacao.CANCELADO  # Tudo falhou

            # Atualizar status final
            await self._atualizar_status_briefing(briefing_id, resultado.status)

            # Notificar conclusao
            await self._notificar_conclusao(resultado)

            logger.info(
                f"Execucao concluida: {plano.doc_nome} - "
                f"{resultado.metricas.get('passos_concluidos', 0)}/{len(plano.passos)} passos"
            )

            return resultado

        except Exception as e:
            logger.error(f"Erro na execucao do briefing: {e}")
            resultado.fim = agora_brasilia()
            resultado.status = StatusAprovacao.CANCELADO
            resultado.erro_global = str(e)

            await self._atualizar_status_briefing(briefing_id, StatusAprovacao.CANCELADO)
            await self._notificar_erro(plano.doc_nome, str(e))

            return resultado

    async def _executar_passo(self, passo: PassoPlano, doc_id: str) -> PassoResult:
        """
        Executa um passo do plano.

        Args:
            passo: Passo a executar
            doc_id: ID do documento para historico

        Returns:
            PassoResult com resultado
        """
        resultado = PassoResult(
            numero=passo.numero,
            descricao=passo.descricao,
            status=StatusPasso.EXECUTANDO,
            inicio=agora_brasilia(),
        )

        # Se passo requer ajuda, marcar como aguardando
        if passo.requer_ajuda:
            resultado.status = StatusPasso.AGUARDANDO_AJUDA
            resultado.fim = agora_brasilia()
            await adicionar_linha_historico(
                doc_id,
                f"Passo {passo.numero}: Aguardando ajuda",
                f"{passo.tipo_ajuda or 'nao especificado'}",
            )
            return resultado

        # Mapear para tool
        tool_name = mapear_passo_para_tool(passo)
        resultado.tool_usada = tool_name

        if not tool_name:
            # Passo nao mapeavel - marcar como pulado
            resultado.status = StatusPasso.PULADO
            resultado.fim = agora_brasilia()
            await adicionar_linha_historico(
                doc_id, f"Passo {passo.numero}: Pulado", "Nao automatizavel"
            )
            return resultado

        # Executar tool
        try:
            from app.tools.slack import executar_tool

            params = extrair_parametros_passo(passo, tool_name)
            tool_result = await executar_tool(tool_name, params, self.user_id, self.channel_id)

            resultado.resultado = tool_result
            resultado.fim = agora_brasilia()

            if tool_result.get("success"):
                resultado.status = StatusPasso.CONCLUIDO
                await adicionar_linha_historico(
                    doc_id, f"Passo {passo.numero}: Concluido", tool_name
                )
            else:
                resultado.status = StatusPasso.FALHOU
                resultado.erro = tool_result.get("error", "Erro desconhecido")
                await adicionar_linha_historico(
                    doc_id, f"Passo {passo.numero}: Falhou", resultado.erro[:50]
                )

        except Exception as e:
            resultado.status = StatusPasso.FALHOU
            resultado.erro = str(e)
            resultado.fim = agora_brasilia()
            logger.error(f"Erro ao executar passo {passo.numero}: {e}")

        return resultado

    def _calcular_metricas(self, resultado: ExecutionResult) -> dict:
        """Calcula metricas da execucao."""
        passos = resultado.passos_resultados

        concluidos = sum(1 for p in passos if p.status == StatusPasso.CONCLUIDO)
        falhos = sum(1 for p in passos if p.status == StatusPasso.FALHOU)
        pulados = sum(1 for p in passos if p.status == StatusPasso.PULADO)
        aguardando = sum(1 for p in passos if p.status == StatusPasso.AGUARDANDO_AJUDA)

        duracao_total = (resultado.fim - resultado.inicio).total_seconds() if resultado.fim else 0

        return {
            "total_passos": len(passos),
            "passos_concluidos": concluidos,
            "passos_falhos": falhos,
            "passos_pulados": pulados,
            "passos_aguardando": aguardando,
            "taxa_sucesso": concluidos / len(passos) if passos else 0,
            "duracao_segundos": duracao_total,
        }

    async def _atualizar_status_briefing(self, briefing_id: str, status: StatusAprovacao) -> None:
        """Atualiza status do briefing no banco."""
        try:
            supabase.table("briefings_pendentes").update(
                {"status": status.value, "atualizado_em": agora_brasilia().isoformat()}
            ).eq("id", briefing_id).execute()
        except Exception as e:
            logger.error(f"Erro ao atualizar status do briefing: {e}")

    async def _notificar_progresso(
        self, doc_nome: str, passo: PassoPlano, resultado: PassoResult
    ) -> None:
        """Notifica progresso no Slack."""
        emoji = {
            StatusPasso.CONCLUIDO: "",
            StatusPasso.FALHOU: "",
            StatusPasso.PULADO: "",
            StatusPasso.AGUARDANDO_AJUDA: "",
        }.get(resultado.status, "")

        # Notificar apenas passos importantes (nao todos)
        if resultado.status in [StatusPasso.FALHOU, StatusPasso.AGUARDANDO_AJUDA]:
            try:
                await enviar_slack(
                    {
                        "text": f"{emoji} *{doc_nome}* - Passo {passo.numero}: {resultado.status.value}",
                        "channel": self.channel_id,
                    }
                )
            except Exception as e:
                logger.warning(f"Erro ao notificar progresso: {e}")

    async def _notificar_conclusao(self, resultado: ExecutionResult) -> None:
        """Notifica conclusao no Slack."""
        metricas = resultado.metricas
        emoji = "" if resultado.status == StatusAprovacao.CONCLUIDO else ""

        mensagem = f"""{emoji} *Briefing executado: {resultado.doc_nome}*

*Resultado:* {metricas["passos_concluidos"]}/{metricas["total_passos"]} passos concluidos
*Duracao:* {metricas["duracao_segundos"]:.0f}s"""

        if metricas["passos_falhos"] > 0:
            mensagem += f"\n*Falhas:* {metricas['passos_falhos']} passos"

        if metricas["passos_aguardando"] > 0:
            mensagem += f"\n*Aguardando ajuda:* {metricas['passos_aguardando']} passos"

        try:
            await enviar_slack({"text": mensagem, "channel": self.channel_id})
        except Exception as e:
            logger.warning(f"Erro ao notificar conclusao: {e}")

    async def _notificar_erro(self, doc_nome: str, erro: str) -> None:
        """Notifica erro no Slack."""
        try:
            await enviar_slack(
                {
                    "text": f" *Erro na execucao: {doc_nome}*\n{erro[:200]}",
                    "channel": self.channel_id,
                }
            )
        except Exception as e:
            logger.warning(f"Erro ao notificar erro: {e}")


# =============================================================================
# FUNCAO DE CONVENIENCIA
# =============================================================================


async def executar_briefing(
    briefing_id: str, plano: AnaliseResult, channel_id: str, user_id: str
) -> ExecutionResult:
    """
    Funcao de conveniencia para executar briefing.

    Args:
        briefing_id: ID do briefing
        plano: Plano aprovado
        channel_id: Canal Slack
        user_id: Usuario

    Returns:
        ExecutionResult
    """
    executor = BriefingExecutor(channel_id, user_id)
    return await executor.executar(briefing_id, plano)
