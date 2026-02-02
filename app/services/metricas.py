"""
Serviço para coleta de métricas de conversa.
"""
from datetime import datetime
from typing import Optional
import logging

from app.core.timezone import agora_utc
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class MetricasService:
    """Serviço para gerenciar métricas de conversas."""

    async def iniciar_metricas_conversa(self, conversa_id: str) -> dict:
        """Cria registro de métricas para nova conversa."""
        try:
            response = (
                supabase.table("metricas_conversa")
                .insert({
                    "conversa_id": conversa_id,
                    "primeira_mensagem_em": agora_utc().isoformat(),
                    "total_mensagens_medico": 0,
                    "total_mensagens_julia": 0,
                    "total_mensagens_humano": 0,
                })
                .execute()
            )
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Erro ao iniciar métricas de conversa: {e}")
            return {}

    async def registrar_mensagem(
        self,
        conversa_id: str,
        origem: str,  # 'medico', 'ai', 'humano'
        tempo_resposta_segundos: Optional[float] = None
    ):
        """Atualiza métricas após cada mensagem."""
        try:
            # Buscar métricas existentes
            response = (
                supabase.table("metricas_conversa")
                .select("*")
                .eq("conversa_id", conversa_id)
                .execute()
            )

            metricas = response.data[0] if response.data else None

            if not metricas:
                metricas = await self.iniciar_metricas_conversa(conversa_id)
                if not metricas:
                    return

            # Atualizar contadores
            atualizacao = {
                "ultima_mensagem_em": agora_utc().isoformat(),
                "updated_at": agora_utc().isoformat()
            }

            if origem == "medico":
                atualizacao["total_mensagens_medico"] = (metricas.get("total_mensagens_medico", 0) or 0) + 1
            elif origem == "ai":
                atualizacao["total_mensagens_julia"] = (metricas.get("total_mensagens_julia", 0) or 0) + 1
            elif origem == "humano":
                atualizacao["total_mensagens_humano"] = (metricas.get("total_mensagens_humano", 0) or 0) + 1

            # Tempo de resposta
            if tempo_resposta_segundos:
                if not metricas.get("tempo_primeira_resposta_segundos"):
                    atualizacao["tempo_primeira_resposta_segundos"] = tempo_resposta_segundos

                # Atualizar média
                total_respostas = (metricas.get("total_mensagens_julia", 0) or 0) + (metricas.get("total_mensagens_humano", 0) or 0)
                if total_respostas > 0:
                    media_atual = metricas.get("tempo_medio_resposta_segundos") or 0
                    nova_media = (media_atual * total_respostas + tempo_resposta_segundos) / (total_respostas + 1)
                    atualizacao["tempo_medio_resposta_segundos"] = nova_media
                else:
                    atualizacao["tempo_medio_resposta_segundos"] = tempo_resposta_segundos

            supabase.table("metricas_conversa").update(atualizacao).eq("id", metricas["id"]).execute()

        except Exception as e:
            logger.error(f"Erro ao registrar mensagem nas métricas: {e}")

    async def finalizar_conversa(
        self,
        conversa_id: str,
        resultado: str,
        houve_handoff: bool = False,
        motivo_handoff: Optional[str] = None
    ):
        """Registra métricas finais da conversa."""
        try:
            response = (
                supabase.table("metricas_conversa")
                .select("*")
                .eq("conversa_id", conversa_id)
                .execute()
            )

            metricas = response.data[0] if response.data else None

            if metricas:
                # Calcular duração
                primeira_mensagem = metricas.get("primeira_mensagem_em")
                if primeira_mensagem:
                    inicio = datetime.fromisoformat(primeira_mensagem.replace('Z', '+00:00'))
                    duracao = (agora_utc() - inicio).total_seconds() / 60
                else:
                    duracao = 0

                supabase.table("metricas_conversa").update({
                    "resultado": resultado,
                    "houve_handoff": houve_handoff,
                    "motivo_handoff": motivo_handoff,
                    "duracao_total_minutos": duracao,
                    "updated_at": agora_utc().isoformat()
                }).eq("id", metricas["id"]).execute()

        except Exception as e:
            logger.error(f"Erro ao finalizar métricas de conversa: {e}")


metricas_service = MetricasService()

