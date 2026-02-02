"""
Serviço para gerenciamento de campanhas de primeiro contato.

DEPRECATION WARNING (Sprint 35 - Debt Cleanup):
=====================================
Este módulo contém código LEGADO que será removido em futuras sprints.

MIGRAÇÃO RECOMENDADA:
- Para criar/gerenciar campanhas: use `app.services.campanhas.campanha_repository`
- Para executar campanhas: use `app.services.campanhas.campanha_executor`
- Para tipos/enums: use `app.services.campanhas.types`

FUNÇÕES DEPRECATED:
- `criar_campanha_piloto()` - usa tabela/colunas legadas
- `executar_campanha()` - usa tabela `envios_campanha` (removida)
- `controlador_envio` - usa tabela `envios_campanha` (removida)

FUNÇÕES MIGRADAS (ainda funcionais):
- `criar_envios_campanha()` - atualizada para usar nomes de colunas corretos
- `enviar_mensagem_prospeccao()` - funcional mas usa `envios_campanha` para registro

Histórico:
- Sprint 23 E03: Tabela `envios_campanha` deprecated
- Sprint 35: Módulo `app.services.campanhas` criado com nova arquitetura
"""
import asyncio
import logging
import warnings
from datetime import datetime, timedelta
from typing import Optional

from app.core.timezone import agora_brasilia, agora_utc
from app.services.supabase import supabase
from app.services.outbound import send_outbound_message, criar_contexto_campanha
from app.core.piloto_config import piloto_config
from app.fragmentos.mensagens import formatar_primeiro_contato
from app.services.abertura import obter_abertura, obter_abertura_texto

logger = logging.getLogger(__name__)


