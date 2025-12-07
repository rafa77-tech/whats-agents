"""
Servico de handoff entre IA e Humano.
"""
from datetime import datetime, timedelta
import random
import logging
from typing import Optional

from app.services.supabase import get_supabase
from app.services.slack import notificar_handoff
from app.services.whatsapp import evolution
from app.services.chatwoot import chatwoot_service
from app.services.interacao import salvar_interacao

logger = logging.getLogger(__name__)


# Mensagens de transição para cada tipo de handoff
MENSAGENS_TRANSICAO = {
    "pedido_humano": [
        "Claro! Vou pedir pra minha supervisora te ajudar, ela é ótima 😊",
        "Entendi! Vou chamar alguém da equipe pra falar com vc",
        "Sem problema! Já to passando pro pessoal aqui",
    ],
    "juridico": [
        "Opa, esse assunto é mais delicado, vou passar pra minha supervisora que entende melhor",
        "Entendi a situação. Vou pedir pra alguém mais experiente te ajudar, ok?",
    ],
    "sentimento_negativo": [
        "Entendo sua frustração, vou chamar minha supervisora pra resolver isso da melhor forma",
        "Desculpa por qualquer inconveniente. Vou passar pro pessoal resolver pra vc",
    ],
    "baixa_confianca": [
        "Hmm, deixa eu confirmar uma coisa com o pessoal aqui. Já volto!",
        "Boa pergunta! Vou checar com a equipe e te retorno",
    ],
    "manual": [
        "Oi! Minha supervisora vai continuar o atendimento, tá? 😊",
    ],
}


def obter_mensagem_transicao(tipo: str) -> str:
    """
    Retorna mensagem de transição apropriada para o tipo de handoff.

    Args:
        tipo: Tipo do trigger (pedido_humano, juridico, etc)

    Returns:
        Mensagem de transição
    """
    mensagens = MENSAGENS_TRANSICAO.get(tipo, MENSAGENS_TRANSICAO["manual"])
    return random.choice(mensagens)


