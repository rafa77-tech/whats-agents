"""
Chip Selector - Selecao inteligente de chip por tipo de mensagem.

Sprint 26 - E02

Considera:
- Trust Score do chip
- Permissoes (pode_prospectar, pode_followup, pode_responder)
- Uso atual (msgs/hora, msgs/dia)
- Historico com o contato
- Continuidade de conversa
"""

import logging
from typing import Optional, List, Dict, Literal
from datetime import datetime, timedelta, timezone

from app.services.supabase import supabase

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
    ) -> Optional[Dict]:
        """
        Seleciona melhor chip para enviar mensagem.

        Args:
            tipo_mensagem: 'prospeccao', 'followup', ou 'resposta'
            conversa_id: ID da conversa (para continuidade)
            telefone_destino: Telefone do destinatario

        Returns:
            Chip selecionado ou None
        """
        if not self.config:
            await self.carregar_config()

        # 1. Se eh resposta e tem conversa, manter no mesmo chip
        if tipo_mensagem == "resposta" and conversa_id:
            chip_existente = await self._buscar_chip_conversa(conversa_id)
            if chip_existente and chip_existente.get("pode_responder"):
                logger.debug(f"[ChipSelector] Usando chip existente da conversa: {chip_existente['telefone']}")
                return chip_existente

        # 2. Buscar chips elegiveis
        chips = await self._buscar_chips_elegiveis(tipo_mensagem)

        if not chips:
            logger.warning(f"[ChipSelector] Nenhum chip disponivel para {tipo_mensagem}")
            return None

        # 3. Verificar historico com o contato (affinity)
        if telefone_destino:
            chip_historico = await self._buscar_chip_historico(
                telefone_destino, chips
            )
            if chip_historico:
                return chip_historico

        # 4. Selecionar por menor uso
        chip_selecionado = await self._selecionar_menor_uso(chips)

        logger.debug(
            f"[ChipSelector] Selecionado {chip_selecionado['telefone']} "
            f"para {tipo_mensagem}"
        )

        return chip_selecionado

    async def _buscar_chip_conversa(self, conversa_id: str) -> Optional[Dict]:
        """Busca chip atualmente associado a conversa."""
        # Usar relationship hint para evitar ambiguidade
        # (conversation_chips tem 2 FKs para chips: chip_id e migrated_from)
        result = supabase.table("conversation_chips").select(
            "chip_id, chips!conversation_chips_chip_id_fkey(*)"
        ).eq(
            "conversa_id", conversa_id
        ).eq(
            "active", True
        ).limit(1).execute()

        if result.data and result.data[0].get("chips"):
            return result.data[0]["chips"]
        return None

    async def _buscar_chips_elegiveis(self, tipo_mensagem: TipoMensagem) -> List[Dict]:
        """
        Busca chips que podem enviar o tipo de mensagem.

        Criterios por tipo:
        - prospeccao: Trust >= 80, pode_prospectar = true
        - followup: Trust >= 60, pode_followup = true
        - resposta: Trust >= 40, pode_responder = true
        """
        query = supabase.table("chips").select("*").eq("status", "active")

        # Filtrar por permissao e trust minimo
        if tipo_mensagem == "prospeccao":
            query = query.eq("pode_prospectar", True).gte("trust_score", 80)
        elif tipo_mensagem == "followup":
            query = query.eq("pode_followup", True).gte("trust_score", 60)
        else:  # resposta
            query = query.eq("pode_responder", True).gte("trust_score", 40)

        result = query.order("trust_score", desc=True).execute()

        # Filtrar por limite de uso
        chips_disponiveis = []
        for chip in result.data or []:
            # Verificar limite diario
            limite_dia = chip.get("limite_dia", 100)
            msgs_hoje = chip.get("msgs_enviadas_hoje", 0)

            if msgs_hoje >= limite_dia:
                logger.debug(f"[ChipSelector] Chip {chip['telefone']} no limite diario")
                continue

            # Verificar limite por hora
            uso_hora = await self._contar_msgs_ultima_hora(chip["id"])
            limite_hora = chip.get("limite_hora", 20)

            if uso_hora >= limite_hora:
                logger.debug(f"[ChipSelector] Chip {chip['telefone']} no limite horario")
                continue

            # Verificar cooldown
            if chip.get("cooldown_until"):
                cooldown_until = datetime.fromisoformat(
                    chip["cooldown_until"].replace("Z", "+00:00")
                )
                if datetime.now(timezone.utc) < cooldown_until:
                    logger.debug(f"[ChipSelector] Chip {chip['telefone']} em cooldown")
                    continue

            chip["_uso_hora"] = uso_hora
            chips_disponiveis.append(chip)

        return chips_disponiveis

    async def _buscar_chip_historico(
        self,
        telefone: str,
        chips: List[Dict]
    ) -> Optional[Dict]:
        """
        Verifica se algum dos chips ja conversou com este telefone.
        Preferir para manter consistencia (affinity).
        """
        chip_ids = [c["id"] for c in chips]

        result = supabase.table("chip_interactions").select(
            "chip_id"
        ).eq(
            "destinatario", telefone
        ).in_(
            "chip_id", chip_ids
        ).order(
            "created_at", desc=True
        ).limit(1).execute()

        if result.data:
            chip_id = result.data[0]["chip_id"]
            for chip in chips:
                if chip["id"] == chip_id:
                    logger.debug(
                        f"[ChipSelector] Usando chip com historico: {chip['telefone']}"
                    )
                    return chip

        return None

    async def _contar_msgs_ultima_hora(self, chip_id: str) -> int:
        """Conta mensagens enviadas na ultima hora."""
        uma_hora_atras = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        result = supabase.table("chip_interactions").select(
            "id", count="exact"
        ).eq(
            "chip_id", chip_id
        ).eq(
            "tipo", "msg_enviada"
        ).gte(
            "created_at", uma_hora_atras
        ).execute()

        return result.count or 0

    async def _selecionar_menor_uso(self, chips: List[Dict]) -> Dict:
        """Seleciona chip com menor uso na hora atual."""
        # Ordenar por uso da hora (menor primeiro), depois por Trust (maior primeiro)
        return sorted(
            chips,
            key=lambda c: (c.get("_uso_hora", 0), -(c.get("trust_score", 0)))
        )[0]

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
        existing = supabase.table("conversation_chips").select("id").eq(
            "conversa_id", conversa_id
        ).eq(
            "active", True
        ).execute()

        if existing.data:
            # Atualizar se o chip mudou
            supabase.table("conversation_chips").update({
                "chip_id": chip_id,
            }).eq("conversa_id", conversa_id).eq("active", True).execute()
        else:
            # Criar novo mapeamento
            supabase.table("conversation_chips").insert({
                "conversa_id": conversa_id,
                "chip_id": chip_id,
                "active": True,
            }).execute()

        # 2. Registrar interacao
        supabase.table("chip_interactions").insert({
            "chip_id": chip_id,
            "tipo": "msg_enviada",
            "destinatario": telefone_destino,
            "metadata": {"tipo_mensagem": tipo_mensagem},
        }).execute()

        # 3. Incrementar contadores
        try:
            supabase.rpc("incrementar_msgs_chip", {
                "p_chip_id": chip_id,
            }).execute()
        except Exception as e:
            logger.warning(f"[ChipSelector] Erro ao incrementar contador: {e}")
            # Fallback: update direto
            supabase.table("chips").update({
                "msgs_enviadas_hoje": supabase.table("chips").select(
                    "msgs_enviadas_hoje"
                ).eq("id", chip_id).single().execute().data.get("msgs_enviadas_hoje", 0) + 1
            }).eq("id", chip_id).execute()

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
        supabase.table("chip_interactions").insert({
            "chip_id": chip_id,
            "tipo": "msg_recebida",
            "destinatario": telefone_remetente,
        }).execute()

        # Incrementar contador de recebidas
        result = supabase.table("chips").select(
            "msgs_recebidas_total, msgs_recebidas_hoje"
        ).eq("id", chip_id).single().execute()

        if result.data:
            supabase.table("chips").update({
                "msgs_recebidas_total": (result.data.get("msgs_recebidas_total") or 0) + 1,
                "msgs_recebidas_hoje": (result.data.get("msgs_recebidas_hoje") or 0) + 1,
            }).eq("id", chip_id).execute()

    async def obter_chip_por_instance(self, instance_name: str) -> Optional[Dict]:
        """
        Busca chip pelo nome da instancia Evolution.

        Args:
            instance_name: Nome da instancia

        Returns:
            Chip ou None
        """
        result = supabase.table("chips").select("*").eq(
            "instance_name", instance_name
        ).single().execute()

        return result.data if result.data else None

    async def listar_chips_disponiveis(
        self,
        tipo_mensagem: Optional[TipoMensagem] = None
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

        result = supabase.table("chips").select("*").eq(
            "status", "active"
        ).order("trust_score", desc=True).execute()

        return result.data or []


# Singleton
chip_selector = ChipSelector()
