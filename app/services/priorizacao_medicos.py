"""
Serviço de Priorização de Médicos para Ofertas.

Sprint 32 E07 - Algoritmo de seleção de médicos para ofertas automáticas.

Critérios de priorização (em ordem):
1. Histórico positivo (já fechou plantão antes)
2. Qualification score alto
3. Nunca foi contatado (novo na base)
4. Tempo desde última interação (nem muito recente, nem muito antigo)
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES DE PESOS
# =============================================================================

# Pesos para cálculo de score de priorização
PESO_HISTORICO_POSITIVO = 100  # Já fechou plantão
PESO_QUALIFICATION_SCORE = 50  # Multiplicado pelo score (0-1)
PESO_NUNCA_CONTATADO = 30  # Novo na base
PESO_TEMPO_IDEAL = 20  # Entre 7-30 dias desde último contato
PESO_ESPECIALIDADE_MATCH = 40  # Match exato de especialidade

# Intervalo ideal de contato (nem muito recente, nem muito antigo)
DIAS_CONTATO_MINIMO = 7  # Não contatar se contatou nos últimos 7 dias
DIAS_CONTATO_IDEAL_MAX = 30  # Priorizar quem foi contatado há menos de 30 dias


# =============================================================================
# FUNÇÕES DE PRIORIZAÇÃO
# =============================================================================

async def priorizar_medicos(
    medicos: list[dict],
    vaga: dict,
    limite: int = 5
) -> list[dict]:
    """
    Prioriza lista de médicos para uma vaga específica.

    Args:
        medicos: Lista de médicos candidatos
        vaga: Dados da vaga
        limite: Máximo de médicos a retornar

    Returns:
        Lista de médicos ordenados por prioridade
    """
    if not medicos:
        return []

    # Calcular score para cada médico
    medicos_com_score = []

    for medico in medicos:
        score = await calcular_score_priorizacao(medico, vaga)
        medicos_com_score.append({
            **medico,
            "_prioridade_score": score,
        })

    # Ordenar por score (maior primeiro)
    medicos_ordenados = sorted(
        medicos_com_score,
        key=lambda m: m["_prioridade_score"],
        reverse=True
    )

    # Remover score interno antes de retornar
    resultado = []
    for medico in medicos_ordenados[:limite]:
        medico_limpo = {k: v for k, v in medico.items() if not k.startswith("_")}
        resultado.append(medico_limpo)

    return resultado


async def calcular_score_priorizacao(
    medico: dict,
    vaga: dict
) -> float:
    """
    Calcula score de priorização para um médico.

    Args:
        medico: Dados do médico
        vaga: Dados da vaga

    Returns:
        Score numérico (maior = mais prioritário)
    """
    score = 0.0

    # 1. Histórico positivo (já fechou plantão)
    historico = await verificar_historico_positivo(medico["id"])
    if historico["tem_historico"]:
        score += PESO_HISTORICO_POSITIVO
        # Bonus se fechou com mesmo hospital
        if historico.get("mesmo_hospital"):
            score += PESO_HISTORICO_POSITIVO * 0.5

    # 2. Qualification score
    qualification = medico.get("qualification_score") or 0
    score += PESO_QUALIFICATION_SCORE * qualification

    # 3. Nunca foi contatado (novo)
    total_interacoes = medico.get("total_interacoes") or 0
    if total_interacoes == 0:
        score += PESO_NUNCA_CONTATADO

    # 4. Tempo desde último contato
    ultima_msg = medico.get("ultima_mensagem_data")
    if ultima_msg:
        try:
            ultima = datetime.fromisoformat(ultima_msg.replace("Z", "+00:00"))
            dias = (datetime.now(timezone.utc) - ultima).days

            # Penalizar se contatou muito recentemente
            if dias < DIAS_CONTATO_MINIMO:
                score -= 50  # Penalidade por contato recente

            # Bonus se está no intervalo ideal
            elif dias <= DIAS_CONTATO_IDEAL_MAX:
                score += PESO_TEMPO_IDEAL

        except (ValueError, TypeError):
            pass

    # 5. Match de especialidade
    esp_medico = (medico.get("especialidade") or "").lower()
    esp_vaga = ""
    if vaga.get("especialidades") and isinstance(vaga["especialidades"], dict):
        esp_vaga = (vaga["especialidades"].get("nome") or "").lower()

    if esp_medico and esp_vaga and esp_medico == esp_vaga:
        score += PESO_ESPECIALIDADE_MATCH
    elif esp_medico and esp_vaga and (esp_medico in esp_vaga or esp_vaga in esp_medico):
        score += PESO_ESPECIALIDADE_MATCH * 0.5  # Match parcial

    return score


async def verificar_historico_positivo(
    cliente_id: str,
    hospital_id: Optional[str] = None
) -> dict:
    """
    Verifica se médico tem histórico positivo de plantões.

    Args:
        cliente_id: ID do médico
        hospital_id: Opcional - verificar se fechou no mesmo hospital

    Returns:
        Dict com informações do histórico
    """
    try:
        # Buscar vagas fechadas/realizadas pelo médico
        response = (
            supabase.table("vagas")
            .select("id, hospital_id, status")
            .eq("cliente_id", cliente_id)
            .in_("status", ["reservada", "fechada", "realizada"])
            .is_("deleted_at", "null")
            .limit(10)
            .execute()
        )

        vagas = response.data or []

        resultado = {
            "tem_historico": len(vagas) > 0,
            "total_plantoes": len(vagas),
            "mesmo_hospital": False,
        }

        # Verificar se fechou no mesmo hospital
        if hospital_id and vagas:
            for vaga in vagas:
                if vaga.get("hospital_id") == hospital_id:
                    resultado["mesmo_hospital"] = True
                    break

        return resultado

    except Exception as e:
        logger.error(f"Erro ao verificar histórico: {e}")
        return {"tem_historico": False, "total_plantoes": 0}


# =============================================================================
# FUNÇÕES DE FILTRO
# =============================================================================

async def filtrar_medicos_contatados_recentemente(
    medicos: list[dict],
    dias_minimo: int = DIAS_CONTATO_MINIMO
) -> list[dict]:
    """
    Remove médicos que foram contatados recentemente.

    Args:
        medicos: Lista de médicos
        dias_minimo: Não retornar médicos contatados há menos de X dias

    Returns:
        Lista filtrada
    """
    data_limite = datetime.now(timezone.utc) - timedelta(days=dias_minimo)

    filtrados = []
    for medico in medicos:
        ultima_msg = medico.get("ultima_mensagem_data")

        if not ultima_msg:
            filtrados.append(medico)
            continue

        try:
            ultima = datetime.fromisoformat(ultima_msg.replace("Z", "+00:00"))
            if ultima < data_limite:
                filtrados.append(medico)
        except (ValueError, TypeError):
            filtrados.append(medico)

    return filtrados


async def filtrar_medicos_em_conversa_ativa(
    medicos: list[dict]
) -> list[dict]:
    """
    Remove médicos que estão em conversa ativa.

    Args:
        medicos: Lista de médicos

    Returns:
        Lista filtrada (sem médicos em conversa)
    """
    if not medicos:
        return []

    cliente_ids = [m["id"] for m in medicos]

    try:
        # Buscar conversas ativas
        response = (
            supabase.table("conversations")
            .select("cliente_id")
            .in_("cliente_id", cliente_ids)
            .eq("status", "active")
            .execute()
        )

        clientes_em_conversa = {c["cliente_id"] for c in response.data or []}

        return [m for m in medicos if m["id"] not in clientes_em_conversa]

    except Exception as e:
        logger.error(f"Erro ao filtrar conversas ativas: {e}")
        return medicos


async def filtrar_medicos_na_fila(
    medicos: list[dict],
    tipo_mensagem: Optional[str] = None
) -> list[dict]:
    """
    Remove médicos que já estão na fila de mensagens.

    Args:
        medicos: Lista de médicos
        tipo_mensagem: Opcional - filtrar por tipo específico

    Returns:
        Lista filtrada
    """
    if not medicos:
        return []

    cliente_ids = [m["id"] for m in medicos]

    try:
        query = (
            supabase.table("fila_mensagens")
            .select("cliente_id")
            .in_("cliente_id", cliente_ids)
            .in_("status", ["pendente", "processando"])
        )

        if tipo_mensagem:
            query = query.eq("tipo", tipo_mensagem)

        response = query.execute()

        clientes_na_fila = {c["cliente_id"] for c in response.data or []}

        return [m for m in medicos if m["id"] not in clientes_na_fila]

    except Exception as e:
        logger.error(f"Erro ao filtrar fila: {e}")
        return medicos


# =============================================================================
# FUNÇÃO COMPLETA DE SELEÇÃO
# =============================================================================

async def selecionar_medicos_para_oferta(
    vaga: dict,
    limite: int = 5,
    aplicar_filtros: bool = True
) -> list[dict]:
    """
    Seleciona e prioriza médicos para uma oferta de vaga.

    Executa todos os passos:
    1. Busca médicos compatíveis
    2. Aplica filtros (recentes, conversa ativa, fila)
    3. Prioriza por score

    Args:
        vaga: Dados da vaga
        limite: Máximo de médicos a retornar
        aplicar_filtros: Se deve aplicar filtros de exclusão

    Returns:
        Lista de médicos priorizados
    """
    from app.services.gatilhos_autonomos import buscar_medicos_compativeis_para_vaga

    # Buscar candidatos iniciais
    medicos = await buscar_medicos_compativeis_para_vaga(vaga, limite=limite * 3)

    if not medicos:
        logger.debug(f"Nenhum médico compatível para vaga {vaga.get('id')}")
        return []

    logger.debug(f"Encontrados {len(medicos)} médicos compatíveis iniciais")

    if aplicar_filtros:
        # Filtrar médicos contatados recentemente
        medicos = await filtrar_medicos_contatados_recentemente(medicos)
        logger.debug(f"Após filtro de contato recente: {len(medicos)} médicos")

        # Filtrar médicos em conversa ativa
        medicos = await filtrar_medicos_em_conversa_ativa(medicos)
        logger.debug(f"Após filtro de conversa ativa: {len(medicos)} médicos")

        # Filtrar médicos já na fila de oferta
        medicos = await filtrar_medicos_na_fila(medicos, tipo_mensagem="oferta")
        logger.debug(f"Após filtro de fila: {len(medicos)} médicos")

    # Priorizar
    medicos_priorizados = await priorizar_medicos(medicos, vaga, limite)

    logger.info(
        f"Selecionados {len(medicos_priorizados)} médicos para vaga {vaga.get('id')}"
    )

    return medicos_priorizados