async def iniciar_handoff(
    conversa_id: str,
    cliente_id: str,
    motivo: str,
    trigger_type: str = "manual"
) -> Optional[dict]:
    """
    Inicia processo de handoff (IA -> Humano).

    1. Envia mensagem de transição
    2. Atualiza conversa para controlled_by = 'human'
    3. Cria registro de handoff com metadata
    4. Notifica gestor no Slack

    Args:
        conversa_id: ID da conversa
        cliente_id: ID do cliente
        motivo: Motivo do handoff
        trigger_type: Tipo do trigger (pedido_humano, juridico, etc)

    Returns:
        Dados do handoff criado ou None se erro
    """
    supabase = get_supabase()

    try:
        # Buscar conversa com dados do cliente
        conversa_response = (
            supabase.table("conversations")
            .select("*, clientes(*)")
            .eq("id", conversa_id)
            .single()
            .execute()
        )

        if not conversa_response.data:
            logger.error(f"Conversa {conversa_id} não encontrada")
            return None

        conversa = conversa_response.data
        medico = conversa.get("clientes", {})
        telefone = medico.get("telefone")

        if not telefone:
            logger.error(f"Telefone não encontrado para cliente {cliente_id}")
            return None

        # Calcular metadata da conversa
        interacoes_response = (
            supabase.table("interacoes")
            .select("*")
            .eq("conversation_id", conversa_id)
            .order("created_at", desc=False)
            .execute()
        )

        interacoes = interacoes_response.data if interacoes_response.data else []
        total_interacoes = len(interacoes)
        ultima_mensagem = interacoes[-1].get("conteudo", "") if interacoes else ""

        # Calcular duração da conversa
        duracao_minutos = 0
        if interacoes:
            primeira = datetime.fromisoformat(interacoes[0]["created_at"].replace("Z", "+00:00"))
            ultima = datetime.fromisoformat(interacoes[-1]["created_at"].replace("Z", "+00:00"))
            duracao_minutos = int((ultima - primeira).total_seconds() / 60)

        # 1. Enviar mensagem de transição
        mensagem_transicao = obter_mensagem_transicao(trigger_type)
        
        try:
            await evolution.enviar_mensagem(
                telefone=telefone,
                texto=mensagem_transicao,
                verificar_rate_limit=False  # Mensagem de transição não conta no rate limit
            )
            logger.info(f"Mensagem de transição enviada para {telefone[:8]}...")

            # Salvar mensagem de transição
            await salvar_interacao(
                conversa_id=conversa_id,
                cliente_id=cliente_id,
                tipo="saida",
                conteudo=mensagem_transicao,
                autor_tipo="julia"
            )

            # Sincronizar com Chatwoot
            chatwoot_conversation_id = conversa.get("chatwoot_conversation_id")
            if chatwoot_conversation_id and chatwoot_service.configurado:
                await chatwoot_service.enviar_mensagem(
                    conversation_id=int(chatwoot_conversation_id),
                    content=mensagem_transicao,
                    message_type="outgoing"
                )
                # Adicionar label "humano" no Chatwoot para o gestor ver
                await chatwoot_service.adicionar_label(
                    conversation_id=int(chatwoot_conversation_id),
                    label="humano"
                )
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de transição: {e}")
            # Continua mesmo se falhar

        # 2. Atualizar conversa para controle humano
        supabase.table("conversations").update({
            "controlled_by": "human",
            "escalation_reason": motivo,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", conversa_id).execute()

        logger.info(f"Conversa {conversa_id} atualizada para controle humano")

        # 3. Criar registro de handoff com metadata
        handoff_data = {
            "conversa_id": conversa_id,
            "motivo": motivo,
            "trigger_type": trigger_type,
            "status": "pendente",
        }

        # Adicionar metadata se disponível
        metadata = {}
        if ultima_mensagem:
            metadata["ultima_mensagem"] = ultima_mensagem[:200]  # Limitar tamanho
        if total_interacoes:
            metadata["total_interacoes"] = total_interacoes
        if duracao_minutos:
            metadata["duracao_conversa_minutos"] = duracao_minutos

        if metadata:
            handoff_data["metadata"] = metadata

        response = supabase.table("handoffs").insert(handoff_data).execute()

        if not response.data:
            logger.error("Erro ao criar registro de handoff")
            return None

        handoff = response.data[0]
        logger.info(f"Handoff criado: {handoff['id']}")

        # 4. Notificar gestor no Slack
        try:
            await notificar_handoff(conversa, handoff)
        except Exception as e:
            logger.error(f"Erro ao notificar Slack: {e}")
            # Não falha a operação principal

        return handoff

    except Exception as e:
        logger.error(f"Erro ao iniciar handoff: {e}", exc_info=True)
        return None


async def finalizar_handoff(
    conversa_id: str,
    notas: str = "Gestor removeu label 'humano' no Chatwoot",
    resolvido_por: str = "gestor"
) -> bool:
    """
    Finaliza handoff e retorna controle para IA.

    1. Atualiza conversa para controlled_by = 'ai'
    2. Marca handoff como resolvido com timestamp
    3. Notifica no Slack sobre a resolução
    4. Calcula duração do handoff

    Args:
        conversa_id: ID da conversa
        notas: Observações sobre a resolução
        resolvido_por: Quem resolveu (gestor, sistema, etc)

    Returns:
        True se sucesso
    """
    supabase = get_supabase()

    try:
        # 1. Buscar conversa com dados do cliente para notificação
        conversa_response = (
            supabase.table("conversations")
            .select("*, clientes(*)")
            .eq("id", conversa_id)
            .single()
            .execute()
        )

        if not conversa_response.data:
            logger.error(f"Conversa {conversa_id} não encontrada para finalizar handoff")
            return False

        conversa = conversa_response.data

        # 2. Atualizar conversa para controle IA
        supabase.table("conversations").update({
            "controlled_by": "ai",
            "escalation_reason": None,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", conversa_id).execute()

        logger.info(f"Conversa {conversa_id} retornada para controle IA")

        # 2.1 Remover label "humano" do Chatwoot (se existir)
        chatwoot_conversation_id = conversa.get("chatwoot_conversation_id")
        if chatwoot_conversation_id and chatwoot_service.configurado:
            try:
                await chatwoot_service.remover_label(
                    conversation_id=int(chatwoot_conversation_id),
                    label="humano"
                )
            except Exception as e:
                logger.warning(f"Erro ao remover label do Chatwoot: {e}")

        # 3. Atualizar handoffs pendentes como resolvidos
        handoff_response = (
            supabase.table("handoffs")
            .update({
                "status": "resolvido",
                "resolvido_em": datetime.utcnow().isoformat(),
                "resolvido_por": resolvido_por,
                "notas": notas
            })
            .eq("conversa_id", conversa_id)
            .eq("status", "pendente")
            .execute()
        )

        # 4. Notificar Slack se tiver handoff resolvido
        if handoff_response.data:
            handoff = handoff_response.data[0]
            logger.info(f"Handoff {handoff['id']} marcado como resolvido")

            # Notificar no Slack
            try:
                from app.services.slack import notificar_handoff_resolvido
                await notificar_handoff_resolvido(conversa, handoff)
            except Exception as e:
                logger.error(f"Erro ao notificar Slack sobre handoff resolvido: {e}")
        else:
            logger.warning(f"Nenhum handoff pendente encontrado para conversa {conversa_id}")

        return True

    except Exception as e:
        logger.error(f"Erro ao finalizar handoff: {e}", exc_info=True)
        return False


async def resolver_handoff(
    handoff_id: str,
    resolvido_por: Optional[str] = None,
    notas: Optional[str] = None
) -> Optional[dict]:
    """
    Marca handoff como resolvido.

    Args:
        handoff_id: ID do handoff
        resolvido_por: ID do usuário que resolveu (opcional)
        notas: Notas sobre a resolução (opcional)

    Returns:
        Dados do handoff atualizado ou None se erro
    """
    supabase = get_supabase()

    try:
        update_data = {
            "status": "resolvido",
            "resolvido_em": datetime.utcnow().isoformat()
        }

        if resolvido_por:
            update_data["resolvido_por"] = resolvido_por
        if notas:
            update_data["notas"] = notas

        response = (
            supabase.table("handoffs")
            .update(update_data)
            .eq("id", handoff_id)
            .execute()
        )

        if not response.data:
            logger.error(f"Handoff {handoff_id} não encontrado")
            return None

        handoff = response.data[0]
        logger.info(f"Handoff {handoff_id} marcado como resolvido")

        return handoff

    except Exception as e:
        logger.error(f"Erro ao resolver handoff: {e}", exc_info=True)
        return None


async def listar_handoffs_pendentes() -> list:
    """
    Lista todos os handoffs pendentes.

    Returns:
        Lista de handoffs pendentes com dados da conversa e cliente
    """
    supabase = get_supabase()

    try:
        # Buscar handoffs pendentes
        handoffs_response = (
            supabase.table("handoffs")
            .select("*")
            .eq("status", "pendente")
            .order("created_at", desc=False)
            .execute()
        )

        handoffs = handoffs_response.data if handoffs_response.data else []

        # Buscar dados das conversas e clientes para cada handoff
        resultado = []
        for handoff in handoffs:
            conversa_id = handoff.get("conversa_id")
            if conversa_id:
                conversa_response = (
                    supabase.table("conversations")
                    .select("*, clientes(*)")
                    .eq("id", conversa_id)
                    .single()
                    .execute()
                )
                if conversa_response.data:
                    handoff["conversations"] = conversa_response.data
            resultado.append(handoff)

        return resultado

        return response.data if response.data else []

    except Exception as e:
        logger.error(f"Erro ao listar handoffs pendentes: {e}")
        return []


async def obter_metricas_handoff(periodo_dias: int = 30) -> dict:
    """
    Retorna métricas de handoff do período.

    Args:
        periodo_dias: Número de dias para calcular métricas

    Returns:
        Dict com métricas agregadas
    """
    supabase = get_supabase()

    try:
        data_inicio = (datetime.now() - timedelta(days=periodo_dias)).isoformat()

        response = (
            supabase.table("handoffs")
            .select("trigger_type, status, created_at, resolvido_em")
            .gte("created_at", data_inicio)
            .execute()
        )

        handoffs = response.data if response.data else []

        # Agrupar por tipo
        por_tipo = {}
        for h in handoffs:
            tipo = h.get("trigger_type", "manual")
            if tipo not in por_tipo:
                por_tipo[tipo] = 0
            por_tipo[tipo] += 1

        # Calcular tempo médio de resolução
        resolvidos = [h for h in handoffs if h.get("status") == "resolvido" and h.get("resolvido_em")]
        tempo_medio_minutos = 0

        if resolvidos:
            tempos = []
            for h in resolvidos:
                try:
                    criado = datetime.fromisoformat(h["created_at"].replace("Z", "+00:00"))
                    resolvido = datetime.fromisoformat(h["resolvido_em"].replace("Z", "+00:00"))
                    minutos = (resolvido - criado).total_seconds() / 60
                    tempos.append(minutos)
                except Exception:
                    pass

            if tempos:
                tempo_medio_minutos = int(sum(tempos) / len(tempos))

        return {
            "total": len(handoffs),
            "pendentes": len([h for h in handoffs if h.get("status") == "pendente"]),
            "resolvidos": len(resolvidos),
            "por_tipo": por_tipo,
            "tempo_medio_resolucao_minutos": tempo_medio_minutos
        }

    except Exception as e:
        logger.error(f"Erro ao obter métricas de handoff: {e}")
        return {
            "total": 0,
            "pendentes": 0,
            "resolvidos": 0,
            "por_tipo": {},
            "tempo_medio_resolucao_minutos": 0
        }


async def verificar_handoff_ativo(conversa_id: str) -> bool:
    """
    Verifica se ha handoff ativo para a conversa.

    Args:
        conversa_id: ID da conversa

    Returns:
        True se conversa esta sob controle humano
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("conversations")
            .select("controlled_by")
            .eq("id", conversa_id)
            .execute()
        )

        if response.data:
            return response.data[0].get("controlled_by") == "human"

        return False

    except Exception as e:
        logger.error(f"Erro ao verificar handoff: {e}")
        return False
