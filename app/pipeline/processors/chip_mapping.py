"""
Processador de mapeamento conversa-chip.

Sprint 44 T03.3: Módulo separado.
"""
import logging

from app.core.tasks import safe_create_task
from ..base import PreProcessor, ProcessorContext, ProcessorResult

logger = logging.getLogger(__name__)


class ChipMappingProcessor(PreProcessor):
    """
    Registra mapeamento conversa-chip quando multi-chip esta habilitado.

    Sprint 26 E02: Garante que respostas saiam pelo mesmo chip que recebeu.

    Prioridade: 21 (logo apos load entities)
    """
    name = "chip_mapping"
    priority = 21

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        from app.core.config import settings

        # Verificar se multi-chip esta habilitado
        if not getattr(settings, "MULTI_CHIP_ENABLED", False):
            return ProcessorResult(success=True)

        # Extrair instance do payload
        instance_name = context.mensagem_raw.get("_evolution_instance")
        if not instance_name:
            logger.debug("[ChipMapping] Instance nao encontrada no payload")
            return ProcessorResult(success=True)

        conversa_id = context.conversa.get("id") if context.conversa else None
        if not conversa_id:
            return ProcessorResult(success=True)

        # Registrar mapeamento em background (nao bloqueia)
        safe_create_task(
            self._registrar_chip_conversa(instance_name, conversa_id, context.telefone),
            name="registrar_chip_conversa"
        )

        # Guardar no metadata para uso posterior
        context.metadata["chip_instance"] = instance_name

        return ProcessorResult(success=True)

    async def _registrar_chip_conversa(
        self,
        instance_name: str,
        conversa_id: str,
        telefone_remetente: str
    ):
        """Registra chip da conversa no banco."""
        try:
            from app.services.chips.selector import chip_selector

            # Buscar chip pela instance
            chip = await chip_selector.obter_chip_por_instance(instance_name)
            if not chip:
                logger.debug(f"[ChipMapping] Chip nao encontrado: {instance_name}")
                return

            chip_id = chip["id"]

            # Registrar recebimento (metricas)
            await chip_selector.registrar_recebimento(chip_id, telefone_remetente)

            # Atualizar/criar mapeamento conversa-chip
            from app.services.supabase import supabase

            existing = supabase.table("conversation_chips").select("id").eq(
                "conversa_id", conversa_id
            ).eq("active", True).execute()

            if existing.data:
                # Atualizar se mudou de chip
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

            logger.debug(
                f"[ChipMapping] Conversa {conversa_id[:8]} mapeada para chip {instance_name}"
            )

        except Exception as e:
            logger.warning(f"[ChipMapping] Erro ao registrar: {e}")
