"""
Servico de fila de mensagens agendadas.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

from app.services.supabase import supabase

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
