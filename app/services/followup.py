"""
Servico de follow-up automatico.

Cadencia: 48h -> 5d -> 15d -> pausa 60d
Documentado em docs/FLUXOS.md
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from app.services.supabase import supabase
from app.services.fila import fila_service
from app.config.followup import (
    FOLLOWUP_CONFIG,
    PAUSA_APOS_NAO_RESPOSTA,
    STAGES_FOLLOWUP,
    TEMPLATES_FOLLOWUP,
    STAGE_RECONTATO,
    REGRAS_FOLLOWUP,
)

logger = logging.getLogger(__name__)


# =============================================================================
# FUNCOES PRINCIPAIS (NOVA IMPLEMENTACAO)
# =============================================================================


async def processar_followups_pendentes() -> dict:
    """
    Processa todas as conversas que precisam de follow-up.

    Verifica cada stage elegivel e agenda follow-ups conforme a cadencia:
    - msg_enviada (48h) -> followup_1_enviado
    - followup_1_enviado (5d) -> followup_2_enviado
    - followup_2_enviado (15d) -> nao_respondeu + pausa 60d

    Returns:
        dict com estatisticas de processamento
    """
    stats = {"processadas": 0, "followups_agendados": 0, "erros": 0, "por_tipo": {}}

    for stage in STAGES_FOLLOWUP:
        config = _get_config_para_stage(stage)
        if not config:
            continue

        # Buscar conversas no stage, sem resposta ha X tempo
        conversas = await _buscar_conversas_para_followup(stage, config["delay"])
        logger.info(f"Stage {stage}: {len(conversas)} conversa(s) para follow-up")

        for conversa in conversas:
            try:
                await _agendar_followup(conversa, config)
                stats["followups_agendados"] += 1

                # Contador por tipo
                tipo = config["key"]
                stats["por_tipo"][tipo] = stats["por_tipo"].get(tipo, 0) + 1

            except Exception as e:
                logger.error(f"Erro ao agendar follow-up para conversa {conversa.get('id')}: {e}")
                stats["erros"] += 1

            stats["processadas"] += 1

    logger.info(f"Follow-ups processados: {stats}")
    return stats


def _get_config_para_stage(stage: str) -> Optional[dict]:
    """Retorna configuracao de follow-up para o stage."""
    for key, config in FOLLOWUP_CONFIG.items():
        if config["stage_anterior"] == stage:
            return {"key": key, **config}
    return None


async def _buscar_conversas_para_followup(stage: str, delay: timedelta) -> list:
    """
    Busca conversas no stage especificado, sem atividade ha mais de delay.

    Criterios:
    - Stage correto
    - Ultima mensagem ha mais de delay
    - Nao em pausa (pausado_ate is null ou < agora)
    - controlled_by = 'ai'
    """
    cutoff = datetime.now(timezone.utc) - delay

    try:
        response = (
            supabase.table("conversations")
            .select("*, clientes(*)")
            .eq("stage", stage)
            .eq("controlled_by", "ai")
            .lte("ultima_mensagem_em", cutoff.isoformat())
            .is_("pausado_ate", "null")  # Nao pausado
            .limit(50)  # Processar em lotes
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"Erro ao buscar conversas para follow-up: {e}")
        return []


async def _agendar_followup(conversa: dict, config: dict):
    """
    Agenda mensagem de follow-up para a conversa.
    """
    medico = conversa.get("clientes", {})
    conversa_id = conversa["id"]

    # Gerar mensagem de follow-up
    if config.get("incluir_vaga"):
        # Follow-up 2: inclui vaga real
        mensagem = await _gerar_followup_com_vaga(medico, config)
    else:
        mensagem = _gerar_followup_simples(medico, config)

    # Enfileirar mensagem
    await fila_service.enfileirar(
        cliente_id=conversa["cliente_id"],
        conversa_id=conversa_id,
        conteudo=mensagem,
        tipo=f"followup_{config['key']}",
        prioridade=5,
    )

    # Atualizar stage da conversa
    novo_stage = config["stage_proximo"]
    supabase.table("conversations").update(
        {"stage": novo_stage, "updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", conversa_id).execute()

    logger.info(f"Follow-up {config['key']} agendado para conversa {conversa_id}")

    # Se proximo stage e 'nao_respondeu', aplicar pausa de 60 dias
    if novo_stage == "nao_respondeu":
        await aplicar_pausa_60_dias(conversa_id)


def _gerar_followup_simples(medico: dict, config: dict) -> str:
    """Gera mensagem de follow-up sem vaga especifica."""
    nome = medico.get("primeiro_nome", "")
    key = config["key"]

    templates = TEMPLATES_FOLLOWUP.get(key, [config.get("template_hint", "Oi!")])
    template = random.choice(templates)

    return template.format(nome=nome)


async def _gerar_followup_com_vaga(medico: dict, config: dict) -> str:
    """Gera follow-up incluindo uma vaga real."""
    from app.services.vaga import buscar_vagas_compativeis

    nome = medico.get("primeiro_nome", "")
    especialidade_id = medico.get("especialidade_id")
    key = config["key"]

    if not especialidade_id:
        return _gerar_followup_simples(medico, config)

    # Buscar vaga real
    try:
        vagas = await buscar_vagas_compativeis(
            especialidade_id=especialidade_id, cliente_id=medico.get("id"), limite=1
        )
    except Exception as e:
        logger.warning(f"Erro ao buscar vagas para follow-up: {e}")
        return _gerar_followup_simples(medico, config)

    if not vagas:
        return _gerar_followup_simples(medico, config)

    vaga = vagas[0]
    hospital = vaga.get("hospitais", {}).get("nome", "hospital")
    data = vaga.get("data", "")
    periodo = vaga.get("periodos", {}).get("nome", "")
    valor = vaga.get("valor", 0)

    # Formatar info da vaga
    vaga_info = f"{hospital}, {data}, {periodo}"
    if valor:
        vaga_info += f"\nR$ {valor:,.0f}".replace(",", ".")

    templates = TEMPLATES_FOLLOWUP.get(key, ["{nome}, achei uma vaga\n\n{vaga_info}"])
    template = random.choice(templates)

    return template.format(nome=nome, vaga_info=vaga_info)


# =============================================================================
# PAUSA DE 60 DIAS
# =============================================================================


async def aplicar_pausa_60_dias(conversa_id: str):
    """
    Aplica pausa de 60 dias em conversa que nao respondeu.

    Chamado quando conversa atinge stage 'nao_respondeu'.
    """
    pausa_ate = datetime.now(timezone.utc) + PAUSA_APOS_NAO_RESPOSTA

    supabase.table("conversations").update({"pausado_ate": pausa_ate.isoformat()}).eq(
        "id", conversa_id
    ).execute()

    logger.info(f"Conversa {conversa_id} pausada ate {pausa_ate.date()}")


async def processar_pausas_expiradas() -> dict:
    """
    Reativa conversas cuja pausa de 60 dias expirou.

    Conversas em stage 'nao_respondeu' com pausa expirada
    voltam para 'recontato' para serem prospectadas novamente.
    """
    stats = {"reativadas": 0, "erros": 0}
    agora = datetime.now(timezone.utc).isoformat()

    try:
        # Buscar conversas com pausa expirada
        response = (
            supabase.table("conversations")
            .select("id, cliente_id")
            .eq("stage", "nao_respondeu")
            .lte("pausado_ate", agora)
            .limit(50)
            .execute()
        )

        for conversa in response.data or []:
            try:
                supabase.table("conversations").update(
                    {"stage": STAGE_RECONTATO, "pausado_ate": None, "updated_at": agora}
                ).eq("id", conversa["id"]).execute()

                logger.info(f"Conversa {conversa['id']} reativada apos pausa de 60 dias")
                stats["reativadas"] += 1
            except Exception as e:
                logger.error(f"Erro ao reativar conversa {conversa['id']}: {e}")
                stats["erros"] += 1

    except Exception as e:
        logger.error(f"Erro ao buscar pausas expiradas: {e}")

    logger.info(f"Pausas processadas: {stats}")
    return stats


# =============================================================================
# CLASSE LEGADA (para compatibilidade com jobs.py existente)
# =============================================================================


class FollowupService:
    """Gerencia follow-ups automaticos (legado - usa nova implementacao)."""

    async def verificar_followups_pendentes(self) -> List[Dict]:
        """
        Identifica conversas que precisam de follow-up.
        LEGADO: Mantido para compatibilidade com job existente.
        """
        pendentes = []

        for tipo, config in REGRAS_FOLLOWUP.items():
            dias = config["dias_ate_followup"]
            data_limite = datetime.now(timezone.utc) - timedelta(days=dias)

            # Buscar conversas ativas controladas pela IA
            try:
                conversas_resp = (
                    supabase.table("conversations")
                    .select("id, cliente_id, status, controlled_by")
                    .eq("status", "active")
                    .eq("controlled_by", "ai")
                    .execute()
                )
            except Exception as e:
                logger.error(f"Erro ao buscar conversas: {e}")
                continue

            conversas = conversas_resp.data or []

            for conv in conversas:
                # Buscar ultima interacao
                try:
                    interacoes_resp = (
                        supabase.table("interacoes")
                        .select("origem, created_at")
                        .eq("conversation_id", conv["id"])
                        .order("created_at", desc=True)
                        .limit(1)
                        .execute()
                    )
                except Exception:
                    continue

                if not interacoes_resp.data:
                    continue

                ultima = interacoes_resp.data[0]

                # Se ultima foi da Julia (origem = "julia" ou autor_tipo = "ai")
                origem = ultima.get("origem", "")
                if origem in ["julia", "saida"] or ultima.get("autor_tipo") == "ai":
                    try:
                        created_at = ultima["created_at"]
                        if created_at.endswith("Z"):
                            created_at = created_at.replace("Z", "+00:00")
                        ultima_data = datetime.fromisoformat(created_at)
                        if ultima_data < data_limite:
                            pendentes.append({"conversa": conv, "tipo": tipo, "config": config})
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
        try:
            conv_resp = (
                supabase.table("conversations")
                .select("*, clientes(primeiro_nome, telefone)")
                .eq("id", conversa_id)
                .single()
                .execute()
            )
        except Exception as e:
            logger.error(f"Erro ao buscar conversa {conversa_id}: {e}")
            return False

        if not conv_resp.data:
            logger.error(f"Conversa {conversa_id} nao encontrada")
            return False

        conv = conv_resp.data
        cliente = conv.get("clientes", {})

        if not cliente:
            logger.error(f"Cliente nao encontrado para conversa {conversa_id}")
            return False

        # Escolher mensagem aleatoria
        template = random.choice(config["mensagens"])
        mensagem = template.format(nome=cliente.get("primeiro_nome", ""))

        # Enfileirar
        await fila_service.enfileirar(
            cliente_id=conv["cliente_id"],
            conversa_id=conversa_id,
            conteudo=mensagem,
            tipo="followup",
            prioridade=4,
            metadata={"tipo_followup": tipo},
        )

        logger.info(f"Follow-up enfileirado para conversa {conversa_id}")
        return True


# Instancia global para compatibilidade
followup_service = FollowupService()
