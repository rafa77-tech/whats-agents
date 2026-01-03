"""
Capabilities Gate - Filtra tools E controla claims por modo de conversa.

Sprint 29 - Conversation Mode

3 CAMADAS DE PROTEÇÃO:
1. Tools - Backend bloqueia chamadas
2. Claims - Prompt proíbe promessas
3. Behavior - Prompt exige comportamento

GUARDRAIL CRÍTICO: Julia é INTERMEDIÁRIA
- Não pode negociar valores
- Não pode confirmar reservas
- Conecta médico com responsável da vaga
"""
import logging
from typing import Any

from .types import ConversationMode

logger = logging.getLogger(__name__)


# =============================================================================
# PROIBIÇÕES GLOBAIS (Aplicam a TODOS os modos)
# Julia é INTERMEDIÁRIA - não pode negociar nem confirmar reservas
# =============================================================================
GLOBAL_FORBIDDEN_CLAIMS = [
    "negotiate_price",           # NUNCA negociar valores
    "confirm_booking",           # NUNCA confirmar reserva
    "confirm_booking_directly",  # NUNCA confirmar reserva sozinha
    "guarantee_availability",    # NUNCA garantir disponibilidade
    "promise_conditions",        # NUNCA prometer condições
    "negotiate_terms",           # NUNCA negociar termos
]

GLOBAL_FORBIDDEN_TOOLS = [
    "reservar_plantao",          # Tool OBSOLETA - Julia não reserva
    "calcular_valor",            # Julia não negocia valores
]


