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
    "Oi {nome}! Sou a Julia do novo numero. Lembra que te avisei da troca? Aqui estou!",
    "{nome}, oi! Julia aqui, do numero novo. Continuando nossa conversa...",
    "Oi {nome}, cheguei no numero novo! Qualquer coisa que precisar, e so falar aqui.",
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
    result = (
        supabase.table("chip_interactions")
        .select("id, tipo, created_at")
        .eq("chip_id", chip_id)
        .execute()
    )

    # Buscar telefone do medico
    medico = supabase.table("clientes").select("telefone").eq("id", medico_id).single().execute()

    if not medico.data:
        return None

    telefone = medico.data.get("telefone", "")

    # Filtrar interacoes com este telefone
    interacoes = [i for i in (result.data or []) if i.get("destinatario") == telefone]

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
            f"[MigracaoAnunciada] Medico {medico_id} sem relacionamento com chip, pulando aviso"
        )
        # Migrar silenciosamente
        return await migrar_conversa_silenciosa(chip_antigo, chip_novo, medico_id)

    # 2. Buscar dados do medico
    medico = (
        supabase.table("clientes")
        .select("id, telefone, nome, primeiro_nome")
        .eq("id", medico_id)
        .single()
        .execute()
    )

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

    supabase.table("migracao_agendada").insert(
        {
            "chip_antigo_id": chip_antigo["id"],
            "chip_novo_id": chip_novo["id"],
            "medico_id": medico_id,
            "agendado_para": agendado_para.isoformat(),
            "status": "pendente",
        }
    ).execute()

    logger.info(f"[MigracaoAnunciada] Continuacao agendada para {agendado_para.isoformat()}")

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
    result = (
        supabase.table("conversations")
        .select("id")
        .eq("cliente_id", medico_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return True  # Nada a migrar

    conversa_id = result.data[0]["id"]

    # Atualizar mapeamento
    supabase.table("conversation_chips").update(
        {
            "chip_id": chip_novo["id"],
            "migrated_at": datetime.now(timezone.utc).isoformat(),
            "migrated_from": chip_antigo["id"],
        }
    ).eq("conversa_id", conversa_id).eq("active", True).execute()

    logger.info(f"[MigracaoAnunciada] Conversa {conversa_id} migrada silenciosamente")

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
    result = (
        supabase.table("migracao_agendada")
        .select(
            "*, chips!chip_novo_id(telefone, instance_name), clientes!medico_id(telefone, primeiro_nome, nome)"
        )
        .eq("status", "pendente")
        .lte("agendado_para", agora)
        .execute()
    )

    processadas = 0
    erros = 0

    for migracao in result.data or []:
        try:
            await enviar_mensagem_continuacao(migracao)

            supabase.table("migracao_agendada").update(
                {
                    "status": "concluida",
                    "processado_em": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", migracao["id"]).execute()

            processadas += 1

        except Exception as e:
            logger.error(f"[MigracaoAnunciada] Erro ao processar {migracao['id']}: {e}")
            erros += 1

    logger.info(f"[MigracaoAnunciada] Processadas: {processadas}, Erros: {erros}")

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

    logger.info(f"[MigracaoAnunciada] Mensagem de continuacao enviada para {telefone}")


async def listar_migracoes_pendentes() -> List[Dict]:
    """Lista migracoes pendentes."""
    result = (
        supabase.table("migracao_agendada")
        .select("*")
        .eq("status", "pendente")
        .order("agendado_para")
        .execute()
    )

    return result.data or []


async def cancelar_migracao(migracao_id: str) -> bool:
    """Cancela uma migracao agendada."""
    supabase.table("migracao_agendada").update(
        {
            "status": "cancelada",
        }
    ).eq("id", migracao_id).execute()

    return True


# ============================================================
# Sprint 36 - T11.4: Migração com Contexto
# ============================================================


async def coletar_contexto_conversa(medico_id: str, chip_id: str, limite_msgs: int = 20) -> Dict:
    """
    Sprint 36 - T11.4: Coleta contexto da conversa para migração.

    Preserva:
    - Resumo das últimas mensagens
    - Preferências do médico
    - Estado do relacionamento
    - Assuntos discutidos

    Args:
        medico_id: ID do médico
        chip_id: ID do chip atual
        limite_msgs: Máximo de mensagens a considerar

    Returns:
        Dict com contexto completo
    """
    contexto = {
        "medico_id": medico_id,
        "chip_id": chip_id,
        "coletado_em": datetime.now(timezone.utc).isoformat(),
        "resumo_conversa": None,
        "preferencias": {},
        "assuntos_recentes": [],
        "tom_relacionamento": "neutro",
        "ultima_interacao": None,
        "total_interacoes": 0,
    }

    try:
        # 1. Buscar dados do médico
        medico_result = (
            supabase.table("clientes")
            .select(
                "id, nome, primeiro_nome, especialidade, preferencias, "
                "horario_preferido, dias_preferidos"
            )
            .eq("id", medico_id)
            .single()
            .execute()
        )

        if medico_result.data:
            medico = medico_result.data
            contexto["preferencias"] = {
                "nome_tratamento": medico.get("primeiro_nome") or medico.get("nome", "").split()[0],
                "especialidade": medico.get("especialidade"),
                "horario_preferido": medico.get("horario_preferido"),
                "dias_preferidos": medico.get("dias_preferidos"),
                "preferencias_custom": medico.get("preferencias") or {},
            }

        # 2. Buscar últimas interações
        interacoes_result = (
            supabase.table("interacoes")
            .select("id, tipo, mensagem, resposta, created_at")
            .eq("cliente_id", medico_id)
            .order("created_at", desc=True)
            .limit(limite_msgs)
            .execute()
        )

        interacoes = interacoes_result.data or []

        if interacoes:
            contexto["total_interacoes"] = len(interacoes)
            contexto["ultima_interacao"] = interacoes[0]["created_at"]

            # Extrair assuntos discutidos (análise simples)
            assuntos = set()
            for inter in interacoes:
                msg = (inter.get("mensagem") or "").lower()
                resp = (inter.get("resposta") or "").lower()
                texto = f"{msg} {resp}"

                if "plantão" in texto or "escala" in texto:
                    assuntos.add("plantoes")
                if "valor" in texto or "pagamento" in texto or "remuneração" in texto:
                    assuntos.add("remuneracao")
                if "hospital" in texto or "unidade" in texto:
                    assuntos.add("locais")
                if "horário" in texto or "disponibilidade" in texto:
                    assuntos.add("disponibilidade")
                if "documentos" in texto or "crm" in texto:
                    assuntos.add("documentacao")

            contexto["assuntos_recentes"] = list(assuntos)

        # 3. Buscar doctor_state para tom do relacionamento
        state_result = (
            supabase.table("doctor_state")
            .select("interest_level, engagement_score, sentiment_trend, optout_reason")
            .eq("cliente_id", medico_id)
            .single()
            .execute()
        )

        if state_result.data:
            state = state_result.data
            interesse = state.get("interest_level", "unknown")
            sentimento = state.get("sentiment_trend", "neutral")

            # Determinar tom
            if interesse == "hot" or state.get("engagement_score", 0) > 70:
                contexto["tom_relacionamento"] = "engajado"
            elif interesse == "cold" or sentimento == "negative":
                contexto["tom_relacionamento"] = "distante"
            elif state.get("optout_reason"):
                contexto["tom_relacionamento"] = "desinteressado"
            else:
                contexto["tom_relacionamento"] = "neutro"

        # 4. Gerar resumo da conversa (últimas 5 mensagens)
        if interacoes:
            ultimas = interacoes[:5]
            resumo_partes = []
            for inter in reversed(ultimas):  # Ordem cronológica
                if inter.get("mensagem"):
                    resumo_partes.append(f"Médico: {inter['mensagem'][:100]}")
                if inter.get("resposta"):
                    resumo_partes.append(f"Julia: {inter['resposta'][:100]}")

            contexto["resumo_conversa"] = "\n".join(resumo_partes) if resumo_partes else None

        return contexto

    except Exception as e:
        logger.error(f"[MigracaoContexto] Erro ao coletar contexto: {e}")
        contexto["erro"] = str(e)
        return contexto


async def migrar_conversa_com_contexto(
    chip_antigo: Dict, chip_novo: Dict, medico_id: str, motivo: str = "degradacao_chip"
) -> Dict:
    """
    Sprint 36 - T11.4: Migra conversa preservando contexto completo.

    Diferente da migração simples:
    - Coleta contexto antes de migrar
    - Salva contexto para o novo chip poder continuar
    - Notifica médico se apropriado
    - Registra auditoria completa

    Args:
        chip_antigo: Chip que está sendo substituído
        chip_novo: Chip que vai assumir
        medico_id: ID do médico
        motivo: Motivo da migração

    Returns:
        Resultado completo da migração
    """
    resultado = {
        "sucesso": False,
        "chip_antigo_id": chip_antigo["id"],
        "chip_novo_id": chip_novo["id"],
        "medico_id": medico_id,
        "motivo": motivo,
        "contexto_preservado": False,
        "notificou_medico": False,
        "migracao_id": None,
    }

    try:
        # 1. Coletar contexto completo
        logger.info(
            f"[MigracaoContexto] Coletando contexto para migração: "
            f"medico={medico_id}, chip_antigo={chip_antigo.get('telefone')}"
        )
        contexto = await coletar_contexto_conversa(medico_id, chip_antigo["id"])

        # 2. Buscar conversa do médico
        conversa_result = (
            supabase.table("conversations")
            .select("id")
            .eq("cliente_id", medico_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        conversa_id = conversa_result.data[0]["id"] if conversa_result.data else None

        # 3. Salvar contexto na tabela de migrações
        migracao_data = {
            "chip_antigo_id": chip_antigo["id"],
            "chip_novo_id": chip_novo["id"],
            "medico_id": medico_id,
            "conversa_id": conversa_id,
            "motivo": motivo,
            "contexto": contexto,
            "status": "em_progresso",
            "iniciado_em": datetime.now(timezone.utc).isoformat(),
        }

        migracao_insert = supabase.table("migracao_agendada").insert(migracao_data).execute()

        if migracao_insert.data:
            resultado["migracao_id"] = migracao_insert.data[0]["id"]
            resultado["contexto_preservado"] = True

        # 4. Verificar se deve notificar médico
        deve_notificar = (
            contexto.get("total_interacoes", 0) >= 2
            and contexto.get("tom_relacionamento") != "desinteressado"
            and chip_antigo.get("evolution_connected")  # Chip antigo ainda funciona
        )

        if deve_notificar:
            # Usar migração anunciada padrão
            notificou = await migrar_conversa_anunciada(chip_antigo, chip_novo, medico_id)
            resultado["notificou_medico"] = notificou
        else:
            # Migração silenciosa
            await migrar_conversa_silenciosa(chip_antigo, chip_novo, medico_id)

        # 5. Atualizar mapeamento de conversa com contexto
        if conversa_id:
            supabase.table("conversation_chips").update(
                {
                    "chip_id": chip_novo["id"],
                    "migrated_at": datetime.now(timezone.utc).isoformat(),
                    "migrated_from": chip_antigo["id"],
                    "migration_context": contexto,
                }
            ).eq("conversa_id", conversa_id).eq("active", True).execute()

        # 6. Transferir afinidade para novo chip
        try:
            from app.services.chips.affinity import registrar_interacao_chip_medico

            # Registrar afinidade no novo chip baseado no contexto
            if contexto.get("total_interacoes", 0) > 0:
                await registrar_interacao_chip_medico(
                    chip_id=chip_novo["id"],
                    medico_id=medico_id,
                    tipo="migracao_afinidade",
                    metadata={
                        "chip_anterior": chip_antigo["id"],
                        "interacoes_anteriores": contexto.get("total_interacoes", 0),
                        "tom_relacionamento": contexto.get("tom_relacionamento"),
                    },
                )
        except Exception as e:
            logger.warning(f"[MigracaoContexto] Erro ao transferir afinidade: {e}")

        # 7. Atualizar status da migração
        if resultado["migracao_id"]:
            supabase.table("migracao_agendada").update(
                {
                    "status": "concluida"
                    if resultado["notificou_medico"]
                    else "migrado_silencioso",
                    "processado_em": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", resultado["migracao_id"]).execute()

        resultado["sucesso"] = True
        resultado["contexto"] = {
            "tom_relacionamento": contexto.get("tom_relacionamento"),
            "total_interacoes": contexto.get("total_interacoes"),
            "assuntos_recentes": contexto.get("assuntos_recentes"),
        }

        logger.info(
            f"[MigracaoContexto] Migração concluída: "
            f"medico={medico_id}, "
            f"chip {chip_antigo.get('telefone')} -> {chip_novo.get('telefone')}, "
            f"contexto_preservado=True, notificou={resultado['notificou_medico']}"
        )

        return resultado

    except Exception as e:
        logger.error(f"[MigracaoContexto] Erro na migração: {e}")
        resultado["erro"] = str(e)

        # Tentar migração de fallback simples
        try:
            await migrar_conversa_silenciosa(chip_antigo, chip_novo, medico_id)
            resultado["sucesso"] = True
            resultado["fallback_usado"] = True
        except Exception:
            pass

        return resultado


async def obter_contexto_conversa_atual(conversa_id: str) -> Optional[Dict]:
    """
    Sprint 36 - T11.4: Obtém contexto de migração salvo para uma conversa.

    Útil para o agente Julia saber o histórico ao continuar
    uma conversa em um novo chip.

    Args:
        conversa_id: ID da conversa

    Returns:
        Contexto de migração ou None
    """
    try:
        result = (
            supabase.table("conversation_chips")
            .select("migration_context, migrated_at, migrated_from")
            .eq("conversa_id", conversa_id)
            .eq("active", True)
            .single()
            .execute()
        )

        if result.data and result.data.get("migration_context"):
            return {
                "contexto": result.data["migration_context"],
                "migrado_em": result.data.get("migrated_at"),
                "chip_anterior": result.data.get("migrated_from"),
            }

        return None

    except Exception as e:
        logger.debug(f"[MigracaoContexto] Erro ao buscar contexto: {e}")
        return None


async def listar_migracoes_com_contexto(
    status: Optional[str] = None, limite: int = 50
) -> List[Dict]:
    """
    Sprint 36 - T11.4: Lista migrações com contexto preservado.

    Args:
        status: Filtrar por status (opcional)
        limite: Máximo de registros

    Returns:
        Lista de migrações com contexto
    """
    query = (
        supabase.table("migracao_agendada")
        .select("*, chips!chip_novo_id(telefone), clientes!medico_id(nome, primeiro_nome)")
        .not_.is_("contexto", "null")
        .order("iniciado_em", desc=True)
        .limit(limite)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    return result.data or []
