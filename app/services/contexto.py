"""
Servico para montagem de contexto do agente.
"""
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.services.interacao import carregar_historico, formatar_historico_para_llm
from app.config.especialidades import obter_config_especialidade
from app.services.redis import cache_get_json, cache_set_json
from app.services.supabase import supabase
from app.services.memoria import enriquecer_contexto_com_memorias
from app.core.config import DatabaseConfig

logger = logging.getLogger(__name__)

# Dias da semana em portugues
DIAS_SEMANA = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]


def formatar_contexto_medico(medico: dict) -> str:
    """
    Formata informacoes do medico para o prompt.

    Args:
        medico: Dados do medico do banco

    Returns:
        String formatada
    """
    partes = []

    # Nome
    nome = medico.get("primeiro_nome", "")
    if medico.get("sobrenome"):
        nome += f" {medico['sobrenome']}"

    if nome:
        partes.append(f"Nome: {nome}")

    # Titulo
    if medico.get("titulo"):
        partes.append(f"Titulo: {medico['titulo']}")

    # Especialidade
    especialidade_nome = medico.get("especialidade") or medico.get("especialidade_nome")
    if especialidade_nome:
        partes.append(f"Especialidade: {especialidade_nome}")

    # CRM
    if medico.get("crm"):
        crm = medico["crm"]
        if medico.get("estado"):
            crm = f"CRM-{medico['estado']} {crm}"
        partes.append(f"CRM: {crm}")

    # Cidade
    if medico.get("cidade"):
        partes.append(f"Cidade: {medico['cidade']}")

    # Stage
    if medico.get("stage_jornada"):
        partes.append(f"Status: {medico['stage_jornada']}")

    # Preferencias
    if medico.get("preferencias_detectadas"):
        prefs = medico["preferencias_detectadas"]
        if isinstance(prefs, dict):
            if prefs.get("turnos"):
                partes.append(f"Prefere: {', '.join(prefs['turnos'])}")
            if prefs.get("valor_minimo"):
                partes.append(f"Valor minimo: R$ {prefs['valor_minimo']}")

    return "\n".join(partes) if partes else "Medico novo, sem informacoes ainda."


def montar_contexto_especialidade(medico: dict) -> str:
    """
    Monta contexto específico da especialidade.
    
    Args:
        medico: Dados do médico
    
    Returns:
        String com contexto da especialidade ou vazio
    """
    especialidade_nome = medico.get("especialidade") or medico.get("especialidade_nome")
    if not especialidade_nome:
        return ""
    
    config = obter_config_especialidade(especialidade_nome)
    if not config:
        return ""
    
    partes = [
        f"## Informações da Especialidade ({config['nome_display']})",
        f"- Tipos de plantão comuns: {', '.join(config['tipo_plantao'])}",
        f"- Faixa de valor: {config['valor_medio']}",
        f"- Setores: {', '.join(config['vocabulario']['setores'])}",
        f"- Contexto: {config['contexto_extra']}"
    ]
    
    return "\n".join(partes)


