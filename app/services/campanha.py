"""
Serviço para gerenciamento de campanhas de primeiro contato.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.services.supabase import supabase
from app.services.whatsapp import enviar_com_digitacao
from app.core.piloto_config import piloto_config
from app.templates.mensagens import formatar_primeiro_contato

logger = logging.getLogger(__name__)


class ControladorEnvio:
    """Controla rate limiting de envios."""

    async def pode_enviar_primeiro_contato(self) -> bool:
        """Verifica se pode enviar primeiro contato agora."""
        agora = datetime.now()

        # Verificar horário
        if agora.hour < piloto_config.HORA_INICIO or agora.hour >= piloto_config.HORA_FIM:
            return False

        # Verificar dia da semana (seg-sex)
        if agora.weekday() >= 5:
            return False

        # Contar envios do dia
        inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        envios_resp = (
            supabase.table("envios_campanha")
            .select("id", count="exact")
            .eq("tipo", "primeiro_contato")
            .gte("created_at", inicio_dia)
            .execute()
        )

        envios_hoje = envios_resp.count or 0

        if envios_hoje >= piloto_config.MAX_PRIMEIROS_CONTATOS_DIA:
            return False

        # Verificar último envio
        ultimo_resp = (
            supabase.table("envios_campanha")
            .select("created_at")
            .eq("tipo", "primeiro_contato")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if ultimo_resp.data:
            ultimo_dt = datetime.fromisoformat(ultimo_resp.data[0]["created_at"].replace("Z", "+00:00"))
            diferenca = (agora - ultimo_dt.replace(tzinfo=None)).total_seconds()
            if diferenca < piloto_config.INTERVALO_ENTRE_ENVIOS_SEGUNDOS:
                return False

        return True

    async def proximo_horario_disponivel(self) -> datetime:
        """Retorna próximo horário disponível para envio."""
        agora = datetime.now()

        # Se fora do horário, ir para próximo dia útil às 8h
        if agora.hour >= piloto_config.HORA_FIM:
            proximo = agora + timedelta(days=1)
            proximo = proximo.replace(hour=piloto_config.HORA_INICIO, minute=0, second=0, microsecond=0)
        elif agora.hour < piloto_config.HORA_INICIO:
            proximo = agora.replace(hour=piloto_config.HORA_INICIO, minute=0, second=0, microsecond=0)
        else:
            proximo = agora + timedelta(seconds=piloto_config.INTERVALO_ENTRE_ENVIOS_SEGUNDOS)

        # Pular fim de semana
        while proximo.weekday() >= 5:
            proximo += timedelta(days=1)
            proximo = proximo.replace(hour=piloto_config.HORA_INICIO, minute=0, second=0, microsecond=0)

        return proximo


controlador_envio = ControladorEnvio()


async def criar_campanha_piloto() -> dict:
    """Cria campanha de primeiro contato para piloto."""
    from app.templates.mensagens import MENSAGEM_PRIMEIRO_CONTATO

    # Buscar médicos do piloto que ainda não foram contactados
    medicos_resp = (
        supabase.table("clientes")
        .select("id")
        .contains("tags", ["piloto_v1"])
        .is_("primeiro_contato_em", "null")
        .execute()
    )

    medicos_piloto = medicos_resp.data or []

    # Verificar se já existe campanha ativa
    campanha_existente_resp = (
        supabase.table("campanhas")
        .select("*")
        .eq("tipo", "primeiro_contato")
        .eq("status", "ativa")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if campanha_existente_resp.data:
        logger.warning("Já existe uma campanha ativa de primeiro contato")
        return campanha_existente_resp.data[0]

    campanha_resp = (
        supabase.table("campanhas")
        .insert({
            "nome": "Piloto V1 - Primeiro Contato",
            "tipo": "primeiro_contato",
            "status": "ativa",
            "total_destinatarios": len(medicos_piloto),
            "mensagem_template": MENSAGEM_PRIMEIRO_CONTATO,
            "config": {
                "piloto": True,
                "max_por_dia": piloto_config.MAX_PRIMEIROS_CONTATOS_DIA,
                "intervalo_segundos": piloto_config.INTERVALO_ENTRE_ENVIOS_SEGUNDOS
            }
        })
        .execute()
    )

    campanha = campanha_resp.data[0]

    # Criar envios pendentes
    for medico in medicos_piloto:
        supabase.table("envios_campanha").insert({
            "campanha_id": campanha["id"],
            "cliente_id": medico["id"],
            "status": "pendente",
            "tipo": "primeiro_contato"
        }).execute()

    logger.info(f"Campanha criada: {campanha['id']} com {len(medicos_piloto)} destinatários")
    return campanha


async def executar_campanha(campanha_id: str):
    """
    Executa campanha respeitando rate limiting.

    Processa um envio por vez, aguardando intervalo.
    """
    while True:
        # Verificar se pode enviar
        if not await controlador_envio.pode_enviar_primeiro_contato():
            proximo = await controlador_envio.proximo_horario_disponivel()
            logger.info(f"Aguardando próximo horário: {proximo}")
            await asyncio.sleep(60)  # Checar a cada minuto
            continue

        # Buscar próximo envio pendente
        envio_resp = (
            supabase.table("envios_campanha")
            .select("*, clientes(*)")
            .eq("campanha_id", campanha_id)
            .eq("status", "pendente")
            .order("created_at")
            .limit(1)
            .execute()
        )

        if not envio_resp.data:
            logger.info("Campanha concluída - todos enviados")
            break

        envio = envio_resp.data[0]
        medico = envio.get("clientes")

        if not medico:
            logger.error(f"Envio {envio['id']} sem médico associado")
            continue

        try:
            # Formatar e enviar mensagem
            mensagem = formatar_primeiro_contato(medico)
            await enviar_com_digitacao(
                telefone=medico["telefone"],
                texto=mensagem
            )

            # Atualizar envio
            supabase.table("envios_campanha").update({
                "status": "enviado",
                "enviado_em": datetime.utcnow().isoformat()
            }).eq("id", envio["id"]).execute()

            # Marcar médico
            supabase.table("clientes").update({
                "primeiro_contato_em": datetime.utcnow().isoformat()
            }).eq("id", medico["id"]).execute()

            logger.info(f"Primeiro contato enviado para {medico.get('primeiro_nome', 'N/A')}")

        except Exception as e:
            logger.error(f"Erro ao enviar para {medico.get('id', 'N/A')}: {e}")
            supabase.table("envios_campanha").update({
                "status": "erro",
                "erro": str(e)
            }).eq("id", envio["id"]).execute()

        # Aguardar intervalo
        await asyncio.sleep(piloto_config.INTERVALO_ENTRE_ENVIOS_SEGUNDOS)

