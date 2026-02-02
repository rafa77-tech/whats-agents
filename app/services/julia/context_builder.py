"""
Context Builder - Monta contexto para geração de resposta.

Sprint 31 - S31.E2.2
Sprint 44 - T02.3: Integração com Summarizer

Responsabilidades:
- Buscar conhecimento dinâmico (RAG)
- Montar constraints (Policy Engine + Conversation Mode)
- Montar system prompt
- Converter histórico para formato de messages
- Filtrar tools por capabilities
- Sumarizar conversas longas (Sprint 44)
"""
import logging
from typing import Optional, List, Dict, Any, Tuple

from app.core.prompts import montar_prompt_julia
from app.services.conhecimento import OrquestradorConhecimento
from app.services.interacao import converter_historico_para_messages
from app.services.conversation_mode.prompts import get_micro_confirmation_prompt

from .models import JuliaContext, PolicyContext
from .summarizer import sumarizar_se_necessario

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Constrói o contexto completo para geração de resposta.

    Extrai a lógica de construção de contexto do gerar_resposta_julia(),
    tornando-a testável e reutilizável.

    Uso:
        builder = ContextBuilder()

        # Buscar conhecimento relevante
        conhecimento = await builder.buscar_conhecimento_dinamico(
            mensagem, historico_raw, medico
        )

        # Montar constraints
        constraints = builder.montar_constraints(policy_decision, capabilities_gate, mode_info)

        # Montar system prompt
        system_prompt = await builder.montar_system_prompt(contexto, conhecimento, constraints)

        # Converter histórico
        messages = builder.converter_historico(historico_raw)
    """

    def __init__(self):
        self._orquestrador = None  # Lazy init

    def _get_orquestrador(self) -> OrquestradorConhecimento:
        """Retorna orquestrador (lazy initialization)."""
        if self._orquestrador is None:
            self._orquestrador = OrquestradorConhecimento()
        return self._orquestrador

    async def buscar_conhecimento_dinamico(
        self,
        mensagem: str,
        historico_raw: List[Dict],
        medico: Dict[str, Any],
    ) -> str:
        """
        Busca conhecimento dinâmico baseado na situação.

        Analisa a mensagem e histórico para identificar:
        - Objeções do médico
        - Perfil profissional
        - Objetivo da conversa

        Args:
            mensagem: Mensagem atual do médico
            historico_raw: Histórico de interações
            medico: Dados do médico

        Returns:
            Resumo do conhecimento relevante para injetar no prompt
        """
        try:
            orquestrador = self._get_orquestrador()

            # Extrair últimas mensagens recebidas
            historico_msgs = []
            if historico_raw:
                historico_msgs = [
                    m.get("conteudo", "") for m in historico_raw
                    if m.get("tipo") == "recebida"
                ][-5:]  # Últimas 5 mensagens

            situacao = await orquestrador.analisar_situacao(
                mensagem=mensagem,
                historico=historico_msgs,
                dados_cliente=medico,
                stage=medico.get("stage_jornada", "novo"),
            )

            logger.debug(
                f"Situação detectada: objecao={situacao.objecao.tipo}, "
                f"perfil={situacao.perfil.perfil}, objetivo={situacao.objetivo.objetivo}"
            )

            return situacao.resumo

        except Exception as e:
            logger.warning(f"Erro ao buscar conhecimento dinâmico: {e}")
            return ""

    def montar_constraints(
        self,
        policy_decision: Any = None,
        capabilities_gate: Any = None,
        mode_info: Any = None,
    ) -> str:
        """
        Monta constraints combinados de Policy Engine e Conversation Mode.

        Combina:
        - Constraints da Policy Engine (Sprint 15)
        - Constraints do Conversation Mode (Sprint 29)
        - Prompt de micro-confirmação se há pending_transition

        Args:
            policy_decision: Decisão da Policy Engine
            capabilities_gate: Gate de capabilities por modo
            mode_info: Info do modo atual

        Returns:
            String com todos os constraints combinados
        """
        constraints_parts = []

        # Constraints da Policy Engine (Sprint 15)
        if policy_decision and hasattr(policy_decision, 'constraints_text'):
            if policy_decision.constraints_text:
                constraints_parts.append(policy_decision.constraints_text)

        # Constraints do Conversation Mode (Sprint 29 - CAMADA 2)
        if capabilities_gate:
            mode_constraints = capabilities_gate.get_constraints_text()
            if mode_constraints:
                constraints_parts.append(mode_constraints)
            logger.debug(
                f"Capabilities Gate aplicado: modo={capabilities_gate.mode.value}, "
                f"claims_proibidos={len(capabilities_gate.get_forbidden_claims())}"
            )

        # Prompt de micro-confirmação se há pending_transition
        if mode_info and hasattr(mode_info, 'pending_transition') and mode_info.pending_transition:
            micro_prompt = get_micro_confirmation_prompt(
                mode_info.mode, mode_info.pending_transition
            )
            if micro_prompt:
                constraints_parts.append(micro_prompt)
                logger.debug(
                    f"Micro-confirmação injetada: {mode_info.mode.value} → "
                    f"{mode_info.pending_transition.value}"
                )

        return "\n\n---\n\n".join(constraints_parts) if constraints_parts else ""

    async def montar_system_prompt(
        self,
        contexto: Dict[str, Any],
        medico: Dict[str, Any],
        conhecimento_dinamico: str = "",
        policy_constraints: str = "",
    ) -> str:
        """
        Monta o system prompt completo para o LLM.

        Args:
            contexto: Dicionário com contextos (medico, vagas, historico, etc)
            medico: Dados do médico
            conhecimento_dinamico: Conhecimento RAG relevante
            policy_constraints: Constraints de policy e modo

        Returns:
            System prompt completo
        """
        return await montar_prompt_julia(
            contexto_medico=contexto.get("medico", ""),
            contexto_vagas=contexto.get("vagas", ""),
            historico=contexto.get("historico", ""),
            primeira_msg=contexto.get("primeira_msg", False),
            data_hora_atual=contexto.get("data_hora_atual", ""),
            dia_semana=contexto.get("dia_semana", ""),
            contexto_especialidade=contexto.get("especialidade", ""),
            contexto_handoff=contexto.get("handoff_recente", ""),
            contexto_memorias=contexto.get("memorias", ""),
            especialidade_id=medico.get("especialidade_id"),
            diretrizes=contexto.get("diretrizes", ""),
            conhecimento=conhecimento_dinamico,
            policy_constraints=policy_constraints,
        )

    def converter_historico(
        self,
        historico_raw: List[Dict],
        incluir: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Converte histórico raw para formato de messages do Claude.

        Args:
            historico_raw: Lista de interações do banco
            incluir: Se deve incluir o histórico

        Returns:
            Lista de messages no formato {"role": "...", "content": "..."}
        """
        if not incluir or not historico_raw:
            return []

        return converter_historico_para_messages(historico_raw)

    async def converter_historico_com_summarization(
        self,
        historico_raw: List[Dict],
        conversa_id: Optional[str] = None,
        incluir: bool = True,
    ) -> Tuple[List[Dict[str, str]], str]:
        """
        Sprint 44 T02.3: Converte histórico com sumarização para conversas longas.

        Para conversas com muitas mensagens:
        1. Sumariza as mensagens antigas
        2. Mantém as recentes completas
        3. Injeta resumo como primeira mensagem do sistema

        Args:
            historico_raw: Lista de interações do banco
            conversa_id: ID da conversa (para logging)
            incluir: Se deve incluir o histórico

        Returns:
            Tupla (messages, resumo):
            - messages: Lista no formato Claude
            - resumo: String com resumo (vazia se não precisou)
        """
        if not incluir or not historico_raw:
            return [], ""

        # Tentar sumarizar se necessário
        resumo, msgs_para_converter = await sumarizar_se_necessario(
            historico_raw, conversa_id
        )

        # Converter mensagens (todas ou apenas recentes)
        messages = converter_historico_para_messages(msgs_para_converter)

        if resumo:
            logger.info(
                f"[ContextBuilder] T02.3: Conversa {conversa_id} sumarizada: "
                f"{len(historico_raw)} msgs -> resumo + {len(msgs_para_converter)} recentes"
            )

        return messages, resumo

    def filtrar_tools(
        self,
        tools: List[Dict],
        capabilities_gate: Any = None,
    ) -> List[Dict]:
        """
        Filtra tools baseado no capabilities gate.

        Args:
            tools: Lista de tools disponíveis
            capabilities_gate: Gate de capabilities por modo

        Returns:
            Lista de tools filtradas
        """
        if not capabilities_gate:
            return tools

        tools_filtradas = capabilities_gate.filter_tools(tools)
        removed_count = len(tools) - len(tools_filtradas)

        if removed_count > 0:
            logger.info(
                f"Tools filtradas pelo modo {capabilities_gate.mode.value}: "
                f"{removed_count} removidas de {len(tools)}"
            )

        return tools_filtradas


# Instância default para uso direto
_default_builder: Optional[ContextBuilder] = None


def get_context_builder() -> ContextBuilder:
    """Retorna instância default do ContextBuilder."""
    global _default_builder
    if _default_builder is None:
        _default_builder = ContextBuilder()
    return _default_builder