# =============================================================================
# CAPABILITIES POR MODO (3 camadas)
# =============================================================================
CAPABILITIES_BY_MODE: dict[ConversationMode, dict] = {
    ConversationMode.DISCOVERY: {
        # CAMADA 1: Tools
        "allowed_tools": [
            "salvar_memoria",
            "perguntar_interesse",
            "perguntar_especialidade",
            "verificar_perfil",
        ],
        "forbidden_tools": [
            "buscar_vagas",
            "criar_handoff_externo",
            "registrar_status_intermediacao",
            "solicitar_documentos",
        ],
        # CAMADA 2: Claims proibidos (além dos globais)
        "forbidden_claims": [
            "offer_specific_shift",
            "quote_price",
            "promise_availability",
        ],
        # CAMADA 3: Comportamento requerido
        "required_behavior": (
            "Você está em DISCOVERY: conheça o médico.\n"
            "- Pergunte 1 coisa de qualificação antes de propor transição\n"
            "- NÃO ofereça vaga nem valores específicos\n"
            "- Se ele pedir plantão, faça micro-confirmação antes de transicionar\n"
            "- Se perguntarem sobre VALORES: explique de forma genérica (faixa/depende), "
            "sem mencionar vaga específica, e puxe 1 pergunta de qualificação"
        ),
        "tone": "leve",
        "description": "Conhecer o médico, entender perfil e interesse",
    },

    ConversationMode.OFERTA: {
        # OFERTA = INTERMEDIAÇÃO (Julia NÃO é dona da vaga)
        "allowed_tools": [
            "buscar_vagas",                    # Somente leitura / apresentar opções
            "criar_handoff_externo",           # Coloca em contato com o dono da vaga
            "registrar_status_intermediacao",  # Status: interessado/contatado/fechado/sem_resposta
            "agendar_followup",                # Agendar acompanhamento
            "salvar_memoria",                  # Sempre
        ],
        "forbidden_tools": [
            "perguntar_especialidade",  # Já deveria saber
        ],
        # Claims proibidos MESMO em oferta (Julia é intermediária)
        "forbidden_claims": [
            "confirm_booking",          # "fechado", "confirmado", "tá reservado"
            "quote_price",              # "paga X", "consigo X", "valor mínimo"
            "promise_availability",     # "garanto que ainda tem"
            "negotiate_terms",          # "consigo melhorar", "dá pra subir"
        ],
        "required_behavior": (
            "Você está em OFERTA (INTERMEDIAÇÃO): apresente a vaga e conecte o médico ao responsável.\n"
            "- Você NÃO é dona da vaga e NÃO confirma plantão\n"
            "- Você NÃO negocia valores/condições\n"
            "- Seu objetivo é: (1) confirmar interesse, (2) fazer ponte com o responsável, (3) acompanhar até desfecho\n"
            "- Se perguntarem valores, responda que quem confirma é o responsável e ofereça fazer a ponte agora\n\n"
            "AÇÃO OBRIGATÓRIA - Quando médico aceitar vaga ('fechou', 'quero essa', 'pode reservar'):\n"
            "1. Procure o VAGA_ID_PARA_HANDOFF da vaga aceita no histórico de tool_results\n"
            "2. CHAME a tool criar_handoff_externo COM O UUID - isso é OBRIGATÓRIO\n"
            "3. NÃO chame buscar_vagas de novo - você já tem o UUID no contexto\n"
            "4. NUNCA apenas DIGA que vai passar pro responsável - você DEVE chamar a tool\n"
            "5. Após chamar criar_handoff_externo, diga: 'Pronto! Passei pro responsável da vaga!'"
        ),
        "tone": "objetiva",
        "description": "Ofertar vaga e intermediar contato com o responsável",
    },

    ConversationMode.FOLLOWUP: {
        # FOLLOWUP = Acompanhar desfecho da intermediação
        "allowed_tools": [
            "buscar_vagas",                    # Pode oferecer novas opções
            "criar_handoff_externo",           # Pode reconectar com outro responsável
            "registrar_status_intermediacao",  # Atualizar status: fechou/não fechou/sem resposta
            "salvar_memoria",                  # Sempre
            "agendar_followup",                # Pode remarcar
            "perguntar_interesse",             # Re-sondar
        ],
        "forbidden_tools": [
            "perguntar_especialidade",  # Já deveria saber
        ],
        "forbidden_claims": [
            "pressure_decision",         # "Preciso de resposta hoje"
            "create_urgency",            # "Vai acabar!"
            "confirm_booking",           # NUNCA confirmar
            "negotiate_terms",           # NUNCA negociar
        ],
        "required_behavior": (
            "Você está em FOLLOWUP: acompanhe o desfecho da intermediação.\n"
            "- Pergunte se conseguiu falar com o responsável da vaga\n"
            "- Se fechou COM O RESPONSÁVEL, registre como conversão\n"
            "- Se não fechou, entenda o motivo e ofereça novas opções\n"
            "- Você continua sendo INTERMEDIÁRIA - não negocie nem confirme\n\n"
            "AÇÃO OBRIGATÓRIA - Se o médico aceitar uma vaga ('fechou', 'quero essa'):\n"
            "1. Procure o VAGA_ID_PARA_HANDOFF no histórico de tool_results\n"
            "2. CHAME a tool criar_handoff_externo COM O UUID - isso é OBRIGATÓRIO\n"
            "3. NUNCA apenas DIGA que vai passar - você DEVE chamar a tool\n"
            "4. Após chamar criar_handoff_externo, diga: 'Pronto! Passei pro responsável!'"
        ),
        "tone": "leve",
        "description": "Acompanhar desfecho da intermediação, manter relacionamento",
    },

    ConversationMode.REATIVACAO: {
        "allowed_tools": [
            "salvar_memoria",           # Sempre
            "perguntar_interesse",      # Re-sondar
            "buscar_vagas",             # Pode mostrar novidades
            "agendar_followup",         # Pode agendar
        ],
        "forbidden_tools": [
            "criar_handoff_externo",           # NÃO conectar direto (ainda não reengajou)
            "registrar_status_intermediacao",  # NÃO registrar ainda
            "solicitar_documentos",            # NÃO cobrar
        ],
        "forbidden_claims": [
            "offer_specific_shift",     # Não oferecer direto
            "quote_price",              # Não falar de valor
            "pressure_return",          # "Sumiu!" "Cadê você?"
            "confirm_booking",          # NUNCA confirmar
            "negotiate_terms",          # NUNCA negociar
        ],
        "required_behavior": (
            "Você está em REATIVAÇÃO: seja gentil.\n"
            "- Não cobre resposta\n"
            "- Ofereça algo novo/diferente\n"
            "- Lembre: você é INTERMEDIÁRIA - não negocie nem confirme"
        ),
        "tone": "cauteloso",
        "description": "Reativar contato de forma gentil, sem pressão",
    },
}


# Mapeamento de claims para texto legível
CLAIMS_TO_TEXT = {
    "offer_specific_shift": "oferecer plantão específico",
    "quote_price": "citar valores exatos",
    "confirm_booking": "confirmar reserva",
    "confirm_booking_directly": "confirmar reserva sozinha",
    "promise_availability": "prometer disponibilidade",
    "pressure_decision": "pressionar por decisão",
    "create_urgency": "criar urgência falsa",
    "pressure_return": "cobrar retorno",
    "negotiate_price": "negociar valores",
    "negotiate_terms": "negociar termos/condições",
    "guarantee_availability": "garantir disponibilidade",
    "promise_conditions": "prometer condições",
}


