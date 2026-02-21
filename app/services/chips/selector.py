"""
Chip Selector - Selecao inteligente de chip por tipo de mensagem.

Sprint 26 - E02
Sprint 36 - T05.6: Retry com chip alternativo
Sprint 36 - T05.7: Threshold emergencial para fallback
Sprint 36 - T09.2: Integrar circuit breaker per-chip na seleção
Sprint 36 - T10.1: Log de decisão ChipSelector
Sprint 36 - T11.5: Afinidade chip-médico na seleção
Sprint 36 - T11.6: Verificar conexão Evolution na seleção
Sprint 27 - Multi-provider: Suporte a Z-API (não requer evolution_connected)

Considera:
- Circuit breaker do chip (não seleciona se OPEN)
- Conexão ativa (evolution_connected para Evolution, status=active para Z-API)
- Trust Score do chip
- Permissoes (pode_prospectar, pode_followup, pode_responder)
- Uso atual (msgs/hora, msgs/dia)
- Afinidade chip-médico (Sprint 36)
- Historico com o contato
- Continuidade de conversa
"""

import logging
from typing import Optional, List, Dict, Literal
from datetime import datetime, timedelta, timezone

from app.services.supabase import supabase
from app.services.chips.circuit_breaker import ChipCircuitBreaker

# Sprint 44 T01.8: Import Redis para reserva atômica
from app.services.redis import redis_client

logger = logging.getLogger(__name__)

TipoMensagem = Literal["prospeccao", "followup", "resposta"]


