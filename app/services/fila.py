"""
Servico de fila de mensagens agendadas.

Sprint 23 E01 - Adiciona suporte a outcome detalhado.
Sprint 36 - T01.1: Timeout para mensagens travadas
Sprint 36 - T01.2: Cancelar mensagens antigas
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, TYPE_CHECKING
import logging

from app.services.supabase import supabase

if TYPE_CHECKING:
    from app.services.guardrails import SendOutcome

logger = logging.getLogger(__name__)


class FilaService:
    """Gerencia fila de mensagens a enviar."""

    async def enfileirar(
        self,
        cliente_id: str,
        conteudo: str,
        tipo: str,
        conversa_id: str = None,
        prioridade: int = 5,
        agendar_para: datetime = None,
        metadata: dict = None
    ) -> Optional[dict]:
        """Adiciona mensagem à fila."""
        data = {
            "cliente_id": cliente_id,
            "conversa_id": conversa_id,
            "conteudo": conteudo,
            "tipo": tipo,
            "prioridade": prioridade,
            "status": "pendente",
            "tentativas": 0,
            "max_tentativas": 3,
            "agendar_para": (agendar_para or datetime.now(timezone.utc)).isoformat(),
            "metadata": metadata or {}
        }

        response = (
            supabase.table("fila_mensagens")
            .insert(data)
            .execute()
        )

        if response.data:
            logger.info(f"Mensagem enfileirada para {cliente_id}: {tipo}")
            return response.data[0]
        return None

    async def obter_proxima(self) -> Optional[dict]:
        """
        Obtém próxima mensagem para processar.

        Considera:
        - Status pendente
        - Agendamento <= agora
        - Maior prioridade primeiro
        """
        agora = datetime.now(timezone.utc).isoformat()

        # Buscar próxima disponível
        response = (
            supabase.table("fila_mensagens")
            .select("*, clientes(telefone, primeiro_nome)")
            .eq("status", "pendente")
            .lte("agendar_para", agora)
            .order("prioridade", desc=True)
            .order("created_at")
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        mensagem = response.data[0]

        # Marcar como processando
        supabase.table("fila_mensagens").update({
            "status": "processando",
            "processando_desde": agora
        }).eq("id", mensagem["id"]).execute()

        return mensagem

    async def marcar_enviada(self, mensagem_id: str) -> bool:
        """Marca mensagem como enviada com sucesso."""
        response = (
            supabase.table("fila_mensagens")
            .update({
                "status": "enviada",
                "enviada_em": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", mensagem_id)
            .execute()
        )

        return len(response.data) > 0

    async def registrar_outcome(
        self,
        mensagem_id: str,
        outcome: "SendOutcome",
        outcome_reason_code: Optional[str] = None,
        provider_message_id: Optional[str] = None,
    ) -> bool:
        """
        Registra outcome detalhado de um envio.

        Sprint 23 E01 - Rastreamento completo de resultados.

        Args:
            mensagem_id: ID da mensagem na fila
            outcome: Enum com resultado (SENT, BLOCKED_*, DEDUPED, FAILED_*)
            outcome_reason_code: Codigo detalhado do motivo
            provider_message_id: ID da mensagem no Evolution API (quando SENT)

        Returns:
            True se registrou com sucesso
        """
        now = datetime.now(timezone.utc).isoformat()

        # Determinar status baseado no outcome
        if outcome.value == "SENT" or outcome.value == "BYPASS":
            status = "enviada"
        elif outcome.value.startswith("BLOCKED_") or outcome.value == "DEDUPED":
            status = "bloqueada"
        else:
            status = "erro"

        update_data = {
            "status": status,
            "outcome": outcome.value,
            "outcome_reason_code": outcome_reason_code,
            "outcome_at": now,
        }

        if provider_message_id:
            update_data["provider_message_id"] = provider_message_id

        if status == "enviada":
            update_data["enviada_em"] = now

        response = (
            supabase.table("fila_mensagens")
            .update(update_data)
            .eq("id", mensagem_id)
            .execute()
        )

        if response.data:
            logger.info(
                f"Outcome registrado para {mensagem_id}: {outcome.value}",
                extra={
                    "mensagem_id": mensagem_id,
                    "outcome": outcome.value,
                    "outcome_reason_code": outcome_reason_code,
                }
            )
            return True

        logger.warning(f"Falha ao registrar outcome para {mensagem_id}")
        return False

    async def obter_metricas_fila(self) -> dict:
        """
        Sprint 36 - T01.5: Obtém métricas da fila para monitoramento.

        Returns:
            {
                'pendentes': int,
                'processando': int,
                'erros_ultimas_24h': int,
                'mensagem_mais_antiga_min': float | None,
            }
        """
        from datetime import timedelta

        agora = datetime.now(timezone.utc)
        ontem = (agora - timedelta(hours=24)).isoformat()

        # Contar pendentes
        pendentes = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq("status", "pendente").execute()

        # Contar processando
        processando = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq("status", "processando").execute()

        # Contar erros nas últimas 24h
        erros = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq("status", "erro").gte("updated_at", ontem).execute()

        # Buscar mensagem pendente mais antiga
        mais_antiga = supabase.table("fila_mensagens").select(
            "created_at"
        ).eq("status", "pendente").order(
            "created_at", desc=False
        ).limit(1).execute()

        # Calcular idade em minutos
        idade_minutos = None
        if mais_antiga.data:
            created_at_str = mais_antiga.data[0]["created_at"]
            created_at = datetime.fromisoformat(
                created_at_str.replace("Z", "+00:00")
            )
            idade_minutos = (agora - created_at).total_seconds() / 60

        return {
            "pendentes": pendentes.count or 0,
            "processando": processando.count or 0,
            "erros_ultimas_24h": erros.count or 0,
            "mensagem_mais_antiga_min": idade_minutos,
        }

    async def marcar_erro(self, mensagem_id: str, erro: str) -> bool:
        """Marca erro e agenda retry se possível."""
        # Buscar mensagem atual
        msg_resp = (
            supabase.table("fila_mensagens")
            .select("tentativas, max_tentativas")
            .eq("id", mensagem_id)
            .single()
            .execute()
        )

        if not msg_resp.data:
            return False

        mensagem = msg_resp.data
        nova_tentativa = (mensagem.get("tentativas") or 0) + 1
        max_tentativas = mensagem.get("max_tentativas", 3)

        if nova_tentativa < max_tentativas:
            # Agendar retry com backoff exponencial
            delay = 60 * (2 ** nova_tentativa)  # 2min, 4min, 8min
            novo_agendamento = datetime.now(timezone.utc) + timedelta(seconds=delay)

            supabase.table("fila_mensagens").update({
                "status": "pendente",
                "tentativas": nova_tentativa,
                "erro": erro,
                "agendar_para": novo_agendamento.isoformat(),
                "processando_desde": None
            }).eq("id", mensagem_id).execute()
            
            logger.info(f"Retry agendado para mensagem {mensagem_id} (tentativa {nova_tentativa})")
            return True
        else:
            # Esgotou tentativas
            supabase.table("fila_mensagens").update({
                "status": "erro",
                "tentativas": nova_tentativa,
                "erro": erro
            }).eq("id", mensagem_id).execute()
            
            logger.error(f"Mensagem {mensagem_id} falhou após {nova_tentativa} tentativas")
            return False

    async def resetar_mensagens_travadas(self, timeout_minutos: int = 60) -> int:
        """
        Sprint 36 - T01.1: Reseta mensagens travadas em 'processando'.

        Mensagens em 'processando' por mais de X minutos são resetadas
        para 'pendente' com incremento de tentativas.

        Args:
            timeout_minutos: Tempo máximo em processando (default: 60)

        Returns:
            Número de mensagens resetadas
        """
        agora = datetime.now(timezone.utc)
        limite = (agora - timedelta(minutes=timeout_minutos)).isoformat()

        # Buscar mensagens travadas
        travadas = supabase.table("fila_mensagens").select(
            "id, tentativas, max_tentativas"
        ).eq(
            "status", "processando"
        ).lt(
            "processando_desde", limite
        ).execute()

        if not travadas.data:
            return 0

        resetadas = 0
        for msg in travadas.data:
            tentativas = (msg.get("tentativas") or 0) + 1
            max_tentativas = msg.get("max_tentativas", 3)

            if tentativas >= max_tentativas:
                # Esgotou tentativas - marcar como erro
                supabase.table("fila_mensagens").update({
                    "status": "erro",
                    "tentativas": tentativas,
                    "erro": f"Timeout após {timeout_minutos}min (tentativa {tentativas})",
                    "outcome": "FAILED_TIMEOUT",
                    "outcome_at": agora.isoformat(),
                }).eq("id", msg["id"]).execute()
            else:
                # Ainda tem tentativas - resetar para pendente
                supabase.table("fila_mensagens").update({
                    "status": "pendente",
                    "tentativas": tentativas,
                    "processando_desde": None,
                    "agendar_para": agora.isoformat(),  # Tentar imediatamente
                }).eq("id", msg["id"]).execute()

            resetadas += 1

        if resetadas > 0:
            logger.warning(
                f"[Fila] Resetadas {resetadas} mensagens travadas "
                f"(timeout: {timeout_minutos}min)"
            )

        return resetadas

    async def cancelar_mensagens_antigas(self, max_idade_horas: int = 24) -> int:
        """
        Sprint 36 - T01.2: Cancela mensagens pendentes muito antigas.

        Mensagens pendentes por mais de X horas são canceladas
        automaticamente para evitar envios desatualizados.

        Args:
            max_idade_horas: Idade máxima em horas (default: 24)

        Returns:
            Número de mensagens canceladas
        """
        limite = (
            datetime.now(timezone.utc) - timedelta(hours=max_idade_horas)
        ).isoformat()

        # Atualizar mensagens antigas para cancelada
        result = supabase.table("fila_mensagens").update({
            "status": "cancelada",
            "outcome": "FAILED_EXPIRED",
            "outcome_reason_code": f"expired_after_{max_idade_horas}h",
            "outcome_at": datetime.now(timezone.utc).isoformat(),
        }).eq(
            "status", "pendente"
        ).lt(
            "created_at", limite
        ).execute()

        canceladas = len(result.data) if result.data else 0

        if canceladas > 0:
            logger.warning(
                f"[Fila] Canceladas {canceladas} mensagens antigas "
                f"(> {max_idade_horas}h)"
            )

        return canceladas

    async def obter_estatisticas_completas(self) -> dict:
        """
        Sprint 36 - T01.4: Obtém estatísticas completas da fila.

        Returns:
            {
                'por_status': {status: count},
                'pendentes': int,
                'processando': int,
                'enviadas_ultima_hora': int,
                'erros_ultima_hora': int,
                'tempo_medio_processamento_ms': float,
                'mensagem_mais_antiga_min': float | None,
                'travadas': int,  # processando > 1h
            }
        """
        agora = datetime.now(timezone.utc)
        uma_hora_atras = (agora - timedelta(hours=1)).isoformat()
        uma_hora_atras_processando = (agora - timedelta(hours=1)).isoformat()

        # Contagens por status
        pendentes = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq("status", "pendente").execute()

        processando = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq("status", "processando").execute()

        # Enviadas na última hora
        enviadas = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq("status", "enviada").gte("enviada_em", uma_hora_atras).execute()

        # Erros na última hora
        erros = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq("status", "erro").gte("updated_at", uma_hora_atras).execute()

        # Mensagens travadas (processando > 1h)
        travadas = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq("status", "processando").lt(
            "processando_desde", uma_hora_atras_processando
        ).execute()

        # Mensagem pendente mais antiga
        mais_antiga = supabase.table("fila_mensagens").select(
            "created_at"
        ).eq("status", "pendente").order(
            "created_at", desc=False
        ).limit(1).execute()

        idade_minutos = None
        if mais_antiga.data:
            created_at_str = mais_antiga.data[0]["created_at"]
            created_at = datetime.fromisoformat(
                created_at_str.replace("Z", "+00:00")
            )
            idade_minutos = round((agora - created_at).total_seconds() / 60, 1)

        return {
            "pendentes": pendentes.count or 0,
            "processando": processando.count or 0,
            "enviadas_ultima_hora": enviadas.count or 0,
            "erros_ultima_hora": erros.count or 0,
            "mensagem_mais_antiga_min": idade_minutos,
            "travadas": travadas.count or 0,
        }


fila_service = FilaService()


# Funções de compatibilidade (mantidas para não quebrar código existente)
async def enfileirar_mensagem(
    cliente_id: str,
    conversa_id: str,
    conteudo: str,
    tipo: str = "lembrete",
    prioridade: int = 5,
    agendar_para: datetime = None,
    metadata: dict = None
) -> Optional[dict]:
    """Enfileira mensagem (wrapper para compatibilidade)."""
    return await fila_service.enfileirar(
        cliente_id=cliente_id,
        conteudo=conteudo,
        tipo=tipo,
        conversa_id=conversa_id,
        prioridade=prioridade,
        agendar_para=agendar_para,
        metadata=metadata
    )


async def buscar_mensagens_pendentes(limite: int = 10) -> list[dict]:
    """Busca mensagens pendentes (wrapper para compatibilidade)."""
    agora = datetime.now(timezone.utc).isoformat()

    response = (
        supabase.table("fila_mensagens")
        .select("*")
        .eq("status", "pendente")
        .lte("agendar_para", agora)
        .order("prioridade", desc=True)
        .order("agendar_para")
        .limit(limite)
        .execute()
    )

    return response.data or []


async def marcar_como_enviada(mensagem_id: str) -> bool:
    """Marca mensagem como enviada (wrapper para compatibilidade)."""
    return await fila_service.marcar_enviada(mensagem_id)


async def cancelar_mensagem(mensagem_id: str) -> bool:
    """
    Cancela mensagem pendente.

    Args:
        mensagem_id: ID da mensagem

    Returns:
        True se cancelou
    """
    response = (
        supabase.table("fila_mensagens")
        .update({"status": "cancelada"})
        .eq("id", mensagem_id)
        .eq("status", "pendente")
        .execute()
    )

    return len(response.data) > 0