class CapabilitiesGate:
    """
    Gate que filtra tools E controla claims por modo de conversa.

    3 CAMADAS DE PROTEÇÃO:
    1. filter_tools() - Backend bloqueia tools proibidas
    2. get_forbidden_claims() - Para injetar no prompt
    3. get_required_behavior() - Para injetar no prompt

    GUARDRAIL CRÍTICO: Proibições globais aplicam a TODOS os modos.
    """

    def __init__(self, mode: ConversationMode):
        """
        Inicializa o gate para um modo específico.

        Args:
            mode: Modo atual da conversa
        """
        self.mode = mode
        self.config = CAPABILITIES_BY_MODE.get(
            mode, CAPABILITIES_BY_MODE[ConversationMode.DISCOVERY]
        )

    # === CAMADA 1: Tools ===

    def get_allowed_tools(self) -> list[str]:
        """Retorna lista de tools permitidas no modo atual."""
        return self.config.get("allowed_tools", [])

    def get_forbidden_tools(self) -> list[str]:
        """Retorna lista de tools proibidas no modo atual + globais."""
        mode_forbidden = self.config.get("forbidden_tools", [])
        # Adiciona proibições globais
        return list(set(mode_forbidden) | set(GLOBAL_FORBIDDEN_TOOLS))

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Verifica se uma tool específica é permitida."""
        # Verifica proibições globais primeiro
        if tool_name in GLOBAL_FORBIDDEN_TOOLS:
            logger.debug(f"Tool '{tool_name}' bloqueada globalmente")
            return False
        # Depois verifica proibições do modo
        forbidden = self.config.get("forbidden_tools", [])
        if tool_name in forbidden:
            logger.debug(f"Tool '{tool_name}' bloqueada no modo {self.mode.value}")
            return False
        return True

    def filter_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Filtra lista de tools, removendo as proibidas.

        Args:
            tools: Lista de definições de tools (formato Claude)

        Returns:
            Lista filtrada apenas com tools permitidas
        """
        # Combina proibições do modo + globais
        forbidden = set(self.config.get("forbidden_tools", [])) | set(GLOBAL_FORBIDDEN_TOOLS)

        filtered = [
            tool for tool in tools
            if tool.get("name") not in forbidden
        ]

        removed = len(tools) - len(filtered)
        if removed:
            logger.debug(
                f"CapabilitiesGate [{self.mode.value}]: "
                f"removidas {removed} tools de {len(tools)}"
            )

        return filtered

    # === CAMADA 2: Claims (promessas verbais) ===

    def get_forbidden_claims(self) -> list[str]:
        """Retorna lista de claims proibidos no modo atual + globais."""
        mode_claims = self.config.get("forbidden_claims", [])
        # Adiciona proibições globais
        return list(set(mode_claims) | set(GLOBAL_FORBIDDEN_CLAIMS))

    # === CAMADA 3: Comportamento requerido ===

    def get_required_behavior(self) -> str:
        """Retorna comportamento requerido no modo atual."""
        return self.config.get("required_behavior", "")

    def get_tone(self) -> str:
        """Retorna tom recomendado para o modo."""
        return self.config.get("tone", "leve")

    def get_description(self) -> str:
        """Retorna descrição do modo."""
        return self.config.get("description", "")

    # === GERAÇÃO DE CONSTRAINTS PARA PROMPT ===

    def get_constraints_text(self) -> str:
        """
        Gera texto completo de constraints para injetar no prompt.

        Inclui:
        - GUARDRAIL de intermediação (SEMPRE)
        - Modo atual
        - Comportamento requerido
        - Claims proibidos (modo + globais)
        - Tools proibidas

        Returns:
            Texto formatado para o prompt
        """
        parts = []

        # GUARDRAIL CRÍTICO (SEMPRE)
        parts.append("## REGRA ABSOLUTA: VOCÊ É INTERMEDIÁRIA")
        parts.append("- NUNCA negocie valores de plantão")
        parts.append("- NUNCA confirme reservas diretamente")
        parts.append("- Seu papel é CONECTAR o médico com o responsável da vaga")
        parts.append("")

        # Header do modo
        parts.append(f"## MODO DE CONVERSA: {self.mode.value.upper()}")
        parts.append("")

        # Comportamento requerido (CAMADA 3)
        required = self.get_required_behavior()
        if required:
            parts.append(required)
            parts.append("")

        # Claims proibidos (CAMADA 2) - modo + globais
        claims = self.get_forbidden_claims()
        if claims:
            claims_text = ", ".join(CLAIMS_TO_TEXT.get(c, c) for c in claims)
            parts.append(f"**NÃO PODE:** {claims_text}")
            parts.append("")

        # Tools proibidas (para referência, já bloqueado no backend)
        tools = self.get_forbidden_tools()
        if tools:
            parts.append(f"**Tools bloqueadas:** {', '.join(tools)}")

        return "\n".join(parts)


def get_capabilities_gate(mode: ConversationMode) -> CapabilitiesGate:
    """Factory function para criar CapabilitiesGate."""
    return CapabilitiesGate(mode)