class ChipSelector:
    """Seletor inteligente de chips."""

    def __init__(self):
        self.config: Optional[Dict] = None

    async def carregar_config(self) -> Dict:
        """Carrega configuracao do pool."""
        result = supabase.table("pool_config").select("*").limit(1).execute()
        if result.data:
            self.config = result.data[0]
        else:
            self.config = {
                "limite_prospeccao_hora": 5,
                "limite_followup_hora": 10,
                "limite_resposta_hora": 20,
            }
        return self.config

    async def selecionar_chip(
        self,
        tipo_mensagem: TipoMensagem,
        conversa_id: Optional[str] = None,
        telefone_destino: Optional[str] = None,
        excluir_chips: Optional[List[str]] = None,
        fallback_mode: bool = False,
    ) -> Optional[Dict]:
        """
        Seleciona melhor chip para enviar mensagem.

        Sprint 36 - T05.6: Suporte a excluir_chips para retry com fallback.
        Sprint 36 - T05.7: Suporte a fallback_mode para threshold emergencial.

        Args:
            tipo_mensagem: 'prospeccao', 'followup', ou 'resposta'
            conversa_id: ID da conversa (para continuidade)
            telefone_destino: Telefone do destinatario
            excluir_chips: Lista de chip_ids a excluir (já tentados)
            fallback_mode: Se True, usa thresholds reduzidos

        Returns:
            Chip selecionado ou None
        """
        if not self.config:
            await self.carregar_config()

        excluir_chips = excluir_chips or []

        # 1. Se eh resposta e tem conversa, manter no mesmo chip
        if tipo_mensagem == "resposta" and conversa_id:
            chip_existente = await self._buscar_chip_conversa(conversa_id)
            if chip_existente and chip_existente.get("pode_responder"):
                # Sprint 36 - T05.6: Verificar se não está na lista de exclusão
                if chip_existente["id"] not in excluir_chips:
                    logger.debug(
                        f"[ChipSelector] Usando chip existente da conversa: {chip_existente['telefone']}"
                    )
                    return chip_existente

        # 2. Buscar chips elegiveis
        chips = await self._buscar_chips_elegiveis(tipo_mensagem, fallback_mode)

        # Sprint 36 - T05.6: Excluir chips já tentados
        if excluir_chips:
            chips_antes = len(chips)
            chips = [c for c in chips if c["id"] not in excluir_chips]
            if chips_antes != len(chips):
                logger.debug(
                    f"[ChipSelector] Excluídos {chips_antes - len(chips)} chips já tentados"
                )

        if not chips:
            # Sprint 36 - T05.7: Tentar fallback mode se ainda não tentou
            if not fallback_mode:
                logger.warning(
                    f"[ChipSelector] Sem chips com trust alto para {tipo_mensagem}, "
                    f"tentando fallback mode"
                )
                return await self.selecionar_chip(
                    tipo_mensagem=tipo_mensagem,
                    conversa_id=conversa_id,
                    telefone_destino=telefone_destino,
                    excluir_chips=excluir_chips,
                    fallback_mode=True,
                )

            logger.warning(f"[ChipSelector] Nenhum chip disponivel para {tipo_mensagem}")
            return None

        # 3. Verificar historico com o contato (affinity)
        if telefone_destino:
            chip_historico = await self._buscar_chip_historico(telefone_destino, chips)
            if chip_historico:
                return chip_historico

        # 4. Selecionar por menor uso
        chip_selecionado = await self._selecionar_menor_uso(chips)

        # Sprint 36 - T10.1: Log de decisão
        await self._registrar_selecao(
            tipo_mensagem=tipo_mensagem,
            chips_elegiveis=chips,
            chip_selecionado=chip_selecionado,
            motivo="menor_uso",
            conversa_id=conversa_id,
            telefone_destino=telefone_destino,
            fallback_mode=fallback_mode,
        )

        logger.debug(
            f"[ChipSelector] Selecionado {chip_selecionado['telefone']} para {tipo_mensagem}"
        )

        return chip_selecionado

    async def _buscar_chip_conversa(self, conversa_id: str) -> Optional[Dict]:
        """
        Busca chip atualmente associado a conversa.

        Sprint 36 - T11.6: Também verifica se chip está conectado.
        Sprint 27: Suporte multi-provider (Z-API não usa evolution_connected).
        """
        # Usar relationship hint para evitar ambiguidade
        # (conversation_chips tem 2 FKs para chips: chip_id e migrated_from)
        result = (
            supabase.table("conversation_chips")
            .select("chip_id, chips!conversation_chips_chip_id_fkey(*)")
            .eq("conversa_id", conversa_id)
            .eq("active", True)
            .limit(1)
            .execute()
        )

        if result.data and result.data[0].get("chips"):
            chip = result.data[0]["chips"]

            # Sprint 27: Verificar conexão baseado no provider
            provider = chip.get("provider", "evolution")

            if provider == "z-api":
                # Z-API: considerar conectado se status = 'active'
                if chip.get("status") != "active":
                    logger.warning(
                        f"[ChipSelector] Chip Z-API {chip.get('telefone')} "
                        f"não está ativo, ignorando afinidade"
                    )
                    return None
            elif provider == "meta":
                # Sprint 66: Meta Cloud API — sempre conectado, verificar quality
                if chip.get("meta_quality_rating") == "RED":
                    logger.warning(
                        f"[ChipSelector] Chip Meta {chip.get('telefone')} "
                        f"quality RED, ignorando afinidade"
                    )
                    return None
            else:
                # Evolution: verificar evolution_connected
                if not chip.get("evolution_connected"):
                    logger.warning(
                        f"[ChipSelector] Chip Evolution {chip.get('telefone')} "
                        f"não está conectado, ignorando afinidade"
                    )
                    return None

            return chip
        return None

    async def _buscar_chips_elegiveis(
        self,
        tipo_mensagem: TipoMensagem,
        fallback_mode: bool = False,
    ) -> List[Dict]:
        """
        Busca chips que podem enviar o tipo de mensagem.

        Criterios por tipo (normal):
        - prospeccao: Trust >= 80, pode_prospectar = true
        - followup: Trust >= 60, pode_followup = true
        - resposta: Trust >= 40, pode_responder = true

        Criterios por tipo (fallback - Sprint 36 T05.7):
        - prospeccao: Trust >= 60, pode_prospectar = true
        - followup: Trust >= 40, pode_followup = true
        - resposta: Trust >= 20, pode_responder = true

        Sprint 36 - T11.6: Verifica conexão (evolution_connected para Evolution)
        Sprint 27: Suporte multi-provider (Z-API não requer evolution_connected)
        """
        query = supabase.table("chips").select("*").eq("status", "active")

        # Sprint 51 - E03: NUNCA selecionar chips do tipo 'listener'
        # Chips listener são exclusivos para escuta de grupos (read-only)
        query = query.neq("tipo", "listener")
        # Issue #88: Chips scraper são exclusivos para coleta (não enviam)
        query = query.neq("tipo", "scraper")

        # Sprint 27: NÃO filtrar por evolution_connected na query
        # A verificação de conexão é feita no loop, pois depende do provider

        # Filtrar por permissao e trust minimo
        # Sprint 36 - T05.7: Thresholds reduzidos em fallback mode
        if tipo_mensagem == "prospeccao":
            min_trust = 60 if fallback_mode else 80
            query = query.eq("pode_prospectar", True).gte("trust_score", min_trust)
        elif tipo_mensagem == "followup":
            min_trust = 40 if fallback_mode else 60
            query = query.eq("pode_followup", True).gte("trust_score", min_trust)
        else:  # resposta
            min_trust = 20 if fallback_mode else 40
            query = query.eq("pode_responder", True).gte("trust_score", min_trust)

        if fallback_mode:
            logger.info(
                f"[ChipSelector] Usando threshold emergencial: "
                f"trust >= {min_trust} para {tipo_mensagem}"
            )

        result = query.order("trust_score", desc=True).execute()

        # Sprint 59 Epic 4: Batch query de msgs/hora para todos os chips candidatos
        all_chip_ids = [c["id"] for c in result.data or []]
        uso_hora_batch = await self._contar_msgs_ultima_hora_batch(all_chip_ids)

        # Filtrar por limite de uso
        chips_disponiveis = []
        chips_desconectados = 0
        chips_circuit_aberto = 0  # Sprint 36 - T09.2

        for chip in result.data or []:
            # Sprint 27: Verificar conexão baseado no provider
            provider = chip.get("provider", "evolution")

            if provider == "z-api":
                # Z-API: já filtrado por status = 'active' na query
                pass
            elif provider == "meta":
                # Sprint 66: Meta Cloud API — não precisa de evolution_connected
                # Verificar quality rating
                if chip.get("meta_quality_rating") == "RED":
                    logger.debug(
                        f"[ChipSelector] Chip Meta {chip['telefone']} quality RED"
                    )
                    chips_desconectados += 1
                    continue
            else:
                # Evolution: verificar evolution_connected
                if not chip.get("evolution_connected"):
                    logger.debug(f"[ChipSelector] Chip Evolution {chip['telefone']} não conectado")
                    chips_desconectados += 1
                    continue

            # Sprint 36 - T11.6: Verificar cooldown de conexão
            if chip.get("connection_cooldown_until"):
                try:
                    cooldown_until = datetime.fromisoformat(
                        chip["connection_cooldown_until"].replace("Z", "+00:00")
                    )
                    if datetime.now(timezone.utc) < cooldown_until:
                        logger.debug(
                            f"[ChipSelector] Chip {chip['telefone']} em cooldown de conexão"
                        )
                        chips_desconectados += 1
                        continue
                except (ValueError, TypeError):
                    pass  # Ignorar se formato invalido

            # Verificar limite diario
            limite_dia = chip.get("limite_dia", 100)
            msgs_hoje = chip.get("msgs_enviadas_hoje", 0)

            if msgs_hoje >= limite_dia:
                logger.debug(f"[ChipSelector] Chip {chip['telefone']} no limite diario")
                continue

            # Sprint 59 Epic 4: Usar batch result ao invés de query individual
            uso_hora = uso_hora_batch.get(chip["id"], 0)
            limite_hora = chip.get("limite_hora", 20)

            if uso_hora >= limite_hora:
                logger.debug(f"[ChipSelector] Chip {chip['telefone']} no limite horario")
                continue

            # Verificar cooldown geral
            if chip.get("cooldown_until"):
                cooldown_until = datetime.fromisoformat(
                    chip["cooldown_until"].replace("Z", "+00:00")
                )
                if datetime.now(timezone.utc) < cooldown_until:
                    logger.debug(f"[ChipSelector] Chip {chip['telefone']} em cooldown")
                    continue

            # Sprint 36 - T09.2: Verificar circuit breaker do chip
            if not ChipCircuitBreaker.pode_usar_chip(chip["id"]):
                circuit = ChipCircuitBreaker.get_circuit(chip["id"], chip.get("telefone", ""))
                logger.debug(
                    f"[ChipSelector] Chip {chip['telefone']} descartado: "
                    f"circuit breaker {circuit.estado.value}"
                )
                chips_circuit_aberto += 1
                continue

            chip["_uso_hora"] = uso_hora
            chips_disponiveis.append(chip)

        # Log de chips descartados por conexão
        if chips_desconectados > 0:
            logger.warning(
                f"[ChipSelector] {chips_desconectados} chips descartados por cooldown de conexão"
            )

        # Sprint 36 - T09.2: Log de chips com circuit aberto
        if chips_circuit_aberto > 0:
            logger.warning(
                f"[ChipSelector] {chips_circuit_aberto} chips descartados por circuit breaker aberto"
            )

        return chips_disponiveis

    async def _buscar_chip_historico(self, telefone: str, chips: List[Dict]) -> Optional[Dict]:
        """
        Verifica se algum dos chips ja conversou com este telefone.
        Preferir para manter consistencia (affinity).
        """
        chip_ids = [c["id"] for c in chips]

        result = (
            supabase.table("chip_interactions")
            .select("chip_id")
            .eq("destinatario", telefone)
            .in_("chip_id", chip_ids)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if result.data:
            chip_id = result.data[0]["chip_id"]
            for chip in chips:
                if chip["id"] == chip_id:
                    logger.debug(f"[ChipSelector] Usando chip com historico: {chip['telefone']}")
                    return chip

        return None

    async def _contar_msgs_ultima_hora(self, chip_id: str) -> int:
        """Conta mensagens enviadas na ultima hora."""
        uma_hora_atras = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        result = (
            supabase.table("chip_interactions")
            .select("id", count="exact")
            .eq("chip_id", chip_id)
            .eq("tipo", "msg_enviada")
            .gte("created_at", uma_hora_atras)
            .execute()
        )

        return result.count or 0

    async def _contar_msgs_ultima_hora_batch(self, chip_ids: list) -> dict:
        """
        Sprint 59 Epic 4: Conta msgs/hora de todos os chips em 1 query.

        Substitui N chamadas individuais a _contar_msgs_ultima_hora por 1 query
        com IN filter + contagem em Python.

        Returns:
            dict[chip_id -> count]
        """
        if not chip_ids:
            return {}

        uma_hora_atras = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        result = (
            supabase.table("chip_interactions")
            .select("chip_id")
            .in_("chip_id", chip_ids)
            .eq("tipo", "msg_enviada")
            .gte("created_at", uma_hora_atras)
            .execute()
        )

        contagem: dict = {}
        for row in result.data or []:
            cid = row["chip_id"]
            contagem[cid] = contagem.get(cid, 0) + 1

        return contagem

    async def _selecionar_menor_uso(self, chips: List[Dict]) -> Dict:
        """Seleciona chip com menor uso na hora atual."""
        # Ordenar por uso da hora (menor primeiro), depois por Trust (maior primeiro)
        return sorted(chips, key=lambda c: (c.get("_uso_hora", 0), -(c.get("trust_score", 0))))[0]

    async def _reservar_slot_atomico(self, chip: Dict) -> bool:
        """
        Sprint 44 T01.8: Reserva slot de envio atomicamente via Redis INCR.

        Resolve race condition onde múltiplos workers podem selecionar o mesmo chip
        simultaneamente, ultrapassando o limite.

        Args:
            chip: Dict com dados do chip (id, limite_hora)

        Returns:
            True se reserva bem sucedida, False se chip atingiu limite
        """
        chip_id = chip["id"]
        limite_hora = chip.get("limite_hora", 20)

        # Key com granularidade de hora (YYYYMMDDHH)
        hora_atual = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        key = f"chip:{chip_id}:hora:{hora_atual}"

        try:
            # INCR atômico - se key não existe, cria com valor 1
            count = await redis_client.incr(key)

            # Primeira reserva da hora - definir TTL
            if count == 1:
                await redis_client.expire(key, 3700)  # 1h + margem

            # Verificar se ainda está dentro do limite
            if count <= limite_hora:
                logger.debug(
                    f"[ChipSelector] T01.8: Slot reservado para chip {chip.get('telefone', '')[-4:]}: "
                    f"{count}/{limite_hora}"
                )
                return True
            else:
                # Excedeu limite - reverter INCR
                await redis_client.decr(key)
                logger.debug(
                    f"[ChipSelector] T01.8: Chip {chip.get('telefone', '')[-4:]} atingiu limite "
                    f"(tentativa {count}/{limite_hora}), revertendo"
                )
                return False

        except Exception as e:
            # Em caso de erro Redis, usar fallback sem reserva atômica
            logger.warning(f"[ChipSelector] T01.8: Erro Redis, fallback sem atomicidade: {e}")
            return True  # Permitir seleção, depender da verificação de banco

    async def selecionar_chip_com_reserva(
        self,
        tipo_mensagem: TipoMensagem,
        conversa_id: Optional[str] = None,
        telefone_destino: Optional[str] = None,
        excluir_chips: Optional[List[str]] = None,
        fallback_mode: bool = False,
    ) -> Optional[Dict]:
        """
        Sprint 44 T01.8: Seleciona chip com reserva atômica de slot.

        Versão melhorada de selecionar_chip() que usa Redis INCR para
        garantir atomicidade e evitar race conditions.

        Args:
            tipo_mensagem: 'prospeccao', 'followup', ou 'resposta'
            conversa_id: ID da conversa (para continuidade)
            telefone_destino: Telefone do destinatario
            excluir_chips: Lista de chip_ids a excluir (já tentados)
            fallback_mode: Se True, usa thresholds reduzidos

        Returns:
            Chip selecionado com slot reservado ou None
        """
        if not self.config:
            await self.carregar_config()

        excluir_chips = excluir_chips or []

        # 1. Se eh resposta e tem conversa, manter no mesmo chip
        if tipo_mensagem == "resposta" and conversa_id:
            chip_existente = await self._buscar_chip_conversa(conversa_id)
            if chip_existente and chip_existente.get("pode_responder"):
                if chip_existente["id"] not in excluir_chips:
                    # Verificar reserva atômica
                    if await self._reservar_slot_atomico(chip_existente):
                        logger.debug(
                            f"[ChipSelector] T01.8: Usando chip existente com reserva: "
                            f"{chip_existente['telefone']}"
                        )
                        return chip_existente

        # 2. Buscar chips elegiveis
        chips = await self._buscar_chips_elegiveis(tipo_mensagem, fallback_mode)

        # Excluir chips já tentados
        if excluir_chips:
            chips = [c for c in chips if c["id"] not in excluir_chips]

        if not chips:
            if not fallback_mode:
                return await self.selecionar_chip_com_reserva(
                    tipo_mensagem=tipo_mensagem,
                    conversa_id=conversa_id,
                    telefone_destino=telefone_destino,
                    excluir_chips=excluir_chips,
                    fallback_mode=True,
                )
            logger.warning(f"[ChipSelector] T01.8: Nenhum chip disponível para {tipo_mensagem}")
            return None

        # 3. Verificar historico com o contato (affinity)
        if telefone_destino:
            chip_historico = await self._buscar_chip_historico(telefone_destino, chips)
            if chip_historico:
                if await self._reservar_slot_atomico(chip_historico):
                    return chip_historico
                # Se não conseguiu reservar, remover da lista e continuar
                chips = [c for c in chips if c["id"] != chip_historico["id"]]

        # 4. Tentar selecionar por menor uso com reserva atômica
        # Ordenar por uso (menor primeiro), trust (maior primeiro)
        chips_ordenados = sorted(
            chips, key=lambda c: (c.get("_uso_hora", 0), -(c.get("trust_score", 0)))
        )

        for chip in chips_ordenados:
            if await self._reservar_slot_atomico(chip):
                # Registrar seleção
                await self._registrar_selecao(
                    tipo_mensagem=tipo_mensagem,
                    chips_elegiveis=chips,
                    chip_selecionado=chip,
                    motivo="menor_uso_com_reserva",
                    conversa_id=conversa_id,
                    telefone_destino=telefone_destino,
                    fallback_mode=fallback_mode,
                )

                logger.debug(
                    f"[ChipSelector] T01.8: Selecionado {chip['telefone']} "
                    f"com reserva atômica para {tipo_mensagem}"
                )
                return chip

        # Nenhum chip conseguiu reservar slot
        logger.warning(
            f"[ChipSelector] T01.8: Todos os {len(chips)} chips atingiram limite "
            f"para {tipo_mensagem}"
        )
        return None

    async def _registrar_selecao(
        self,
        tipo_mensagem: TipoMensagem,
        chips_elegiveis: List[Dict],
        chip_selecionado: Optional[Dict],
        motivo: str,
        conversa_id: Optional[str] = None,
        telefone_destino: Optional[str] = None,
        fallback_mode: bool = False,
    ) -> None:
        """
        Sprint 36 - T10.1: Registra decisão de seleção para auditoria.

        Args:
            tipo_mensagem: Tipo da mensagem
            chips_elegiveis: Lista de chips considerados
            chip_selecionado: Chip que foi selecionado (ou None)
            motivo: Motivo da seleção
            conversa_id: ID da conversa (opcional)
            telefone_destino: Telefone destino (opcional)
            fallback_mode: Se estava em modo fallback
        """
        try:
            supabase.table("chip_selection_log").insert(
                {
                    "tipo_mensagem": tipo_mensagem,
                    "conversa_id": conversa_id,
                    "telefone_destino": telefone_destino[-4:] if telefone_destino else None,
                    "chips_elegiveis_count": len(chips_elegiveis),
                    "chips_elegiveis_ids": [c["id"] for c in chips_elegiveis[:10]],  # Limitar
                    "chip_selecionado_id": chip_selecionado["id"] if chip_selecionado else None,
                    "chip_selecionado_telefone": (
                        chip_selecionado.get("telefone")[-4:]
                        if chip_selecionado and chip_selecionado.get("telefone")
                        else None
                    ),
                    "motivo": motivo,
                    "fallback_mode": fallback_mode,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ).execute()

        except Exception as e:
            # Não falhar seleção por erro de log
            logger.debug(f"[ChipSelector] Erro ao registrar seleção: {e}")

    async def registrar_envio(
        self,
        chip_id: str,
        conversa_id: str,
        tipo_mensagem: TipoMensagem,
        telefone_destino: str,
    ):
        """
        Registra envio para metricas e mapeamento.

        Args:
            chip_id: ID do chip usado
            conversa_id: ID da conversa
            tipo_mensagem: Tipo da mensagem
            telefone_destino: Telefone destino
        """
        # 1. Atualizar/criar mapeamento conversa-chip
        existing = (
            supabase.table("conversation_chips")
            .select("id")
            .eq("conversa_id", conversa_id)
            .eq("active", True)
            .execute()
        )

        if existing.data:
            # Atualizar se o chip mudou
            supabase.table("conversation_chips").update(
                {
                    "chip_id": chip_id,
                }
            ).eq("conversa_id", conversa_id).eq("active", True).execute()
        else:
            # Criar novo mapeamento
            supabase.table("conversation_chips").insert(
                {
                    "conversa_id": conversa_id,
                    "chip_id": chip_id,
                    "active": True,
                }
            ).execute()

        # 2. Registrar interacao
        supabase.table("chip_interactions").insert(
            {
                "chip_id": chip_id,
                "tipo": "msg_enviada",
                "destinatario": telefone_destino,
                "metadata": {"tipo_mensagem": tipo_mensagem},
            }
        ).execute()

        # 3. Incrementar contadores
        try:
            supabase.rpc(
                "incrementar_msgs_chip",
                {
                    "p_chip_id": chip_id,
                },
            ).execute()
        except Exception as e:
            logger.warning(f"[ChipSelector] Erro ao incrementar contador: {e}")
            # Fallback: update direto
            supabase.table("chips").update(
                {
                    "msgs_enviadas_hoje": supabase.table("chips")
                    .select("msgs_enviadas_hoje")
                    .eq("id", chip_id)
                    .single()
                    .execute()
                    .data.get("msgs_enviadas_hoje", 0)
                    + 1
                }
            ).eq("id", chip_id).execute()

    async def registrar_recebimento(
        self,
        chip_id: str,
        telefone_remetente: str,
    ):
        """
        Registra mensagem recebida.

        Args:
            chip_id: ID do chip que recebeu
            telefone_remetente: Telefone de quem enviou
        """
        supabase.table("chip_interactions").insert(
            {
                "chip_id": chip_id,
                "tipo": "msg_recebida",
                "destinatario": telefone_remetente,
            }
        ).execute()

        # Incrementar contador de recebidas
        result = (
            supabase.table("chips")
            .select("msgs_recebidas_total, msgs_recebidas_hoje")
            .eq("id", chip_id)
            .single()
            .execute()
        )

        if result.data:
            supabase.table("chips").update(
                {
                    "msgs_recebidas_total": (result.data.get("msgs_recebidas_total") or 0) + 1,
                    "msgs_recebidas_hoje": (result.data.get("msgs_recebidas_hoje") or 0) + 1,
                }
            ).eq("id", chip_id).execute()

    async def obter_chip_por_instance(self, instance_name: str) -> Optional[Dict]:
        """
        Busca chip pelo nome da instancia Evolution.

        Args:
            instance_name: Nome da instancia

        Returns:
            Chip ou None
        """
        result = (
            supabase.table("chips")
            .select("*")
            .eq("instance_name", instance_name)
            .single()
            .execute()
        )

        return result.data if result.data else None

    async def listar_chips_disponiveis(
        self, tipo_mensagem: Optional[TipoMensagem] = None
    ) -> List[Dict]:
        """
        Lista chips disponiveis para envio.

        Args:
            tipo_mensagem: Filtrar por tipo (opcional)

        Returns:
            Lista de chips com metricas
        """
        if tipo_mensagem:
            return await self._buscar_chips_elegiveis(tipo_mensagem)

        result = (
            supabase.table("chips")
            .select("*")
            .eq("status", "active")
            .order("trust_score", desc=True)
            .execute()
        )

        return result.data or []

    async def aplicar_rampup_gradual(
        self, chip_id: str, motivo: str = "recuperacao_cooldown"
    ) -> Dict:
        """
        Sprint 36 - T10.3: Aplica ramp-up gradual para chip saindo de restrição.

        Quando um chip sai de cooldown ou tinha trust baixo, não volta
        imediatamente para capacidade total. Isso evita sobrecarga e
        permite monitorar a recuperação.

        Níveis de ramp-up:
        - Fase 1 (0-2h): 25% da capacidade
        - Fase 2 (2-6h): 50% da capacidade
        - Fase 3 (6-12h): 75% da capacidade
        - Fase 4 (12h+): 100% da capacidade

        Args:
            chip_id: ID do chip
            motivo: Motivo do ramp-up

        Returns:
            {
                "chip_id": str,
                "rampup_inicio": datetime,
                "limite_atual_pct": int,
                "fase": int
            }
        """
        agora = datetime.now(timezone.utc)

        try:
            # Buscar chip
            chip_result = (
                supabase.table("chips")
                .select("id, telefone, limite_hora, limite_dia")
                .eq("id", chip_id)
                .single()
                .execute()
            )

            if not chip_result.data:
                return {"erro": "Chip não encontrado"}

            chip = chip_result.data

            # Aplicar ramp-up: definir início e fase inicial
            supabase.table("chips").update(
                {
                    "rampup_inicio": agora.isoformat(),
                    "rampup_fase": 1,
                    "rampup_motivo": motivo,
                    "updated_at": agora.isoformat(),
                }
            ).eq("id", chip_id).execute()

            logger.info(
                f"[ChipSelector] T10.3: Ramp-up iniciado para chip {chip.get('telefone')[-4:]}: "
                f"fase 1 (25%), motivo={motivo}"
            )

            return {
                "chip_id": chip_id,
                "telefone": chip.get("telefone", "")[-4:],
                "rampup_inicio": agora.isoformat(),
                "limite_atual_pct": 25,
                "fase": 1,
                "motivo": motivo,
            }

        except Exception as e:
            logger.error(f"[ChipSelector] Erro ao aplicar ramp-up: {e}")
            return {"erro": str(e)}

    def calcular_limite_rampup(self, chip: Dict) -> Dict:
        """
        Sprint 36 - T10.3: Calcula limite atual baseado no ramp-up.

        Args:
            chip: Dict com dados do chip

        Returns:
            {
                "limite_hora": int,
                "limite_dia": int,
                "fase": int,
                "percentual": int,
                "em_rampup": bool
            }
        """
        limite_hora_base = chip.get("limite_hora", 20)
        limite_dia_base = chip.get("limite_dia", 100)

        # Verificar se está em ramp-up
        rampup_inicio = chip.get("rampup_inicio")
        if not rampup_inicio:
            return {
                "limite_hora": limite_hora_base,
                "limite_dia": limite_dia_base,
                "fase": 0,
                "percentual": 100,
                "em_rampup": False,
            }

        try:
            if isinstance(rampup_inicio, str):
                rampup_inicio = datetime.fromisoformat(rampup_inicio.replace("Z", "+00:00"))

            horas_desde_inicio = (datetime.now(timezone.utc) - rampup_inicio).total_seconds() / 3600

            # Determinar fase e percentual
            if horas_desde_inicio < 2:
                fase = 1
                percentual = 25
            elif horas_desde_inicio < 6:
                fase = 2
                percentual = 50
            elif horas_desde_inicio < 12:
                fase = 3
                percentual = 75
            else:
                # Ramp-up completo
                fase = 4
                percentual = 100

            return {
                "limite_hora": int(limite_hora_base * percentual / 100),
                "limite_dia": int(limite_dia_base * percentual / 100),
                "fase": fase,
                "percentual": percentual,
                "em_rampup": percentual < 100,
                "horas_restantes": max(0, 12 - horas_desde_inicio) if fase < 4 else 0,
            }

        except Exception:
            # Em caso de erro, usar limite padrão
            return {
                "limite_hora": limite_hora_base,
                "limite_dia": limite_dia_base,
                "fase": 0,
                "percentual": 100,
                "em_rampup": False,
            }

    async def atualizar_fases_rampup(self) -> Dict:
        """
        Sprint 36 - T10.3: Atualiza fases de ramp-up de todos os chips.

        Deve ser chamado periodicamente por um job.

        Returns:
            {
                "chips_atualizados": int,
                "chips_finalizados": int,
                "detalhes": List[Dict]
            }
        """
        agora = datetime.now(timezone.utc)

        try:
            # Buscar chips em ramp-up
            result = (
                supabase.table("chips")
                .select("id, telefone, rampup_inicio, rampup_fase")
                .eq("status", "active")
                .not_.is_("rampup_inicio", "null")
                .execute()
            )

            chips_atualizados = 0
            chips_finalizados = 0
            detalhes = []

            # Sprint 59 Epic 4.5: Agrupar chips por nova fase para batch UPDATE
            finalizados_ids = []
            por_fase: Dict[int, list] = {}  # fase -> [chip_ids]

            for chip in result.data or []:
                chip_id = chip["id"]
                limite_info = self.calcular_limite_rampup(chip)
                nova_fase = limite_info["fase"]
                fase_atual = chip.get("rampup_fase") or 1

                if nova_fase != fase_atual:
                    if nova_fase == 4:
                        finalizados_ids.append(chip_id)
                        logger.info(
                            f"[ChipSelector] Ramp-up finalizado para chip {chip.get('telefone')[-4:]}"
                        )
                    else:
                        por_fase.setdefault(nova_fase, []).append(chip_id)
                        logger.info(
                            f"[ChipSelector] Ramp-up fase {nova_fase} ({limite_info['percentual']}%) "
                            f"para chip {chip.get('telefone')[-4:]}"
                        )

                    chips_atualizados += 1
                    detalhes.append(
                        {
                            "chip_id": chip_id,
                            "telefone": chip.get("telefone", "")[-4:],
                            "fase_anterior": fase_atual,
                            "fase_nova": nova_fase,
                            "percentual": limite_info["percentual"],
                        }
                    )

            # Batch UPDATE: finalizados (1 query)
            if finalizados_ids:
                supabase.table("chips").update(
                    {
                        "rampup_inicio": None,
                        "rampup_fase": None,
                        "rampup_motivo": None,
                        "updated_at": agora.isoformat(),
                    }
                ).in_("id", finalizados_ids).execute()
                chips_finalizados = len(finalizados_ids)

            # Batch UPDATE: cada fase (1 query por fase)
            for fase, ids in por_fase.items():
                supabase.table("chips").update(
                    {
                        "rampup_fase": fase,
                        "updated_at": agora.isoformat(),
                    }
                ).in_("id", ids).execute()

            return {
                "chips_atualizados": chips_atualizados,
                "chips_finalizados": chips_finalizados,
                "detalhes": detalhes,
            }

        except Exception as e:
            logger.error(f"[ChipSelector] Erro ao atualizar fases ramp-up: {e}")
            return {"erro": str(e)}

    async def listar_chips_em_rampup(self) -> List[Dict]:
        """
        Sprint 36 - T10.3: Lista chips atualmente em ramp-up.

        Returns:
            Lista de chips com informações de ramp-up
        """
        result = (
            supabase.table("chips")
            .select(
                "id, telefone, trust_score, rampup_inicio, rampup_fase, rampup_motivo, "
                "limite_hora, limite_dia"
            )
            .eq("status", "active")
            .not_.is_("rampup_inicio", "null")
            .execute()
        )

        chips_rampup = []
        for chip in result.data or []:
            limite_info = self.calcular_limite_rampup(chip)
            chips_rampup.append(
                {
                    **chip,
                    **limite_info,
                }
            )

        return chips_rampup


# Singleton
chip_selector = ChipSelector()
