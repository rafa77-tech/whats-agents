"""
BSUIDs Migration Compatibility Layer.

Sprint 70+ — Chunk 30.

v1: Passthrough (phone = phone).
Interface ready for when Meta rolls out BSUIDs.
"""

import logging


logger = logging.getLogger(__name__)


class BsuidCompat:
    """
    Camada de compatibilidade para BSUIDs (Business Scoped User IDs).

    Meta planeja migrar de phone numbers para BSUIDs.
    v1: Passthrough — usa telefone como identificador.
    """

    async def resolver_bsuid(
        self,
        telefone: str,
        waba_id: str,
    ) -> str:
        """
        Resolve BSUID para um telefone.

        v1: Retorna o próprio telefone (passthrough).
        Em versões futuras, buscará BSUID da Meta.

        Args:
            telefone: Número de telefone
            waba_id: WABA ID

        Returns:
            BSUID ou telefone (v1 passthrough)
        """
        # v1: passthrough
        return telefone

    async def resolver_telefone(
        self,
        bsuid: str,
        waba_id: str,
    ) -> str:
        """
        Resolve telefone a partir de um BSUID.

        v1: Retorna o próprio BSUID (passthrough).

        Args:
            bsuid: Business Scoped User ID
            waba_id: WABA ID

        Returns:
            Telefone ou BSUID (v1 passthrough)
        """
        # v1: passthrough
        return bsuid

    async def migrar_para_bsuid(self, waba_id: str) -> dict:
        """
        Migra registros para usar BSUIDs.

        v1: No-op — retorna resultado vazio.

        Args:
            waba_id: WABA ID para migrar

        Returns:
            Dict com resultado da migração
        """
        logger.info("[BsuidCompat] Migração BSUID ainda não disponível (v1 passthrough)")
        return {
            "success": True,
            "migrated": 0,
            "message": "v1 passthrough — migração não necessária",
        }

    def eh_bsuid(self, identificador: str) -> bool:
        """
        Verifica se identificador é um BSUID.

        v1: BSUIDs ainda não existem, retorna False.

        Args:
            identificador: String para verificar

        Returns:
            True se é BSUID
        """
        # BSUIDs da Meta terão formato específico quando lançados
        # v1: nenhum identificador é BSUID
        return False

    def normalizar_identificador(self, identificador: str) -> str:
        """
        Normaliza identificador (telefone ou BSUID).

        v1: Remove caracteres não-numéricos (assume telefone).

        Args:
            identificador: Telefone ou BSUID

        Returns:
            Identificador normalizado
        """
        if self.eh_bsuid(identificador):
            return identificador
        # Normalizar telefone
        return "".join(c for c in identificador if c.isdigit())


# Singleton
bsuid_compat = BsuidCompat()
