"""
Mapeamento determinístico de objeção → severidade.

ARQUITETURA:
- Este módulo é NEUTRO (não depende de policy)
- conhecimento/ pode usar
- policy/ pode usar
- Evita circular imports

Sprint 15 - Policy Engine
"""
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ObjectionSeverity(Enum):
    """Severidade de objeção (espelhado de policy.types para evitar import)."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    GRAVE = "grave"


# Mapeamento: tipo de objeção (do TipoObjecao) → severidade base
# Tipos vêm de app/services/conhecimento/detector_objecao.py
SEVERITY_BY_TYPE = {
    # LOW - objeções leves, fácil contornar
    "comunicacao": ObjectionSeverity.LOW,
    "disponibilidade": ObjectionSeverity.LOW,

    # MEDIUM - objeções comuns, tratáveis pela Julia
    "preco": ObjectionSeverity.MEDIUM,
    "tempo": ObjectionSeverity.MEDIUM,
    "processo": ObjectionSeverity.MEDIUM,
    "motivacao": ObjectionSeverity.MEDIUM,
    "lealdade": ObjectionSeverity.MEDIUM,

    # HIGH - atenção redobrada, pode escalar
    "confianca": ObjectionSeverity.HIGH,
    "qualidade": ObjectionSeverity.HIGH,
    "risco": ObjectionSeverity.HIGH,

    # Tipos que não existem no detector mas podem ser detectados por keywords
    "opt_out": ObjectionSeverity.GRAVE,
    "ameaca": ObjectionSeverity.GRAVE,
    "agressao": ObjectionSeverity.GRAVE,
    "pedido_humano": ObjectionSeverity.GRAVE,

    # Default
    "nenhuma": ObjectionSeverity.LOW,
}

# Keywords que SEMPRE elevam para GRAVE, independente do tipo detectado
GRAVE_KEYWORDS = [
    # Opt-out explícito
    "não me procure",
    "para de me mandar",
    "não quero mais receber",
    "me tire da lista",
    "remove meu número",
    "não manda mais",
    "para de mandar",
    "me remove",
    "tire meu contato",
    "para de me ligar",
    "não me ligue",
    "não me mande",
    "sai da minha vida",

    # Ameaças legais
    "vou denunciar",
    "vou processar",
    "meu advogado",
    "processo judicial",
    "procon",
    "anatel",
    "ministério público",
    "delegacia",
    "boletim de ocorrência",

    # Agressividade explícita
    "isso é spam",
    "spammer",
    "vou bloquear",
    "bloqueado",
    "isso é golpe",
    "golpista",
    "quem te deu meu número",
    "de onde pegaram meu contato",
    "como conseguiram meu número",
    "vai se f",
    "vai tomar",
    "seu merda",
    "filha da",
    "filho da",
    "vai a merda",
    "vai pro inferno",

    # Pedido explícito de humano
    "quero falar com uma pessoa",
    "quero falar com um humano",
    "quero falar com gente de verdade",
    "passa para um atendente",
    "me transfere para alguém",
    "quero um supervisor",
    "isso é robô",
    "isso é bot",
    "você é robô",
    "você é bot",
    "tá falando com máquina",
]

# Keywords que elevam para HIGH (se não for já GRAVE)
HIGH_KEYWORDS = [
    # Desconfiança forte
    "desconfio muito",
    "não confio em vocês",
    "parece golpe",
    "parece fraude",
    "muito suspeito",
    "estranho isso",

    # Reclamações sérias
    "vou reclamar",
    "péssimo atendimento",
    "horrível",
    "ridículo",
    "absurdo",
    "inadmissível",

    # Sinais de irritação
    "estou irritado",
    "estou cansado",
    "já disse que não",
    "quantas vezes tenho que dizer",
    "para de insistir",
]


def map_severity(
    tipo_objecao: str,
    subtipo: Optional[str],
    mensagem: str,
) -> ObjectionSeverity:
    """
    Mapeia objeção para severidade.

    Ordem de prioridade:
    1. Keywords graves (sempre GRAVE)
    2. Keywords high (eleva para HIGH se não for GRAVE)
    3. Mapa por tipo
    4. Default MEDIUM

    Args:
        tipo_objecao: Tipo detectado (ex: "preco", "confianca")
        subtipo: Subtipo se houver
        mensagem: Mensagem original para análise de keywords

    Returns:
        ObjectionSeverity
    """
    mensagem_lower = mensagem.lower()

    # 1. Checar keywords graves
    for keyword in GRAVE_KEYWORDS:
        if keyword in mensagem_lower:
            logger.debug(f"Keyword GRAVE detectada: '{keyword}'")
            return ObjectionSeverity.GRAVE

    # 2. Pegar severidade base do mapa
    tipo_lower = tipo_objecao.lower() if tipo_objecao else "nenhuma"
    base_severity = SEVERITY_BY_TYPE.get(tipo_lower, ObjectionSeverity.MEDIUM)

    # 3. Checar keywords high (eleva se não for já GRAVE)
    if base_severity not in (ObjectionSeverity.GRAVE, ObjectionSeverity.HIGH):
        for keyword in HIGH_KEYWORDS:
            if keyword in mensagem_lower:
                logger.debug(f"Keyword HIGH detectada: '{keyword}'")
                return ObjectionSeverity.HIGH

    return base_severity


def is_opt_out(tipo_objecao: str, mensagem: str) -> bool:
    """
    Verifica se é opt-out (terminal, não é cooling_off).

    Opt-out é diferente de atrito:
    - Opt-out: "não me procure mais" → permission_state = opted_out
    - Atrito: "spam", agressividade → permission_state = cooling_off
    """
    tipo_lower = tipo_objecao.lower() if tipo_objecao else ""
    mensagem_lower = mensagem.lower()

    # Tipo explícito
    if tipo_lower == "opt_out":
        return True

    # Keywords de opt-out (pedido explícito para parar)
    opt_out_keywords = [
        "não me procure",
        "para de me mandar",
        "não quero mais receber",
        "me tire da lista",
        "remove meu número",
        "não manda mais",
        "para de mandar",
        "me remove",
        "tire meu contato",
        "para de me ligar",
        "não me ligue mais",
        "não me mande mais",
        "me deixa em paz",
        "não quero mais contato",
        "apaga meu contato",
        "deleta meu número",
    ]

    for keyword in opt_out_keywords:
        if keyword in mensagem_lower:
            return True

    return False


def is_handoff_required(tipo_objecao: str, mensagem: str) -> bool:
    """
    Verifica se requer handoff imediato para humano.

    Retorna True para:
    - Objeção GRAVE
    - Pedido explícito de humano
    - Ameaças
    - Agressividade
    """
    severity = map_severity(tipo_objecao, None, mensagem)
    return severity == ObjectionSeverity.GRAVE
