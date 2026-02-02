"""
Servico de confirmacao de plantao.

Sprint 17 - Fluxo: reservada -> pendente_confirmacao -> realizada/cancelada

Responsabilidades:
- Job horario: transiciona vagas reservadas apos fim do plantao
- Confirmacao: processa acoes do Slack (realizado/nao ocorreu)
- Emissao de business_events em cada transicao

IMPORTANTE: Timezone
- Dados no banco (data, hora_inicio, hora_fim) sao em horario local (America/Sao_Paulo)
- Conversao para UTC so acontece APOS combinar data + hora em SP
- Nunca usar .replace(tzinfo=UTC) diretamente em horarios locais
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from app.services.supabase import supabase
from app.services.business_events.types import BusinessEvent, EventType, EventSource
from app.services.business_events.repository import emit_event

logger = logging.getLogger(__name__)

# Buffer apos fim do plantao para considerar "vencido" (2 horas)
BUFFER_HORAS = 2

# Timezone do Brasil (hospitais operam em horario local)
TZ_SP = ZoneInfo("America/Sao_Paulo")


def calcular_fim_plantao(data: str, hora_inicio: str, hora_fim: str) -> datetime:
    """
    Calcula o datetime real do fim do plantão.

    IMPORTANTE: data/hora no banco são em horário local (America/Sao_Paulo).
    Esta função primeiro cria o datetime em SP, depois converte para UTC.

    Trata plantões noturnos onde hora_fim < hora_inicio
    (ex: 19:00-07:00 significa que termina no dia seguinte).

    Args:
        data: Data do plantão (YYYY-MM-DD) - horário local SP
        hora_inicio: Hora de início (HH:MM:SS) - horário local SP
        hora_fim: Hora de fim (HH:MM:SS) - horário local SP

    Returns:
        datetime com timezone UTC do fim real do plantão
    """
    data_plantao = datetime.strptime(data, "%Y-%m-%d").date()
    inicio = datetime.strptime(hora_inicio, "%H:%M:%S").time()
    fim = datetime.strptime(hora_fim, "%H:%M:%S").time()

    # Combinar data + hora_fim em horário local (SP)
    fim_local = datetime.combine(data_plantao, fim).replace(tzinfo=TZ_SP)

    # Se hora_fim <= hora_inicio, é plantão noturno (termina no dia seguinte)
    # Ex: 19:00-07:00 ou 22:00-06:00
    if fim <= inicio:
        fim_local += timedelta(days=1)

    # Converter para UTC antes de retornar
    return fim_local.astimezone(timezone.utc)


@dataclass
class ResultadoTransicao:
    """Resultado de uma operacao de transicao."""
    sucesso: bool
    vaga_id: Optional[str] = None
    status_anterior: Optional[str] = None
    status_novo: Optional[str] = None
    erro: Optional[str] = None


@dataclass
class VagaPendenteConfirmacao:
    """Vaga aguardando confirmacao."""
    id: str
    data: str
    hora_inicio: str
    hora_fim: str
    valor: int
    hospital_nome: str
    hospital_id: str
    especialidade_nome: str
    cliente_id: str
    cliente_nome: Optional[str] = None
    cliente_telefone: Optional[str] = None


# =============================================================================
# Job: Transicao reservada -> pendente_confirmacao
# =============================================================================

async def processar_vagas_vencidas(
    buffer_horas: int = BUFFER_HORAS,
    is_backfill: bool = False
) -> dict:
    """
    Processa vagas reservadas cujo plantao ja terminou.

    Regra: status='reservada' AND fim_plantao <= now() - buffer

    Args:
        buffer_horas: Horas apos fim do plantao para considerar vencido
        is_backfill: Se True, marca source como 'backfill' nos eventos

    Returns:
        Dict com estatisticas do processamento
    """
    agora = datetime.now(timezone.utc)
    limite = agora - timedelta(hours=buffer_horas)

    # Buscar vagas reservadas vencidas
    # Precisamos combinar data + hora_inicio + hora_fim para calcular fim real
    # Sprint 44 T04.5: Adicionado limite para evitar queries sem bound
    result = supabase.table("vagas") \
        .select("id, data, hora_inicio, hora_fim, hospital_id, cliente_id") \
        .eq("status", "reservada") \
        .limit(1000) \
        .execute()

    if not result.data:
        logger.info("Nenhuma vaga reservada encontrada")
        return {"processadas": 0, "erros": 0, "vagas": []}

    processadas = 0
    erros = 0
    vagas_transicionadas = []

    for vaga in result.data:
        try:
            # Calcular fim real do plantao
            fim_plantao = calcular_fim_plantao(
                data=vaga["data"],
                hora_inicio=vaga["hora_inicio"],
                hora_fim=vaga["hora_fim"]
            )

            # Verificar se ja passou do buffer
            if fim_plantao > limite:
                continue  # Ainda nao venceu

            # Transicionar para pendente_confirmacao
            resultado = await transicionar_para_pendente_confirmacao(
                vaga_id=vaga["id"],
                hospital_id=vaga.get("hospital_id"),
                cliente_id=vaga.get("cliente_id"),
                fim_plantao=fim_plantao,
                is_backfill=is_backfill
            )

            if resultado.sucesso:
                processadas += 1
                vagas_transicionadas.append(vaga["id"])
            else:
                erros += 1
                logger.error(f"Erro ao transicionar vaga {vaga['id']}: {resultado.erro}")

        except Exception as e:
            erros += 1
            logger.error(f"Erro ao processar vaga {vaga['id']}: {e}")

    logger.info(f"Job de confirmacao: {processadas} transicionadas, {erros} erros")

    return {
        "processadas": processadas,
        "erros": erros,
        "vagas": vagas_transicionadas
    }


async def transicionar_para_pendente_confirmacao(
    vaga_id: str,
    hospital_id: Optional[str],
    cliente_id: Optional[str],
    fim_plantao: datetime,
    is_backfill: bool = False
) -> ResultadoTransicao:
    """
    Transiciona vaga para pendente_confirmacao e emite evento.

    IMPORTANTE: Status e evento sao atualizados atomicamente.
    """
    agora = datetime.now(timezone.utc)

    try:
        # 1. Atualizar status (idempotente: só atualiza se ainda reservada)
        supabase.table("vagas").update({
            "status": "pendente_confirmacao",
            "pendente_confirmacao_em": agora.isoformat(),
            "updated_at": agora.isoformat()
        }).eq("id", vaga_id).eq("status", "reservada").execute()

        # 2. Emitir business_event (com dedupe_key para idempotência)
        dedupe = f"shift_confirmation_due:{vaga_id}"
        event = BusinessEvent(
            event_type=EventType.SHIFT_CONFIRMATION_DUE,
            source=EventSource.BACKEND if not is_backfill else EventSource.OPS,
            cliente_id=cliente_id,
            vaga_id=vaga_id,
            hospital_id=hospital_id,
            dedupe_key=dedupe,
            event_props={
                "scheduled_end_at": fim_plantao.isoformat(),
                "transitioned_at": agora.isoformat(),
                "is_backfill": is_backfill,
                "channel": "job",
                "method": "hourly_cron"
            }
        )

        await emit_event(event)

        # 3. Enviar notificação Slack com botões (se não for backfill)
        if not is_backfill:
            await _enviar_notificacao_slack(vaga_id)

        logger.info(f"Vaga {vaga_id} transicionada para pendente_confirmacao")

        return ResultadoTransicao(
            sucesso=True,
            vaga_id=vaga_id,
            status_anterior="reservada",
            status_novo="pendente_confirmacao"
        )

    except Exception as e:
        return ResultadoTransicao(
            sucesso=False,
            vaga_id=vaga_id,
            erro=str(e)
        )


# =============================================================================
# Confirmacao via Slack
# =============================================================================

async def confirmar_plantao_realizado(
    vaga_id: str,
    confirmado_por: str
) -> ResultadoTransicao:
    """
    Confirma que plantao foi realizado.

    Chamado pelo handler do Slack quando usuario clica "Realizado".

    Args:
        vaga_id: UUID da vaga
        confirmado_por: Identificador de quem confirmou (slack user_id ou nome)
    """
    agora = datetime.now(timezone.utc)

    try:
        # 1. Verificar status atual (idempotencia)
        result = supabase.table("vagas") \
            .select("status, hospital_id, cliente_id") \
            .eq("id", vaga_id) \
            .single() \
            .execute()

        if not result.data:
            return ResultadoTransicao(sucesso=False, erro="Vaga nao encontrada")

        status_atual = result.data["status"]

        if status_atual == "realizada":
            return ResultadoTransicao(sucesso=True, vaga_id=vaga_id, erro="Ja confirmada")

        if status_atual != "pendente_confirmacao":
            return ResultadoTransicao(
                sucesso=False,
                vaga_id=vaga_id,
                erro=f"Status invalido para confirmacao: {status_atual}"
            )

        # 2. Atualizar status + auditoria
        supabase.table("vagas") \
            .update({
                "status": "realizada",
                "realizada_em": agora.isoformat(),
                "realizada_por": confirmado_por,
                "updated_at": agora.isoformat()
            }) \
            .eq("id", vaga_id) \
            .execute()

        # 3. Emitir business_event (com dedupe_key para idempotência)
        dedupe = f"shift_completed:{vaga_id}"
        event = BusinessEvent(
            event_type=EventType.SHIFT_COMPLETED,
            source=EventSource.OPS,
            cliente_id=result.data.get("cliente_id"),
            vaga_id=vaga_id,
            hospital_id=result.data.get("hospital_id"),
            dedupe_key=dedupe,
            event_props={
                "confirmed_by": confirmado_por,
                "confirmed_at": agora.isoformat(),
                "channel": "slack",
                "method": "button"
            }
        )

        await emit_event(event)

        logger.info(f"Vaga {vaga_id} confirmada como REALIZADA por {confirmado_por}")

        return ResultadoTransicao(
            sucesso=True,
            vaga_id=vaga_id,
            status_anterior="pendente_confirmacao",
            status_novo="realizada"
        )

    except Exception as e:
        logger.error(f"Erro ao confirmar vaga {vaga_id}: {e}")
        return ResultadoTransicao(sucesso=False, vaga_id=vaga_id, erro=str(e))


async def confirmar_plantao_nao_ocorreu(
    vaga_id: str,
    confirmado_por: str,
    motivo: Optional[str] = None
) -> ResultadoTransicao:
    """
    Confirma que plantao NAO ocorreu.

    Chamado pelo handler do Slack quando usuario clica "Nao ocorreu".
    """
    agora = datetime.now(timezone.utc)

    try:
        # 1. Verificar status atual
        result = supabase.table("vagas") \
            .select("status, hospital_id, cliente_id") \
            .eq("id", vaga_id) \
            .single() \
            .execute()

        if not result.data:
            return ResultadoTransicao(sucesso=False, erro="Vaga nao encontrada")

        status_atual = result.data["status"]

        if status_atual == "cancelada":
            return ResultadoTransicao(sucesso=True, vaga_id=vaga_id, erro="Ja cancelada")

        if status_atual != "pendente_confirmacao":
            return ResultadoTransicao(
                sucesso=False,
                vaga_id=vaga_id,
                erro=f"Status invalido: {status_atual}"
            )

        # 2. Atualizar status + auditoria
        supabase.table("vagas") \
            .update({
                "status": "cancelada",
                "cancelada_em": agora.isoformat(),
                "cancelada_por": confirmado_por,
                "updated_at": agora.isoformat()
            }) \
            .eq("id", vaga_id) \
            .execute()

        # 3. Emitir business_event (com dedupe_key para idempotência)
        dedupe = f"shift_not_completed:{vaga_id}"
        event = BusinessEvent(
            event_type=EventType.SHIFT_NOT_COMPLETED,
            source=EventSource.OPS,
            cliente_id=result.data.get("cliente_id"),
            vaga_id=vaga_id,
            hospital_id=result.data.get("hospital_id"),
            dedupe_key=dedupe,
            event_props={
                "confirmed_by": confirmado_por,
                "confirmed_at": agora.isoformat(),
                "motivo": motivo,
                "channel": "slack",
                "method": "button"
            }
        )

        await emit_event(event)

        logger.info(f"Vaga {vaga_id} confirmada como NAO OCORREU por {confirmado_por}")

        return ResultadoTransicao(
            sucesso=True,
            vaga_id=vaga_id,
            status_anterior="pendente_confirmacao",
            status_novo="cancelada"
        )

    except Exception as e:
        logger.error(f"Erro ao cancelar vaga {vaga_id}: {e}")
        return ResultadoTransicao(sucesso=False, vaga_id=vaga_id, erro=str(e))


# =============================================================================
# Notificação Slack
# =============================================================================

async def _enviar_notificacao_slack(vaga_id: str) -> bool:
    """
    Envia notificação Slack para confirmação de plantão.
    """
    from app.services.slack import notificar_confirmacao_plantao

    try:
        # Buscar dados completos da vaga
        result = supabase.table("vagas") \
            .select("""
                id, data, hora_inicio, hora_fim, valor,
                hospitais(nome),
                especialidades(nome),
                clientes(nome, telefone)
            """) \
            .eq("id", vaga_id) \
            .single() \
            .execute()

        if not result.data:
            logger.warning(f"Vaga {vaga_id} não encontrada para notificação")
            return False

        vaga = result.data
        hospital = vaga.get("hospitais", {}) or {}
        especialidade = vaga.get("especialidades", {}) or {}
        cliente = vaga.get("clientes", {}) or {}

        await notificar_confirmacao_plantao(
            vaga_id=vaga_id,
            data=vaga.get("data", ""),
            horario=f"{vaga.get('hora_inicio', '')} - {vaga.get('hora_fim', '')}",
            valor=vaga.get("valor", 0),
            hospital=hospital.get("nome", "N/A"),
            especialidade=especialidade.get("nome", "N/A"),
            medico_nome=cliente.get("nome"),
            medico_telefone=cliente.get("telefone")
        )

        return True

    except Exception as e:
        logger.error(f"Erro ao enviar notificação Slack: {e}")
        return False


# =============================================================================
# Queries auxiliares
# =============================================================================

async def listar_pendentes_confirmacao() -> list[VagaPendenteConfirmacao]:
    """
    Lista vagas aguardando confirmacao para exibir no Slack.
    """
    result = supabase.table("vagas") \
        .select("""
            id, data, hora_inicio, hora_fim, valor,
            hospital_id, cliente_id,
            hospitais(nome),
            especialidades(nome),
            clientes(nome, telefone)
        """) \
        .eq("status", "pendente_confirmacao") \
        .order("pendente_confirmacao_em") \
        .execute()

    vagas = []
    for row in result.data or []:
        vagas.append(VagaPendenteConfirmacao(
            id=row["id"],
            data=row["data"],
            hora_inicio=row["hora_inicio"],
            hora_fim=row["hora_fim"],
            valor=row["valor"],
            hospital_id=row["hospital_id"],
            hospital_nome=row.get("hospitais", {}).get("nome", "N/A") if row.get("hospitais") else "N/A",
            especialidade_nome=row.get("especialidades", {}).get("nome", "N/A") if row.get("especialidades") else "N/A",
            cliente_id=row["cliente_id"],
            cliente_nome=row.get("clientes", {}).get("nome") if row.get("clientes") else None,
            cliente_telefone=row.get("clientes", {}).get("telefone") if row.get("clientes") else None,
        ))

    return vagas


async def contar_pendencias() -> dict:
    """
    Conta pendencias para alertas.

    Returns:
        Dict com contagens para alertas P0
    """
    agora = datetime.now(timezone.utc)
    limite_24h = (agora - timedelta(hours=24)).isoformat()
    limite_buffer = (agora - timedelta(hours=BUFFER_HORAS)).isoformat()

    # Pendentes ha mais de 24h (alerta)
    pendentes_atrasadas = supabase.table("vagas") \
        .select("id", count="exact") \
        .eq("status", "pendente_confirmacao") \
        .lt("pendente_confirmacao_em", limite_24h) \
        .execute()

    # Reservadas vencidas (job falhou?)
    reservadas_vencidas = supabase.rpc("contar_reservadas_vencidas", {
        "limite_ts": limite_buffer
    }).execute()

    return {
        "pendentes_atrasadas": pendentes_atrasadas.count or 0,
        "reservadas_vencidas": reservadas_vencidas.data if reservadas_vencidas.data else 0
    }


# =============================================================================
# Funcao RPC auxiliar (criar no banco)
# =============================================================================

# SQL para criar a funcao:
# CREATE OR REPLACE FUNCTION contar_reservadas_vencidas(limite_ts TIMESTAMPTZ)
# RETURNS INTEGER AS $$
# SELECT COUNT(*)::INTEGER
# FROM vagas
# WHERE status = 'reservada'
#   AND (data || ' ' || hora_fim)::TIMESTAMPTZ < limite_ts;
# $$ LANGUAGE SQL;
