"""
Prompts de Micro-Confirmação para transições de modo.

Sprint 29 - Conversation Mode

REGRA CRÍTICA: A micro-confirmação é sobre CONECTAR COM RESPONSÁVEL,
não sobre reservar. Julia é INTERMEDIÁRIA.

Exemplos corretos:
✅ "Quer que eu te conecte ao responsável pela vaga X?"
✅ "Posso te colocar em contato com quem tá oferecendo?"

Exemplos ERRADOS:
❌ "Quer que eu reserve pra você?" (Julia NÃO reserva)
❌ "Posso confirmar?" (Julia NÃO confirma)
"""
from .types import ConversationMode


# Prompts de micro-confirmação por tipo de transição
MICRO_CONFIRMATION_PROMPTS: dict[tuple[ConversationMode, ConversationMode], str] = {
    # discovery → oferta (precisa qualificar antes de mostrar vagas)
    (ConversationMode.DISCOVERY, ConversationMode.OFERTA): (
        "\n\n## ATENÇÃO: MICRO-CONFIRMAÇÃO NECESSÁRIA\n"
        "O médico mostrou interesse em vagas, mas ANTES de oferecer:\n"
        "1. Faça UMA pergunta de qualificação\n"
        "2. NÃO mencione vagas específicas ainda\n"
        "3. NÃO fale de valores\n"
        "4. Aguarde a resposta antes de mostrar opções\n\n"
        "Exemplos de micro-confirmação:\n"
        "- \"Que legal! Só pra eu entender melhor - vc já tem CRM ativo em SP?\"\n"
        "- \"Show! Vc tá procurando mais fixo ou avulso?\"\n"
        "- \"Boa! Qual região vc prefere?\"\n"
        "- \"Legal! Prefere diurno ou noturno?\"\n\n"
        "LEMBRE-SE: Você é INTERMEDIÁRIA - não negocia valores nem confirma reservas."
    ),

    # followup → oferta (verificar interesse em nova oportunidade)
    (ConversationMode.FOLLOWUP, ConversationMode.OFERTA): (
        "\n\n## ATENÇÃO: MICRO-CONFIRMAÇÃO NECESSÁRIA\n"
        "O médico pode estar interessado em nova oportunidade. ANTES de oferecer:\n"
        "1. Pergunte se quer ver os detalhes\n"
        "2. NÃO apresente a vaga ainda\n"
        "3. NÃO fale de valores\n\n"
        "Exemplos:\n"
        "- \"Surgiu uma vaga interessante - quer que eu mande os detalhes?\"\n"
        "- \"Lembrei de vc pq abriu uma boa, quer ver?\"\n"
        "- \"Tem uma oportunidade nova aqui, quer saber mais?\"\n\n"
        "LEMBRE-SE: Você é INTERMEDIÁRIA - conecta com o responsável, não fecha."
    ),
}


def get_micro_confirmation_prompt(
    current_mode: ConversationMode,
    pending_mode: ConversationMode,
) -> str:
    """
    Retorna prompt de micro-confirmação para a transição.

    Args:
        current_mode: Modo atual
        pending_mode: Modo pendente (aguardando confirmação)

    Returns:
        Prompt de micro-confirmação ou string vazia se não aplicável
    """
    transition_key = (current_mode, pending_mode)
    return MICRO_CONFIRMATION_PROMPTS.get(transition_key, "")


# Comportamento adicional quando em pending (para qualquer transição)
PENDING_BEHAVIOR_REMINDER = (
    "\n\n## TRANSIÇÃO PENDENTE\n"
    "Há uma transição de modo aguardando confirmação do médico.\n"
    "- Se ele responder positivamente → a transição será aplicada\n"
    "- Se ele responder negativamente/objeção → a transição será cancelada\n"
    "- Continue a conversa normalmente enquanto aguarda"
)
