"""
Serviço de follow-up automático.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from app.services.supabase import supabase
from app.services.fila import fila_service
from app.config.followup import REGRAS_FOLLOWUP

logger = logging.getLogger(__name__)


class FollowupService:
    """Gerencia follow-ups automáticos."""

    async def verificar_followups_pendentes(self) -> List[Dict]:
        """
        Identifica conversas que precisam de follow-up.

        Critérios:
        - Última mensagem foi da Júlia
        - Passou tempo configurado sem resposta
        - Não atingiu max de followups
        """
        pendentes = []

        for tipo, config in REGRAS_FOLLOWUP.items():
            dias = config["dias_ate_followup"]
            data_limite = datetime.now(timezone.utc) - timedelta(days=dias)

            # Buscar conversas ativas controladas pela IA
            conversas_resp = (
                supabase.table("conversations")
                .select("id, cliente_id, status, controlled_by")
                .eq("status", "active")
                .eq("controlled_by", "ai")
                .execute()
            )

            conversas = conversas_resp.data or []

            for conv in conversas:
                # Buscar última interação
                interacoes_resp = (
                    supabase.table("interacoes")
                    .select("origem, created_at")
                    .eq("conversation_id", conv["id"])
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )

                if not interacoes_resp.data:
                    continue

                ultima = interacoes_resp.data[0]

                # Se última foi da Júlia (origem = "julia" ou autor_tipo = "ai")
                origem = ultima.get("origem", "")
                if origem in ["julia", "saida"] or ultima.get("autor_tipo") == "ai":
                    try:
                        created_at = ultima["created_at"]
                        # Normalizar formato de data
                        if created_at.endswith("Z"):
                            created_at = created_at.replace("Z", "+00:00")
                        ultima_data = datetime.fromisoformat(created_at)
                        if ultima_data < data_limite:
                            # Verificar quantos followups já foram enviados
                            # (assumindo que isso está em metadata ou campo separado)
                            pendentes.append({
                                "conversa": conv,
                                "tipo": tipo,
                                "config": config
                            })
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Erro ao processar data: {e}")
                        continue

        return pendentes

    async def enviar_followup(self, conversa_id: str, tipo: str) -> bool:
        """Envia mensagem de follow-up."""
        config = REGRAS_FOLLOWUP.get(tipo)
        if not config:
            logger.warning(f"Tipo de follow-up desconhecido: {tipo}")
            return False

        # Buscar conversa e cliente
        conv_resp = (
            supabase.table("conversations")
            .select("*, clientes(primeiro_nome, telefone)")
            .eq("id", conversa_id)
            .single()
            .execute()
        )

        if not conv_resp.data:
            logger.error(f"Conversa {conversa_id} não encontrada")
            return False

        conv = conv_resp.data
        cliente = conv.get("clientes", {})

        if not cliente:
            logger.error(f"Cliente não encontrado para conversa {conversa_id}")
            return False

        # Escolher mensagem (baseado em quantos já enviou)
        # Por enquanto, usar primeira mensagem (pode ser melhorado)
        followups_enviados = 0  # TODO: buscar do banco
        if followups_enviados >= len(config["mensagens"]):
            logger.info(f"Max followups atingido para conversa {conversa_id}")
            return False

        template = config["mensagens"][followups_enviados]
        mensagem = template.format(
            nome=cliente.get("primeiro_nome", "")
        )

        # Enfileirar
        await fila_service.enfileirar(
            cliente_id=conv["cliente_id"],
            conversa_id=conversa_id,
            conteudo=mensagem,
            tipo="followup",
            prioridade=4,
            metadata={"tipo_followup": tipo}
        )

        # Atualizar contador (assumindo campo followups_enviados)
        # TODO: adicionar campo followups_enviados na tabela conversations se não existir
        logger.info(f"Follow-up enfileirado para conversa {conversa_id}")

        return True


followup_service = FollowupService()

