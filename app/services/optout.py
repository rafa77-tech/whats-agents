"""
Serviço de detecção e processamento de opt-out.
Permite que médicos solicitem parar de receber mensagens.
"""
import logging
import re
from typing import Tuple

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Padrões de opt-out (case insensitive)
# Normalizados para funcionar sem acentos
PADROES_OPTOUT = [
    r'\bpara\b.*\bmensag',        # "para de mandar mensagem"
    r'\bnao\b.*\bquer.*\breceb',  # "não quero receber"
    r'\bremov.*\blista',          # "remove da lista"
    r'\bsai\s*fora\b',            # "sai fora"
    r'\bnao\b.*\bmand.*\bmais',   # "não me mande mais"
    r'\bpare\b',                  # "pare"
    r'\bstop\b',                  # "STOP"
    r'\bdesinscrever\b',          # "desinscrever"
    r'\bcancelar?\b.*\benvio',    # "cancelar envio"
    r'\bbloque(ar|ia)?\b',        # "bloquear"
    r'\bnao\b.*\binteress',       # "não tenho interesse"
    r'\bchega\b',                 # "chega"
    r'\bpara\b.*\bme\b.*\bcontatar', # "para de me contatar"
    r'\bdesist[oi]',              # "desisto"
]


def _normalizar_texto(texto: str) -> str:
    """
    Normaliza texto removendo acentos para matching mais robusto.
    """
    return (
        texto.lower()
        .replace('ã', 'a').replace('á', 'a').replace('â', 'a').replace('à', 'a')
        .replace('é', 'e').replace('ê', 'e').replace('è', 'e')
        .replace('í', 'i').replace('î', 'i').replace('ì', 'i')
        .replace('ó', 'o').replace('ô', 'o').replace('õ', 'o').replace('ò', 'o')
        .replace('ú', 'u').replace('û', 'u').replace('ù', 'u')
        .replace('ç', 'c')
    )


def detectar_optout(texto: str) -> Tuple[bool, str]:
    """
    Detecta se mensagem indica desejo de opt-out.

    Args:
        texto: Texto da mensagem

    Returns:
        (is_optout, padrao_detectado)
    """
    if not texto:
        return False, ""

    texto_normalizado = _normalizar_texto(texto)

    for padrao in PADROES_OPTOUT:
        if re.search(padrao, texto_normalizado):
            logger.info(f"Opt-out detectado: padrao '{padrao}' em '{texto[:50]}'")
            return True, padrao

    return False, ""


async def processar_optout(cliente_id: str, telefone: str, motivo: str = "") -> bool:
    """
    Processa opt-out: atualiza banco e prepara confirmação.

    Args:
        cliente_id: ID do médico
        telefone: Telefone do médico
        motivo: Mensagem que triggou o opt-out

    Returns:
        True se processado com sucesso
    """
    from datetime import datetime

    try:
        # Atualizar status do médico
        update_data = {
            "opted_out": True,
            "opted_out_at": datetime.utcnow().isoformat(),
        }

        if motivo:
            update_data["opted_out_reason"] = motivo[:200]  # Limitar tamanho

        response = (
            supabase.table("clientes")
            .update(update_data)
            .eq("id", cliente_id)
            .execute()
        )

        logger.info(f"Opt-out processado para cliente {cliente_id}")
        return True

    except Exception as e:
        logger.error(f"Erro ao processar opt-out: {e}")
        return False


async def verificar_opted_out(cliente_id: str) -> bool:
    """
    Verifica se cliente fez opt-out.

    Args:
        cliente_id: ID do médico

    Returns:
        True se fez opt-out
    """
    try:
        response = (
            supabase.table("clientes")
            .select("opted_out")
            .eq("id", cliente_id)
            .execute()
        )

        if response.data:
            return response.data[0].get("opted_out", False) or False
        return False

    except Exception as e:
        logger.error(f"Erro ao verificar opt-out: {e}")
        return False


# Mensagem de confirmação de opt-out (tom casual da Júlia)
MENSAGEM_CONFIRMACAO_OPTOUT = """Entendi! Removido da lista

Nao vou mais te enviar mensagens.

Se mudar de ideia, é so me chamar aqui!"""


async def pode_enviar_proativo(cliente_id: str) -> Tuple[bool, str]:
    """
    Verifica se pode enviar mensagem proativa para cliente.

    Args:
        cliente_id: ID do médico

    Returns:
        (pode_enviar, motivo)
    """
    if await verificar_opted_out(cliente_id):
        return False, "Cliente fez opt-out"

    return True, "OK"
