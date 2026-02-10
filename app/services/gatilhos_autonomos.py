"""
Serviço de Gatilhos Automáticos para Julia Autônoma.

Sprint 32 E05 - Implementa gatilhos que disparam ações automáticas:
- Discovery: Médicos não-enriquecidos
- Oferta: Vagas com furo de escala (< 20 dias)
- Reativação: Médicos inativos (> 60 dias)
- Feedback: Plantões realizados recentemente

IMPORTANTE: Esses gatilhos SÓ executam se PILOT_MODE=False.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.services.supabase import supabase
from app.workers.pilot_mode import (
    skip_if_pilot,
    AutonomousFeature,
    require_pilot_disabled,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES DE CONFIGURAÇÃO
# =============================================================================

# Discovery: Médicos sem especialidade definida são considerados "não-enriquecidos"
DISCOVERY_CAMPOS_ENRIQUECIMENTO = ["especialidade", "cidade", "estado"]

# Oferta: Vagas com menos de X dias para a data são consideradas urgentes
OFERTA_THRESHOLD_DIAS = 20

# Reativação: Médicos sem interação há mais de X dias
REATIVACAO_DIAS_INATIVO = 60

# Feedback: Plantões realizados nos últimos X dias
FEEDBACK_DIAS_RECENTES = 2

# Limites por execução (para não sobrecarregar)
LIMITE_DISCOVERY_POR_CICLO = 50
LIMITE_OFERTA_POR_CICLO = 30
LIMITE_REATIVACAO_POR_CICLO = 20
LIMITE_FEEDBACK_POR_CICLO = 20


# =============================================================================
# DISCOVERY AUTOMÁTICO
# =============================================================================


async def buscar_medicos_nao_enriquecidos(limite: int = LIMITE_DISCOVERY_POR_CICLO) -> list[dict]:
    """
    Busca médicos que precisam de enriquecimento (Discovery).

    Critérios:
    - Telefone validado (status_telefone = 'validado')
    - Sem especialidade OU sem cidade/estado
    - Não optou out
    - Não está em conversa ativa

    Args:
        limite: Máximo de médicos a retornar

    Returns:
        Lista de médicos para Discovery
    """
    try:
        response = (
            supabase.table("clientes")
            .select("id, telefone, primeiro_nome, especialidade, cidade, estado")
            .eq("status_telefone", "validado")
            .eq("opt_out", False)
            .is_("opted_out", "null")
            .is_("especialidade", "null")
            .is_("deleted_at", "null")
            .limit(limite)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar médicos para discovery: {e}")
        return []


@skip_if_pilot(AutonomousFeature.DISCOVERY)
async def executar_discovery_automatico() -> dict:
    """
    Executa Discovery automático para médicos não-enriquecidos.

    Só executa se PILOT_MODE=False.

    Returns:
        Estatísticas de execução
    """
    stats = {
        "encontrados": 0,
        "enfileirados": 0,
        "erros": 0,
    }

    medicos = await buscar_medicos_nao_enriquecidos()
    stats["encontrados"] = len(medicos)

    if not medicos:
        logger.debug("Nenhum médico para Discovery automático")
        return stats

    logger.info(f"Discovery automático: {len(medicos)} médicos encontrados")

    from app.services.fila import fila_service

    for medico in medicos:
        try:
            # Enfileirar mensagem de discovery
            await fila_service.enfileirar(
                cliente_id=medico["id"],
                conteudo="__DISCOVERY_AUTOMATICO__",  # Marcador para o agente
                tipo="discovery",
                prioridade=4,  # Baixa prioridade
                metadata={
                    "gatilho": "discovery_automatico",
                    "campos_faltantes": _identificar_campos_faltantes(medico),
                },
            )
            stats["enfileirados"] += 1

        except Exception as e:
            logger.error(f"Erro ao enfileirar discovery para {medico['id']}: {e}")
            stats["erros"] += 1

    logger.info(
        f"Discovery automático concluído: {stats['enfileirados']} enfileirados, "
        f"{stats['erros']} erros"
    )

    return stats


def _identificar_campos_faltantes(medico: dict) -> list[str]:
    """Identifica quais campos de enriquecimento estão faltando."""
    faltantes = []
    for campo in DISCOVERY_CAMPOS_ENRIQUECIMENTO:
        if not medico.get(campo):
            faltantes.append(campo)
    return faltantes


# =============================================================================
# OFERTA AUTOMÁTICA (FURO DE ESCALA)
# =============================================================================


async def buscar_vagas_urgentes(
    threshold_dias: int = OFERTA_THRESHOLD_DIAS, limite: int = LIMITE_OFERTA_POR_CICLO
) -> list[dict]:
    """
    Busca vagas que precisam de médico urgentemente.

    Critérios:
    - Status = 'aberta' (sem médico confirmado)
    - Data da vaga < threshold_dias a partir de hoje
    - Data da vaga > hoje (não passou)

    Args:
        threshold_dias: Considerar vagas com menos de X dias
        limite: Máximo de vagas a retornar

    Returns:
        Lista de vagas urgentes ordenadas por data
    """
    try:
        hoje = datetime.now(timezone.utc).date()
        data_limite = hoje + timedelta(days=threshold_dias)

        response = (
            supabase.table("vagas")
            .select(
                "id, data, valor, status, especialidade_id, hospital_id, "
                "hospitais(nome), especialidades(nome)"
            )
            .eq("status", "aberta")
            .gte("data", hoje.isoformat())
            .lte("data", data_limite.isoformat())
            .is_("deleted_at", "null")
            .order("data", desc=False)  # Mais urgentes primeiro
            .limit(limite)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar vagas urgentes: {e}")
        return []


async def buscar_medicos_compativeis_para_vaga(vaga: dict, limite: int = 5) -> list[dict]:
    """
    Busca médicos compatíveis com uma vaga específica.

    Critérios:
    - Mesma especialidade
    - Telefone validado
    - Não optou out
    - Não está em conversa ativa sobre esta vaga

    Args:
        vaga: Dados da vaga
        limite: Máximo de médicos a retornar

    Returns:
        Lista de médicos compatíveis
    """
    from app.services.priorizacao_medicos import priorizar_medicos

    try:
        especialidade_id = vaga.get("especialidade_id")
        if not especialidade_id:
            return []

        # Buscar especialidade nome para match
        response = (
            supabase.table("clientes")
            .select("id, telefone, primeiro_nome, especialidade, qualification_score")
            .eq("status_telefone", "validado")
            .eq("opt_out", False)
            .is_("opted_out", "null")
            .is_("deleted_at", "null")
            .limit(limite * 3)  # Buscar mais para ter margem após priorização
            .execute()
        )

        medicos = response.data or []

        # Filtrar por especialidade (match parcial)
        esp_nome = (
            vaga.get("especialidades", {}).get("nome", "").lower()
            if vaga.get("especialidades")
            else ""
        )
        if esp_nome:
            medicos = [
                m
                for m in medicos
                if m.get("especialidade") and esp_nome in m["especialidade"].lower()
            ]

        # Priorizar médicos
        medicos_priorizados = await priorizar_medicos(medicos=medicos, vaga=vaga, limite=limite)

        return medicos_priorizados

    except Exception as e:
        logger.error(f"Erro ao buscar médicos compatíveis: {e}")
        return []


@skip_if_pilot(AutonomousFeature.OFERTA)
async def executar_oferta_automatica() -> dict:
    """
    Executa Oferta automática para vagas urgentes.

    Só executa se PILOT_MODE=False.

    Returns:
        Estatísticas de execução
    """
    stats = {
        "vagas_encontradas": 0,
        "ofertas_enfileiradas": 0,
        "medicos_contatados": 0,
        "erros": 0,
    }

    vagas = await buscar_vagas_urgentes()
    stats["vagas_encontradas"] = len(vagas)

    if not vagas:
        logger.debug("Nenhuma vaga urgente para oferta automática")
        return stats

    logger.info(f"Oferta automática: {len(vagas)} vagas urgentes encontradas")

    from app.services.fila import fila_service

    for vaga in vagas:
        try:
            medicos = await buscar_medicos_compativeis_para_vaga(vaga)

            if not medicos:
                logger.debug(f"Nenhum médico compatível para vaga {vaga['id']}")
                continue

            for medico in medicos:
                try:
                    # Enfileirar oferta
                    await fila_service.enfileirar(
                        cliente_id=medico["id"],
                        conteudo="__OFERTA_AUTOMATICA__",  # Marcador para o agente
                        tipo="oferta",
                        prioridade=2,  # Alta prioridade
                        metadata={
                            "gatilho": "oferta_automatica",
                            "vaga_id": vaga["id"],
                            "vaga_data": vaga["data"],
                            "vaga_valor": vaga.get("valor"),
                            "hospital_nome": vaga.get("hospitais", {}).get("nome")
                            if vaga.get("hospitais")
                            else None,
                        },
                    )
                    stats["ofertas_enfileiradas"] += 1
                    stats["medicos_contatados"] += 1

                except Exception as e:
                    logger.error(f"Erro ao enfileirar oferta para {medico['id']}: {e}")
                    stats["erros"] += 1

        except Exception as e:
            logger.error(f"Erro ao processar vaga {vaga['id']}: {e}")
            stats["erros"] += 1

    logger.info(
        f"Oferta automática concluída: {stats['ofertas_enfileiradas']} ofertas, "
        f"{stats['medicos_contatados']} médicos, {stats['erros']} erros"
    )

    return stats


# =============================================================================
# REATIVAÇÃO AUTOMÁTICA
# =============================================================================


async def buscar_medicos_inativos(
    dias_inativo: int = REATIVACAO_DIAS_INATIVO, limite: int = LIMITE_REATIVACAO_POR_CICLO
) -> list[dict]:
    """
    Busca médicos inativos que precisam de reativação.

    Critérios:
    - Última interação > X dias atrás
    - Telefone validado
    - Não optou out
    - Já teve pelo menos uma interação (não é novo)

    Args:
        dias_inativo: Considerar inativo após X dias
        limite: Máximo de médicos a retornar

    Returns:
        Lista de médicos inativos
    """
    try:
        data_limite = datetime.now(timezone.utc) - timedelta(days=dias_inativo)

        response = (
            supabase.table("clientes")
            .select("id, telefone, primeiro_nome, ultima_mensagem_data, total_interacoes")
            .eq("status_telefone", "validado")
            .eq("opt_out", False)
            .is_("opted_out", "null")
            .is_("deleted_at", "null")
            .lt("ultima_mensagem_data", data_limite.isoformat())
            .gt("total_interacoes", 0)  # Já interagiu antes
            .order("ultima_mensagem_data", desc=False)  # Mais antigos primeiro
            .limit(limite)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar médicos inativos: {e}")
        return []


@skip_if_pilot(AutonomousFeature.REATIVACAO)
async def executar_reativacao_automatica() -> dict:
    """
    Executa Reativação automática para médicos inativos.

    Só executa se PILOT_MODE=False.

    Returns:
        Estatísticas de execução
    """
    stats = {
        "encontrados": 0,
        "enfileirados": 0,
        "erros": 0,
    }

    medicos = await buscar_medicos_inativos()
    stats["encontrados"] = len(medicos)

    if not medicos:
        logger.debug("Nenhum médico para reativação automática")
        return stats

    logger.info(f"Reativação automática: {len(medicos)} médicos inativos encontrados")

    from app.services.fila import fila_service

    for medico in medicos:
        try:
            dias_sem_contato = None
            if medico.get("ultima_mensagem_data"):
                ultima = datetime.fromisoformat(
                    medico["ultima_mensagem_data"].replace("Z", "+00:00")
                )
                dias_sem_contato = (datetime.now(timezone.utc) - ultima).days

            # Enfileirar reativação
            await fila_service.enfileirar(
                cliente_id=medico["id"],
                conteudo="__REATIVACAO_AUTOMATICA__",  # Marcador para o agente
                tipo="reativacao",
                prioridade=3,  # Prioridade média
                metadata={
                    "gatilho": "reativacao_automatica",
                    "dias_inativo": dias_sem_contato,
                    "total_interacoes_anteriores": medico.get("total_interacoes"),
                },
            )
            stats["enfileirados"] += 1

        except Exception as e:
            logger.error(f"Erro ao enfileirar reativação para {medico['id']}: {e}")
            stats["erros"] += 1

    logger.info(
        f"Reativação automática concluída: {stats['enfileirados']} enfileirados, "
        f"{stats['erros']} erros"
    )

    return stats


# =============================================================================
# FEEDBACK AUTOMÁTICO
# =============================================================================


async def buscar_plantoes_realizados_recentes(
    dias: int = FEEDBACK_DIAS_RECENTES, limite: int = LIMITE_FEEDBACK_POR_CICLO
) -> list[dict]:
    """
    Busca plantões realizados recentemente para pedir feedback.

    Critérios:
    - Status = 'realizada'
    - realizada_em nos últimos X dias
    - Médico associado (cliente_id não nulo)
    - Feedback ainda não solicitado

    Args:
        dias: Considerar plantões dos últimos X dias
        limite: Máximo de plantões a retornar

    Returns:
        Lista de vagas realizadas com dados do médico
    """
    try:
        data_limite = datetime.now(timezone.utc) - timedelta(days=dias)

        response = (
            supabase.table("vagas")
            .select(
                "id, data, realizada_em, cliente_id, "
                "hospitais(nome), especialidades(nome), "
                "clientes(id, telefone, primeiro_nome, opt_out, opted_out, status_telefone)"
            )
            .eq("status", "realizada")
            .gte("realizada_em", data_limite.isoformat())
            .not_.is_("cliente_id", "null")
            .is_("deleted_at", "null")
            .order("realizada_em", desc=True)
            .limit(limite)
            .execute()
        )

        # Filtrar médicos válidos para feedback
        vagas_validas = []
        for vaga in response.data or []:
            cliente = vaga.get("clientes")
            if not cliente:
                continue
            if cliente.get("opt_out") or cliente.get("opted_out"):
                continue
            if cliente.get("status_telefone") != "validado":
                continue
            vagas_validas.append(vaga)

        return vagas_validas

    except Exception as e:
        logger.error(f"Erro ao buscar plantões para feedback: {e}")
        return []


async def verificar_feedback_ja_solicitado(cliente_id: str, vaga_id: str) -> bool:
    """
    Verifica se feedback já foi solicitado para este plantão.

    Args:
        cliente_id: ID do médico
        vaga_id: ID da vaga

    Returns:
        True se já foi solicitado
    """
    try:
        # Verificar na fila se já tem solicitação pendente ou enviada
        response = (
            supabase.table("fila_mensagens")
            .select("id")
            .eq("cliente_id", cliente_id)
            .eq("tipo", "feedback")
            .contains("metadata", {"vaga_id": vaga_id})
            .limit(1)
            .execute()
        )

        return len(response.data or []) > 0

    except Exception as e:
        logger.error(f"Erro ao verificar feedback solicitado: {e}")
        return False


@skip_if_pilot(AutonomousFeature.FEEDBACK)
async def executar_feedback_automatico() -> dict:
    """
    Executa Feedback automático para plantões realizados.

    Só executa se PILOT_MODE=False.

    Returns:
        Estatísticas de execução
    """
    stats = {
        "plantoes_encontrados": 0,
        "feedbacks_enfileirados": 0,
        "ja_solicitados": 0,
        "erros": 0,
    }

    plantoes = await buscar_plantoes_realizados_recentes()
    stats["plantoes_encontrados"] = len(plantoes)

    if not plantoes:
        logger.debug("Nenhum plantão recente para feedback automático")
        return stats

    logger.info(f"Feedback automático: {len(plantoes)} plantões encontrados")

    from app.services.fila import fila_service

    for plantao in plantoes:
        try:
            cliente = plantao.get("clientes", {})
            cliente_id = cliente.get("id")

            if not cliente_id:
                continue

            # Verificar se já solicitou feedback
            if await verificar_feedback_ja_solicitado(cliente_id, plantao["id"]):
                stats["ja_solicitados"] += 1
                continue

            # Enfileirar feedback
            await fila_service.enfileirar(
                cliente_id=cliente_id,
                conteudo="__FEEDBACK_AUTOMATICO__",  # Marcador para o agente
                tipo="feedback",
                prioridade=3,  # Prioridade média
                metadata={
                    "gatilho": "feedback_automatico",
                    "vaga_id": plantao["id"],
                    "vaga_data": plantao["data"],
                    "hospital_nome": plantao.get("hospitais", {}).get("nome")
                    if plantao.get("hospitais")
                    else None,
                    "realizada_em": plantao.get("realizada_em"),
                },
            )
            stats["feedbacks_enfileirados"] += 1

        except Exception as e:
            logger.error(f"Erro ao enfileirar feedback para plantão {plantao['id']}: {e}")
            stats["erros"] += 1

    logger.info(
        f"Feedback automático concluído: {stats['feedbacks_enfileirados']} enfileirados, "
        f"{stats['ja_solicitados']} já solicitados, {stats['erros']} erros"
    )

    return stats


# =============================================================================
# ORQUESTRADOR PRINCIPAL
# =============================================================================


async def executar_todos_gatilhos() -> dict:
    """
    Executa todos os gatilhos automáticos em sequência.

    Esta função é chamada pelo job scheduler.
    Só executa gatilhos se PILOT_MODE=False.

    Returns:
        Estatísticas consolidadas de todos os gatilhos
    """
    logger.info("Iniciando execução de gatilhos automáticos")

    resultados = {
        "discovery": {},
        "oferta": {},
        "reativacao": {},
        "feedback": {},
        "pilot_mode": not require_pilot_disabled(AutonomousFeature.DISCOVERY),
    }

    # Se em modo piloto, retornar cedo com stats vazias
    if resultados["pilot_mode"]:
        logger.info("Modo piloto ativo - gatilhos automáticos não executados")
        return resultados

    # Executar cada gatilho
    try:
        resultados["discovery"] = await executar_discovery_automatico() or {}
    except Exception as e:
        logger.error(f"Erro no gatilho discovery: {e}")
        resultados["discovery"] = {"erro": str(e)}

    try:
        resultados["oferta"] = await executar_oferta_automatica() or {}
    except Exception as e:
        logger.error(f"Erro no gatilho oferta: {e}")
        resultados["oferta"] = {"erro": str(e)}

    try:
        resultados["reativacao"] = await executar_reativacao_automatica() or {}
    except Exception as e:
        logger.error(f"Erro no gatilho reativação: {e}")
        resultados["reativacao"] = {"erro": str(e)}

    try:
        resultados["feedback"] = await executar_feedback_automatico() or {}
    except Exception as e:
        logger.error(f"Erro no gatilho feedback: {e}")
        resultados["feedback"] = {"erro": str(e)}

    logger.info(f"Gatilhos automáticos concluídos: {resultados}")

    return resultados


# =============================================================================
# FUNÇÕES DE ESTATÍSTICAS
# =============================================================================


async def obter_estatisticas_gatilhos() -> dict:
    """
    Retorna estatísticas atuais dos gatilhos.

    Útil para dashboard e monitoramento.

    Returns:
        Dict com contagens de cada categoria
    """
    stats = {
        "discovery": {
            "pendentes": 0,
            "descricao": "Médicos sem especialidade definida",
        },
        "oferta": {
            "vagas_urgentes": 0,
            "descricao": f"Vagas abertas com menos de {OFERTA_THRESHOLD_DIAS} dias",
        },
        "reativacao": {
            "inativos": 0,
            "descricao": f"Médicos sem contato há mais de {REATIVACAO_DIAS_INATIVO} dias",
        },
        "feedback": {
            "plantoes_recentes": 0,
            "descricao": f"Plantões realizados nos últimos {FEEDBACK_DIAS_RECENTES} dias",
        },
    }

    try:
        # Discovery
        medicos_discovery = await buscar_medicos_nao_enriquecidos(limite=1000)
        stats["discovery"]["pendentes"] = len(medicos_discovery)

        # Oferta
        vagas_urgentes = await buscar_vagas_urgentes(limite=1000)
        stats["oferta"]["vagas_urgentes"] = len(vagas_urgentes)

        # Reativação
        medicos_inativos = await buscar_medicos_inativos(limite=1000)
        stats["reativacao"]["inativos"] = len(medicos_inativos)

        # Feedback
        plantoes = await buscar_plantoes_realizados_recentes(limite=1000)
        stats["feedback"]["plantoes_recentes"] = len(plantoes)

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de gatilhos: {e}")

    return stats
