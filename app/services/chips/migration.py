"""
Migracao Anunciada - Notificar medico antes de trocar chip.

Sprint 26 - E07

Quando chip degrada (mas ainda funciona), notifica o medico da troca
de numero para manter transparencia e confianca.

Regras:
- Usar apenas quando medico tem historico (affinity > 2 msgs)
- NAO usar para prospeccao fria
- NAO usar se chip ja desconectado
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List

from app.services.supabase import supabase
from app.services.whatsapp import EvolutionClient

logger = logging.getLogger(__name__)


# Templates de mensagem para troca de numero
TEMPLATES_AVISO_TROCA = [
    "Oi {nome}! Tudo bem? Vou trocar de numero essa semana, "
    "me salva esse novo: {numero_novo}. Continuo por la!",

    "Oi {nome}, passando pra avisar que vou mudar de numero. "
    "Ja anota ai o novo: {numero_novo}. Qualquer coisa me chama la!",

    "{nome}, so avisando que vou trocar de numero. "
    "O novo e {numero_novo}, ja salva ai pra gente continuar conversando!",
]

TEMPLATES_CONTINUACAO = [
    "Oi {nome}! Sou a Julia do novo numero. "
    "Lembra que te avisei da troca? Aqui estou!",

    "{nome}, oi! Julia aqui, do numero novo. "
    "Continuando nossa conversa...",

    "Oi {nome}, cheguei no numero novo! "
    "Qualquer coisa que precisar, e so falar aqui.",
]


async def verificar_affinity(medico_id: str, chip_id: str) -> Optional[Dict]:
    """
    Verifica affinity (historico) entre medico e chip.

    Args:
        medico_id: ID do medico
        chip_id: ID do chip

    Returns:
        {
            "msgs_trocadas": N,
            "ultima_interacao": datetime,
            "tem_relacionamento": bool
        }
    """
    # Buscar interacoes entre o chip e o medico
    result = supabase.table("chip_interactions").select(
        "id, tipo, created_at"
    ).eq(
        "chip_id", chip_id
    ).execute()

    # Buscar telefone do medico
    medico = supabase.table("clientes").select("telefone").eq(
        "id", medico_id
    ).single().execute()

    if not medico.data:
        return None

    telefone = medico.data.get("telefone", "")

    # Filtrar interacoes com este telefone
    interacoes = [
        i for i in (result.data or [])
        if i.get("destinatario") == telefone
    ]

    if not interacoes:
        return {
            "msgs_trocadas": 0,
            "ultima_interacao": None,
            "tem_relacionamento": False,
        }

    return {
        "msgs_trocadas": len(interacoes),
        "ultima_interacao": max(i["created_at"] for i in interacoes),
        "tem_relacionamento": len(interacoes) >= 2,
    }


async def migrar_conversa_anunciada(
    chip_antigo: Dict,
    chip_novo: Dict,
    medico_id: str,
) -> bool:
    """
    Migra conversa com aviso ao medico.

    Fluxo:
    1. Verificar se medico tem historico
    2. Enviar mensagem de aviso pelo chip antigo
    3. Agendar continuacao em 24-48h

    Args:
        chip_antigo: Chip degradado (ainda funcional)
        chip_novo: Chip que assumira a conversa
        medico_id: ID do medico

    Returns:
        True se iniciou migracao com sucesso
    """
    # 1. Verificar se medico tem historico
    affinity = await verificar_affinity(medico_id, chip_antigo["id"])

    if not affinity or not affinity.get("tem_relacionamento"):
        logger.info(
            f"[MigracaoAnunciada] Medico {medico_id} sem relacionamento com chip, "
            "pulando aviso"
        )
        # Migrar silenciosamente
        return await migrar_conversa_silenciosa(chip_antigo, chip_novo, medico_id)

    # 2. Buscar dados do medico
    medico = supabase.table("clientes").select(
        "id, telefone, nome, primeiro_nome"
    ).eq("id", medico_id).single().execute()

    if not medico.data:
        logger.warning(f"[MigracaoAnunciada] Medico {medico_id} nao encontrado")
        return False

    nome = medico.data.get("primeiro_nome") or medico.data.get("nome", "").split()[0]
    telefone = medico.data.get("telefone")

    # 3. Gerar mensagem de aviso
    template = random.choice(TEMPLATES_AVISO_TROCA)
    mensagem = template.format(
        nome=nome,
        numero_novo=chip_novo["telefone"],
    )

    # 4. Enviar pelo chip antigo
    try:
        client = EvolutionClient(instance=chip_antigo["instance_name"])
        await client.enviar_texto(telefone, mensagem)

        logger.info(
            f"[MigracaoAnunciada] Aviso enviado para {telefone} "
            f"({chip_antigo['telefone']} -> {chip_novo['telefone']})"
        )

    except Exception as e:
        logger.error(f"[MigracaoAnunciada] Erro ao enviar aviso: {e}")
        # Se nao conseguiu enviar, migrar silenciosamente
        return await migrar_conversa_silenciosa(chip_antigo, chip_novo, medico_id)

    # 5. Agendar continuacao em 24-48h
    delay_horas = random.randint(24, 48)
    agendado_para = datetime.now(timezone.utc) + timedelta(hours=delay_horas)

    supabase.table("migracao_agendada").insert({
        "chip_antigo_id": chip_antigo["id"],
        "chip_novo_id": chip_novo["id"],
        "medico_id": medico_id,
        "agendado_para": agendado_para.isoformat(),
        "status": "pendente",
    }).execute()

    logger.info(
        f"[MigracaoAnunciada] Continuacao agendada para {agendado_para.isoformat()}"
    )

    return True


async def migrar_conversa_silenciosa(
    chip_antigo: Dict,
    chip_novo: Dict,
    medico_id: str,
) -> bool:
    """
    Migra conversa sem aviso (para prospeccao fria).

    Apenas atualiza o mapeamento conversa-chip.
    """
    # Buscar conversa do medico
    result = supabase.table("conversations").select("id").eq(
        "cliente_id", medico_id
    ).order("created_at", desc=True).limit(1).execute()

    if not result.data:
        return True  # Nada a migrar

    conversa_id = result.data[0]["id"]

    # Atualizar mapeamento
    supabase.table("conversation_chips").update({
        "chip_id": chip_novo["id"],
        "migrated_at": datetime.now(timezone.utc).isoformat(),
        "migrated_from": chip_antigo["id"],
    }).eq("conversa_id", conversa_id).eq("active", True).execute()

    logger.info(
        f"[MigracaoAnunciada] Conversa {conversa_id} migrada silenciosamente"
    )

    return True


async def processar_migracoes_agendadas() -> Dict:
    """
    Processa migracoes agendadas que ja passaram do horario.

    Rodar via job periodico.

    Returns:
        {"processadas": N, "erros": N}
    """
    agora = datetime.now(timezone.utc).isoformat()

    # Buscar pendentes
    result = supabase.table("migracao_agendada").select(
        "*, chips!chip_novo_id(telefone, instance_name), clientes!medico_id(telefone, primeiro_nome, nome)"
    ).eq(
        "status", "pendente"
    ).lte(
        "agendado_para", agora
    ).execute()

    processadas = 0
    erros = 0

    for migracao in result.data or []:
        try:
            await enviar_mensagem_continuacao(migracao)

            supabase.table("migracao_agendada").update({
                "status": "concluida",
                "processado_em": datetime.now(timezone.utc).isoformat(),
            }).eq("id", migracao["id"]).execute()

            processadas += 1

        except Exception as e:
            logger.error(f"[MigracaoAnunciada] Erro ao processar {migracao['id']}: {e}")
            erros += 1

    logger.info(
        f"[MigracaoAnunciada] Processadas: {processadas}, Erros: {erros}"
    )

    return {"processadas": processadas, "erros": erros}


async def enviar_mensagem_continuacao(migracao: Dict):
    """
    Envia mensagem de continuacao pelo chip novo.
    """
    chip_novo = migracao.get("chips", {})
    medico = migracao.get("clientes", {})

    if not chip_novo or not medico:
        logger.warning(f"[MigracaoAnunciada] Dados incompletos para {migracao['id']}")
        return

    nome = medico.get("primeiro_nome") or medico.get("nome", "").split()[0]
    telefone = medico.get("telefone")

    template = random.choice(TEMPLATES_CONTINUACAO)
    mensagem = template.format(nome=nome)

    client = EvolutionClient(instance=chip_novo["instance_name"])
    await client.enviar_texto(telefone, mensagem)

    logger.info(
        f"[MigracaoAnunciada] Mensagem de continuacao enviada para {telefone}"
    )


async def listar_migracoes_pendentes() -> List[Dict]:
    """Lista migracoes pendentes."""
    result = supabase.table("migracao_agendada").select("*").eq(
        "status", "pendente"
    ).order("agendado_para").execute()

    return result.data or []


async def cancelar_migracao(migracao_id: str) -> bool:
    """Cancela uma migracao agendada."""
    supabase.table("migracao_agendada").update({
        "status": "cancelada",
    }).eq("id", migracao_id).execute()

    return True