async def verificar_handoff_recente(conversa_id: str, horas: int = 24) -> Optional[dict]:
    """
    Verifica se houve handoff resolvido recentemente para a conversa.

    Args:
        conversa_id: ID da conversa
        horas: Janela de tempo para considerar recente (padrao 24h)

    Returns:
        Dados do handoff se encontrado, None caso contrario
    """
    try:
        limite_tempo = (datetime.utcnow() - timedelta(hours=horas)).isoformat()

        response = (
            supabase.table("handoffs")
            .select("*")
            .eq("conversa_id", conversa_id)
            .eq("status", "resolvido")
            .gte("resolvido_em", limite_tempo)
            .order("resolvido_em", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            handoff = response.data[0]
            logger.info(f"Handoff recente encontrado: {handoff['id']}")
            return handoff

        return None

    except Exception as e:
        logger.error(f"Erro ao verificar handoff recente: {e}")
        return None


def formatar_contexto_handoff(handoff: dict) -> str:
    """
    Formata informacoes do handoff recente para o prompt.

    Args:
        handoff: Dados do handoff

    Returns:
        String formatada
    """
    partes = ["ATENCAO: Esta conversa estava com atendimento humano ate pouco tempo."]

    motivo = handoff.get("motivo", "")
    if motivo:
        partes.append(f"Motivo original: {motivo}")

    notas = handoff.get("notas", "")
    if notas:
        partes.append(f"Notas do gestor: {notas}")

    trigger = handoff.get("trigger_type", "")
    if trigger == "sentimento_negativo":
        partes.append("O medico estava irritado - seja extra cuidadosa.")
    elif trigger == "juridico":
        partes.append("Houve questao juridica - evite esse assunto.")

    partes.append("Retome de forma suave, sem mencionar a supervisora.")

    return "\n".join(partes)


def formatar_contexto_vagas(vagas: list[dict], limite: int = 3) -> str:
    """
    Formata vagas disponiveis para o prompt.

    Args:
        vagas: Lista de vagas do banco
        limite: Maximo de vagas a mostrar

    Returns:
        String formatada
    """
    if not vagas:
        return "Nenhuma vaga disponivel no momento."

    linhas = []
    for v in vagas[:limite]:
        hospital = v.get("hospitais", {}).get("nome", "Hospital")
        data = v.get("data", "")
        periodo = v.get("periodos", {}).get("nome", "")
        valor = v.get("valor") or 0
        setor = v.get("setores", {}).get("nome", "")
        vaga_id = v.get("id", "")

        linha = f"- [{vaga_id[:8]}] {hospital}, {data}, {periodo}"
        if setor:
            linha += f", {setor}"
        if valor:
            linha += f", R$ {valor:,.0f}"

        linhas.append(linha)

    return "\n".join(linhas)


async def carregar_diretrizes_ativas() -> dict:
    """
    Carrega diretrizes ativas do briefing.

    Returns:
        Dict com diretrizes por tipo
    """
    try:
        response = (
            supabase.table("diretrizes")
            .select("tipo, conteudo")
            .eq("ativo", True)
            .order("prioridade", desc=True)
            .execute()
        )

        diretrizes = {}
        for d in response.data or []:
            diretrizes[d["tipo"]] = d["conteudo"]

        return diretrizes

    except Exception as e:
        logger.error(f"Erro ao carregar diretrizes: {e}")
        return {}


def formatar_contexto_diretrizes(diretrizes: dict) -> str:
    """
    Formata diretrizes ativas para o prompt.

    Args:
        diretrizes: Dict com diretrizes por tipo

    Returns:
        String formatada
    """
    if not diretrizes:
        return ""

    partes = ["## Diretrizes do Gestor (PRIORIDADE MAXIMA)"]

    if diretrizes.get("foco_semana"):
        partes.append(f"\n**Foco:**\n{diretrizes['foco_semana']}")

    if diretrizes.get("tom_semana"):
        partes.append(f"\n**Tom:**\n{diretrizes['tom_semana']}")

    if diretrizes.get("margem_negociacao"):
        partes.append(f"\n**Margem de Negociacao:** Pode oferecer ate {diretrizes['margem_negociacao']}% a mais")

    if diretrizes.get("observacoes"):
        partes.append(f"\n**Observacoes:**\n{diretrizes['observacoes']}")

    partes.append("\nSiga essas diretrizes como prioridade maxima.")

    return "\n".join(partes)


async def montar_contexto_completo(
    medico: dict,
    conversa: dict,
    vagas: list[dict] = None,
    mensagem_atual: str = None
) -> dict:
    """
    Monta contexto completo para o agente.

    Args:
        medico: Dados do medico
        conversa: Dados da conversa
        vagas: Lista de vagas disponiveis (opcional)
        mensagem_atual: Mensagem atual do medico (para busca RAG)

    Returns:
        Dict com todos os contextos formatados
    """
    # Cache de partes estáticas do contexto
    cache_key = f"contexto:medico:{medico.get('id')}"
    cached_estatico = await cache_get_json(cache_key)

    if cached_estatico:
        contexto_medico_str = cached_estatico.get("medico", "")
        contexto_especialidade_str = cached_estatico.get("especialidade", "")
    else:
        # Montar partes estáticas
        contexto_medico_str = formatar_contexto_medico(medico)
        contexto_especialidade_str = montar_contexto_especialidade(medico)

        # Salvar no cache
        await cache_set_json(cache_key, {
            "medico": contexto_medico_str,
            "especialidade": contexto_especialidade_str
        }, DatabaseConfig.CACHE_TTL_CONTEXTO)

    # Partes dinâmicas sempre buscam (não cachear)
    historico_raw = await carregar_historico(conversa["id"], limite=10)
    historico = formatar_historico_para_llm(historico_raw)

    # Verificar se e primeira mensagem
    primeira_msg = len(historico_raw) == 0

    # Data/hora atual para calculo de lembretes
    agora = datetime.now()
    dia_semana = DIAS_SEMANA[agora.weekday()]

    # Verificar se houve handoff recente (retorno de atendimento humano)
    contexto_handoff = ""
    handoff_recente = await verificar_handoff_recente(conversa["id"])
    if handoff_recente:
        contexto_handoff = formatar_contexto_handoff(handoff_recente)

    # Carregar diretrizes do briefing (S7.E7.5)
    diretrizes = await carregar_diretrizes_ativas()
    contexto_diretrizes = formatar_contexto_diretrizes(diretrizes)

    # Buscar memorias relevantes via RAG (Sprint 8 - Epic 02)
    contexto_memorias = ""
    if mensagem_atual and medico.get("id"):
        try:
            contexto_memorias = await enriquecer_contexto_com_memorias(
                cliente_id=medico["id"],
                mensagem_atual=mensagem_atual
            )
            if contexto_memorias:
                logger.debug(f"Memorias RAG carregadas para medico {medico['id']}")
        except Exception as e:
            logger.warning(f"Erro ao carregar memorias RAG: {e}")

    return {
        "medico": contexto_medico_str,
        "especialidade": contexto_especialidade_str,
        "historico": historico,
        "historico_raw": historico_raw,
        "vagas": formatar_contexto_vagas(vagas) if vagas else "",
        "primeira_msg": primeira_msg,
        "controlled_by": conversa.get("controlled_by", "ai"),
        "data_hora_atual": agora.strftime("%Y-%m-%d %H:%M"),
        "dia_semana": dia_semana,
        "handoff_recente": contexto_handoff,
        "diretrizes": contexto_diretrizes,
        "memorias": contexto_memorias,  # Sprint 8 - RAG
    }
