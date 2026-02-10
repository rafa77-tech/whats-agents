"""
Serviço de Conhecimento de Hospitais.

Sprint 32 E11 - Julia aprende com respostas do gestor.

Quando o gestor responde uma pergunta sobre um hospital,
Julia salva essa informação para não precisar perguntar novamente.

Atributos comuns:
- refeicao: Informações sobre refeitório/alimentação
- estacionamento: Informações sobre estacionamento
- vestiario: Informações sobre vestiário
- wifi: Informações sobre internet
- descanso: Informações sobre área de descanso
- acesso: Como chegar, entrada de médicos
- pagamento: Forma e prazo de pagamento
- contato: Telefone, responsável pela escala
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES - ATRIBUTOS CONHECIDOS
# =============================================================================

ATRIBUTO_REFEICAO = "refeicao"
ATRIBUTO_ESTACIONAMENTO = "estacionamento"
ATRIBUTO_VESTIARIO = "vestiario"
ATRIBUTO_WIFI = "wifi"
ATRIBUTO_DESCANSO = "descanso"
ATRIBUTO_ACESSO = "acesso"
ATRIBUTO_PAGAMENTO = "pagamento"
ATRIBUTO_CONTATO = "contato"
ATRIBUTO_OUTRO = "outro"

ATRIBUTOS_CONHECIDOS = [
    ATRIBUTO_REFEICAO,
    ATRIBUTO_ESTACIONAMENTO,
    ATRIBUTO_VESTIARIO,
    ATRIBUTO_WIFI,
    ATRIBUTO_DESCANSO,
    ATRIBUTO_ACESSO,
    ATRIBUTO_PAGAMENTO,
    ATRIBUTO_CONTATO,
]

# Fontes de conhecimento
FONTE_GESTOR = "gestor"
FONTE_MEDICO = "medico"
FONTE_SISTEMA = "sistema"


# =============================================================================
# FUNÇÕES DE CRUD
# =============================================================================


async def salvar_conhecimento(
    hospital_id: str,
    atributo: str,
    valor: str,
    fonte: str = FONTE_GESTOR,
    criado_por: Optional[str] = None,
    pedido_ajuda_id: Optional[str] = None,
) -> dict:
    """
    Salva ou atualiza conhecimento sobre um hospital.

    Args:
        hospital_id: ID do hospital
        atributo: Tipo de informação (refeicao, estacionamento, etc)
        valor: Conteúdo da informação
        fonte: Origem da informação (gestor, medico, sistema)
        criado_por: Quem forneceu a informação
        pedido_ajuda_id: ID do pedido de ajuda relacionado

    Returns:
        Dict com dados do conhecimento salvo
    """
    try:
        # Normalizar atributo
        atributo_normalizado = _normalizar_atributo(atributo)

        # Verificar se já existe
        existing = (
            supabase.table("conhecimento_hospitais")
            .select("id")
            .eq("hospital_id", hospital_id)
            .eq("atributo", atributo_normalizado)
            .limit(1)
            .execute()
        )

        if existing.data:
            # Atualizar existente
            response = (
                supabase.table("conhecimento_hospitais")
                .update(
                    {
                        "valor": valor,
                        "fonte": fonte,
                        "criado_por": criado_por,
                        "pedido_ajuda_id": pedido_ajuda_id,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", existing.data[0]["id"])
                .execute()
            )

            logger.info(
                f"Conhecimento atualizado: {atributo_normalizado} para hospital {hospital_id}"
            )
        else:
            # Criar novo
            response = (
                supabase.table("conhecimento_hospitais")
                .insert(
                    {
                        "id": str(uuid4()),
                        "hospital_id": hospital_id,
                        "atributo": atributo_normalizado,
                        "valor": valor,
                        "fonte": fonte,
                        "criado_por": criado_por,
                        "pedido_ajuda_id": pedido_ajuda_id,
                    }
                )
                .execute()
            )

            logger.info(f"Conhecimento criado: {atributo_normalizado} para hospital {hospital_id}")

        return response.data[0] if response.data else {}

    except Exception as e:
        logger.error(f"Erro ao salvar conhecimento: {e}")
        raise


async def buscar_conhecimento(
    hospital_id: str,
    atributo: Optional[str] = None,
) -> Optional[dict | list[dict]]:
    """
    Busca conhecimento sobre um hospital.

    Args:
        hospital_id: ID do hospital
        atributo: Atributo específico (opcional)

    Returns:
        Dict com conhecimento ou lista de conhecimentos
    """
    try:
        query = supabase.table("conhecimento_hospitais").select("*").eq("hospital_id", hospital_id)

        if atributo:
            atributo_normalizado = _normalizar_atributo(atributo)
            query = query.eq("atributo", atributo_normalizado)
            response = query.limit(1).execute()
            return response.data[0] if response.data else None

        response = query.execute()
        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar conhecimento: {e}")
        return None if atributo else []


async def listar_conhecimentos_hospital(hospital_id: str) -> list[dict]:
    """
    Lista todos os conhecimentos de um hospital.

    Args:
        hospital_id: ID do hospital

    Returns:
        Lista de conhecimentos
    """
    try:
        response = (
            supabase.table("conhecimento_hospitais")
            .select("*")
            .eq("hospital_id", hospital_id)
            .order("atributo")
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar conhecimentos: {e}")
        return []


async def deletar_conhecimento(
    hospital_id: str,
    atributo: str,
) -> bool:
    """
    Deleta um conhecimento específico.

    Args:
        hospital_id: ID do hospital
        atributo: Atributo a deletar

    Returns:
        True se deletou
    """
    try:
        atributo_normalizado = _normalizar_atributo(atributo)

        response = (
            supabase.table("conhecimento_hospitais")
            .delete()
            .eq("hospital_id", hospital_id)
            .eq("atributo", atributo_normalizado)
            .execute()
        )

        if response.data:
            logger.info(f"Conhecimento deletado: {atributo_normalizado} de hospital {hospital_id}")
            return True

        return False

    except Exception as e:
        logger.error(f"Erro ao deletar conhecimento: {e}")
        return False


# =============================================================================
# FUNÇÕES DE BUSCA AVANÇADA
# =============================================================================


async def buscar_hospitais_com_atributo(
    atributo: str,
    valor_contem: Optional[str] = None,
) -> list[dict]:
    """
    Busca hospitais que têm determinado atributo.

    Args:
        atributo: Tipo de atributo
        valor_contem: Filtrar por valor que contém texto

    Returns:
        Lista de hospitais com o atributo
    """
    try:
        atributo_normalizado = _normalizar_atributo(atributo)

        query = (
            supabase.table("conhecimento_hospitais")
            .select("*, hospitais:hospital_id(id, nome)")
            .eq("atributo", atributo_normalizado)
        )

        if valor_contem:
            query = query.ilike("valor", f"%{valor_contem}%")

        response = query.execute()
        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar hospitais com atributo: {e}")
        return []


async def obter_ficha_hospital(hospital_id: str) -> dict:
    """
    Obtém ficha completa de conhecimentos de um hospital.

    Args:
        hospital_id: ID do hospital

    Returns:
        Dict com todos os conhecimentos organizados
    """
    try:
        # Buscar dados do hospital
        hospital_response = (
            supabase.table("hospitais")
            .select("id, nome, endereco, cidade, estado")
            .eq("id", hospital_id)
            .limit(1)
            .execute()
        )

        hospital = hospital_response.data[0] if hospital_response.data else {}

        # Buscar conhecimentos
        conhecimentos = await listar_conhecimentos_hospital(hospital_id)

        # Organizar em dict
        ficha = {
            "hospital": hospital,
            "conhecimentos": {},
        }

        for c in conhecimentos:
            ficha["conhecimentos"][c["atributo"]] = {
                "valor": c["valor"],
                "fonte": c["fonte"],
                "atualizado_em": c.get("updated_at") or c.get("created_at"),
            }

        return ficha

    except Exception as e:
        logger.error(f"Erro ao obter ficha do hospital: {e}")
        return {"hospital": {}, "conhecimentos": {}}


# =============================================================================
# FUNÇÕES PARA INTEGRAÇÃO COM JULIA
# =============================================================================


async def julia_sabe_sobre_hospital(
    hospital_id: str,
    pergunta: str,
) -> Optional[str]:
    """
    Verifica se Julia sabe responder uma pergunta sobre o hospital.

    Uso no agente:
    ```python
    resposta = await julia_sabe_sobre_hospital(hospital_id, "tem estacionamento?")
    if resposta:
        return resposta  # Julia já sabe
    else:
        # Julia precisa perguntar ao gestor
        await julia_precisa_ajuda(...)
    ```

    Args:
        hospital_id: ID do hospital
        pergunta: Pergunta do médico

    Returns:
        Resposta se souber, None se não souber
    """
    # Detectar atributo baseado na pergunta
    atributo = _detectar_atributo_da_pergunta(pergunta)

    if not atributo:
        return None

    conhecimento = await buscar_conhecimento(hospital_id, atributo)

    if conhecimento and conhecimento.get("valor"):
        return conhecimento["valor"]

    return None


async def julia_aprendeu(
    hospital_id: str,
    pergunta: str,
    resposta_gestor: str,
    pedido_ajuda_id: Optional[str] = None,
    criado_por: Optional[str] = None,
) -> bool:
    """
    Julia aprende com resposta do gestor.

    Uso no agente:
    ```python
    # Após gestor responder
    await julia_aprendeu(
        hospital_id=hospital_id,
        pergunta="tem estacionamento?",
        resposta_gestor="Sim, estacionamento gratuito no subsolo",
    )
    ```

    Args:
        hospital_id: ID do hospital
        pergunta: Pergunta original
        resposta_gestor: Resposta do gestor
        pedido_ajuda_id: ID do pedido de ajuda
        criado_por: ID do gestor

    Returns:
        True se salvou conhecimento
    """
    atributo = _detectar_atributo_da_pergunta(pergunta)

    if not atributo:
        atributo = ATRIBUTO_OUTRO

    try:
        await salvar_conhecimento(
            hospital_id=hospital_id,
            atributo=atributo,
            valor=resposta_gestor,
            fonte=FONTE_GESTOR,
            criado_por=criado_por,
            pedido_ajuda_id=pedido_ajuda_id,
        )
        return True

    except Exception as e:
        logger.error(f"Erro ao salvar aprendizado: {e}")
        return False


async def obter_contexto_hospital(hospital_id: str) -> str:
    """
    Obtém contexto formatado do hospital para injetar no prompt.

    Uso no agente:
    ```python
    contexto = await obter_contexto_hospital(hospital_id)
    # Injetar no prompt da Julia
    ```

    Args:
        hospital_id: ID do hospital

    Returns:
        String formatada com conhecimentos
    """
    conhecimentos = await listar_conhecimentos_hospital(hospital_id)

    if not conhecimentos:
        return ""

    linhas = ["Informações do hospital:"]

    for c in conhecimentos:
        atributo_display = _atributo_para_display(c["atributo"])
        linhas.append(f"- {atributo_display}: {c['valor']}")

    return "\n".join(linhas)


# =============================================================================
# FUNÇÕES INTERNAS
# =============================================================================


def _normalizar_atributo(atributo: str) -> str:
    """Normaliza nome do atributo."""
    atributo_lower = atributo.lower().strip()

    # Mapeamento de sinônimos
    mapeamento = {
        "comida": ATRIBUTO_REFEICAO,
        "alimentacao": ATRIBUTO_REFEICAO,
        "refeitorio": ATRIBUTO_REFEICAO,
        "restaurante": ATRIBUTO_REFEICAO,
        "lanche": ATRIBUTO_REFEICAO,
        "parking": ATRIBUTO_ESTACIONAMENTO,
        "vaga": ATRIBUTO_ESTACIONAMENTO,
        "roupa": ATRIBUTO_VESTIARIO,
        "armario": ATRIBUTO_VESTIARIO,
        "internet": ATRIBUTO_WIFI,
        "rede": ATRIBUTO_WIFI,
        "repouso": ATRIBUTO_DESCANSO,
        "dormitorio": ATRIBUTO_DESCANSO,
        "entrada": ATRIBUTO_ACESSO,
        "endereco": ATRIBUTO_ACESSO,
        "localizacao": ATRIBUTO_ACESSO,
        "pagar": ATRIBUTO_PAGAMENTO,
        "salario": ATRIBUTO_PAGAMENTO,
        "valor": ATRIBUTO_PAGAMENTO,
        "telefone": ATRIBUTO_CONTATO,
        "responsavel": ATRIBUTO_CONTATO,
        "escala": ATRIBUTO_CONTATO,
    }

    if atributo_lower in mapeamento:
        return mapeamento[atributo_lower]

    if atributo_lower in ATRIBUTOS_CONHECIDOS:
        return atributo_lower

    return ATRIBUTO_OUTRO


def _detectar_atributo_da_pergunta(pergunta: str) -> Optional[str]:
    """Detecta atributo baseado na pergunta."""
    pergunta_lower = pergunta.lower()

    # Palavras-chave por atributo
    keywords = {
        ATRIBUTO_REFEICAO: ["refei", "comida", "almo", "janta", "lanche", "cafe", "refeitório"],
        ATRIBUTO_ESTACIONAMENTO: ["estacion", "parking", "carro", "vaga", "garagem"],
        ATRIBUTO_VESTIARIO: ["vestia", "trocar", "roupa", "armario", "chuveiro"],
        ATRIBUTO_WIFI: ["wifi", "internet", "rede", "sinal"],
        ATRIBUTO_DESCANSO: ["descan", "dormir", "repouso", "dormitorio", "quarto"],
        ATRIBUTO_ACESSO: ["chegar", "endere", "entrada", "acesso", "localiza"],
        ATRIBUTO_PAGAMENTO: ["paga", "valor", "salario", "deposito", "pix", "quando recebe"],
        ATRIBUTO_CONTATO: ["telefone", "contato", "responsavel", "escala", "falar com"],
    }

    for atributo, kws in keywords.items():
        for kw in kws:
            if kw in pergunta_lower:
                return atributo

    return None


def _atributo_para_display(atributo: str) -> str:
    """Converte atributo para exibição."""
    display = {
        ATRIBUTO_REFEICAO: "Refeição",
        ATRIBUTO_ESTACIONAMENTO: "Estacionamento",
        ATRIBUTO_VESTIARIO: "Vestiário",
        ATRIBUTO_WIFI: "WiFi/Internet",
        ATRIBUTO_DESCANSO: "Área de descanso",
        ATRIBUTO_ACESSO: "Acesso/Entrada",
        ATRIBUTO_PAGAMENTO: "Pagamento",
        ATRIBUTO_CONTATO: "Contato",
        ATRIBUTO_OUTRO: "Outro",
    }

    return display.get(atributo, atributo.capitalize())