class ControladorEnvio:
    """Controla rate limiting de envios."""

    async def pode_enviar_primeiro_contato(self) -> bool:
        """
        Verifica se pode enviar primeiro contato agora.

        DEPRECATED: Esta funcao usa a tabela legada envios_campanha.
        Use campaign_sends_repo para queries unificadas.
        """
        warnings.warn(
            "pode_enviar_primeiro_contato usa tabela legada envios_campanha",
            DeprecationWarning,
            stacklevel=2
        )
        agora = agora_brasilia()

        # Verificar horário
        if agora.hour < piloto_config.HORA_INICIO or agora.hour >= piloto_config.HORA_FIM:
            return False

        # Verificar dia da semana (seg-sex)
        if agora.weekday() >= 5:
            return False

        # Contar envios do dia - DEPRECATED: usar campaign_sends
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

        # Verificar último envio - DEPRECATED: usar campaign_sends
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
        agora = agora_brasilia()

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
    """
    Cria campanha de primeiro contato para piloto.

    DEPRECATED: Esta função usa colunas legadas (tipo, mensagem_template, config)
    e a tabela `envios_campanha` que foi removida.

    Use `app.services.campanhas.campanha_repository.criar()` para criar campanhas.
    """
    warnings.warn(
        "criar_campanha_piloto() usa colunas legadas e tabela removida. "
        "Use campanha_repository.criar() do módulo app.services.campanhas",
        DeprecationWarning,
        stacklevel=2
    )
    from app.fragmentos.mensagens import MENSAGEM_PRIMEIRO_CONTATO

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

    DEPRECATED: Esta função usa a tabela `envios_campanha` que foi removida.

    Use `app.services.campanhas.campanha_executor.executar()` para executar campanhas.

    Processa um envio por vez, aguardando intervalo.
    """
    warnings.warn(
        "executar_campanha() usa tabela envios_campanha que foi removida. "
        "Use campanha_executor.executar() do módulo app.services.campanhas",
        DeprecationWarning,
        stacklevel=2
    )
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
            # Formatar mensagem
            mensagem = formatar_primeiro_contato(medico)

            # GUARDRAIL: Verificar antes de enviar
            ctx = criar_contexto_campanha(
                cliente_id=medico["id"],
                campaign_id=campanha_id,
            )
            result = await send_outbound_message(
                telefone=medico["telefone"],
                texto=mensagem,
                ctx=ctx,
                simular_digitacao=True,
            )

            if result.blocked:
                logger.info(f"Envio bloqueado para {medico.get('primeiro_nome', 'N/A')}: {result.block_reason}")
                supabase.table("envios_campanha").update({
                    "status": "bloqueado",
                    "erro": f"Guardrail: {result.block_reason}"
                }).eq("id", envio["id"]).execute()
                continue

            if not result.success:
                raise Exception(result.error)

            # Atualizar envio
            supabase.table("envios_campanha").update({
                "status": "enviado",
                "enviado_em": agora_utc().isoformat()
            }).eq("id", envio["id"]).execute()

            # Marcar médico
            supabase.table("clientes").update({
                "primeiro_contato_em": agora_utc().isoformat()
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


async def criar_envios_campanha(campanha_id: str):
    """
    Cria envios para todos os destinatários da campanha.
    
    Esta função é usada pelo sistema de campanhas automatizadas.
    """
    from app.services.segmentacao import segmentacao_service
    from app.services.fila import fila_service
    
    campanha_resp = (
        supabase.table("campanhas")
        .select("*")
        .eq("id", campanha_id)
        .single()
        .execute()
    )

    if not campanha_resp.data:
        logger.error(f"Campanha {campanha_id} não encontrada")
        return

    campanha = campanha_resp.data
    audience_filters = campanha.get("audience_filters", {})

    # Montar filtros
    filtros = {}
    if audience_filters.get("especialidades"):
        filtros["especialidade"] = audience_filters["especialidades"][0]
    if audience_filters.get("regioes"):
        filtros["regiao"] = audience_filters["regioes"][0]

    # Buscar destinatários
    destinatarios = await segmentacao_service.buscar_segmento(filtros, limite=10000)

    # Sprint 44 T01.5: Filtrar opted-out ANTES de enfileirar
    # Isso evita envio de mensagens para médicos que pediram para sair
    destinatarios_filtrados = [
        d for d in destinatarios
        if not d.get("opted_out") and not d.get("optado_saida")
    ]

    opted_out_count = len(destinatarios) - len(destinatarios_filtrados)
    if opted_out_count > 0:
        logger.info(
            f"Campanha {campanha_id}: {opted_out_count} destinatários filtrados por opt-out"
        )

    destinatarios = destinatarios_filtrados

    # Criar envio para cada destinatário
    tipo_campanha = campanha.get("tipo_campanha", "campanha")

    for dest in destinatarios:
        # Gerar mensagem baseada no tipo de campanha
        if tipo_campanha == "discovery":
            # Discovery: usar aberturas dinâmicas para variedade
            mensagem = await obter_abertura_texto(
                cliente_id=dest["id"],
                nome=dest.get("primeiro_nome", "")
            )
        else:
            # Outros tipos: usar corpo como template
            corpo = campanha.get("corpo", "")
            if "{nome}" in corpo or "{especialidade}" in corpo:
                mensagem = corpo.format(
                    nome=dest.get("primeiro_nome", ""),
                    especialidade=dest.get("especialidade_nome", "médico")
                )
            else:
                mensagem = corpo

        # Enfileirar
        await fila_service.enfileirar(
            cliente_id=dest["id"],
            conteudo=mensagem,
            tipo=tipo_campanha,
            prioridade=3,  # Prioridade baixa para campanhas
            metadata={"campanha_id": str(campanha_id)}
        )

    # Atualizar contagem
    supabase.table("campanhas").update({
        "enviados": len(destinatarios)
    }).eq("id", campanha_id).execute()
    
    logger.info(f"Enfileirados {len(destinatarios)} envios para campanha {campanha_id}")


async def enviar_mensagem_prospeccao(
    cliente_id: str,
    telefone: str,
    nome: str,
    campanha_id: str = None,
    usar_aberturas_variadas: bool = True
) -> dict:
    """
    Envia mensagem de prospeccao com abertura variada.

    Args:
        cliente_id: ID do medico
        telefone: Telefone do medico
        nome: Nome do medico
        campanha_id: ID da campanha (opcional)
        usar_aberturas_variadas: Se usa sistema de variacoes

    Returns:
        Resultado do envio
    """
    from app.services.agente import enviar_mensagens_sequencia
    from app.services.guardrails import check_outbound_guardrails, OutboundContext, OutboundChannel, OutboundMethod, ActorType

    # GUARDRAIL: Verificar ANTES de gerar texto ou qualquer operacao
    ctx = OutboundContext(
        cliente_id=cliente_id,
        actor_type=ActorType.SYSTEM,
        channel=OutboundChannel.JOB,
        method=OutboundMethod.CAMPAIGN,
        is_proactive=True,
        campaign_id=campanha_id,
    )
    guardrail_result = await check_outbound_guardrails(ctx)

    if guardrail_result.is_blocked:
        logger.warning(
            f"Prospeccao bloqueada para {cliente_id}: {guardrail_result.reason_code}"
        )
        return {
            "success": False,
            "blocked": True,
            "block_reason": guardrail_result.reason_code,
            "block_details": guardrail_result.details,
        }

    try:
        if usar_aberturas_variadas:
            # Obter abertura personalizada (evita repeticao)
            mensagens = await obter_abertura(
                cliente_id=cliente_id,
                nome=nome
            )

            logger.info(
                f"Prospeccao com abertura variada para {nome}: "
                f"{len(mensagens)} mensagens"
            )
        else:
            # Usar template fixo antigo
            medico = {"primeiro_nome": nome}
            texto = formatar_primeiro_contato(medico)
            mensagens = [texto]

        # Enviar em sequencia com timing natural
        # Sprint 18.1 P0: Reusar ctx do check para garantir soberania guardrail
        from app.services.outbound import criar_contexto_campanha
        envio_ctx = criar_contexto_campanha(
            cliente_id=cliente_id,
            campaign_id=campanha_id or "prospeccao_manual",
        )
        resultados = await enviar_mensagens_sequencia(
            telefone=telefone,
            mensagens=mensagens,
            ctx=envio_ctx,
        )

        # Registrar envio se tem campanha
        if campanha_id:
            try:
                supabase.table("envios_campanha").insert({
                    "campanha_id": campanha_id,
                    "cliente_id": cliente_id,
                    "status": "enviado",
                    "tipo": "primeiro_contato",
                    "enviado_em": agora_utc().isoformat(),
                    "metadata": {
                        "mensagens_enviadas": len(mensagens),
                        "abertura_variada": usar_aberturas_variadas
                    }
                }).execute()
            except Exception as e:
                logger.warning(f"Erro ao registrar envio: {e}")

        return {
            "success": True,
            "mensagens_enviadas": len(mensagens),
            "primeira_mensagem": mensagens[0] if mensagens else None,
            "resultados": resultados
        }

    except Exception as e:
        logger.error(f"Erro ao enviar prospeccao para {cliente_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

