"""
Service para resolução de especialidades.

Sprint 31 - S31.E5.1

Centraliza a lógica de buscar especialidades por nome,
incluindo normalização e cache.
"""

import logging
from typing import Optional

from app.services.supabase import supabase
from app.services.redis import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

# Cache TTL
CACHE_TTL_ESPECIALIDADE = 3600  # 1 hora


class EspecialidadeService:
    """
    Service para resolução de especialidades.

    Responsabilidades:
    - Buscar especialidade por nome (case insensitive)
    - Cache de resultados
    - Normalização de nomes
    """

    def __init__(self):
        """Inicializa o service."""
        self._cache_ttl = CACHE_TTL_ESPECIALIDADE

    @staticmethod
    def normalizar_nome(nome: str) -> str:
        """
        Normaliza nome de especialidade para busca.

        Args:
            nome: Nome original

        Returns:
            Nome normalizado (lowercase, stripped)
        """
        return nome.strip().lower()

    async def buscar_por_nome(self, nome: str) -> Optional[str]:
        """
        Busca ID da especialidade pelo nome (com cache).

        Args:
            nome: Nome da especialidade (ex: "Anestesiologia")

        Returns:
            UUID da especialidade ou None se não encontrada
        """
        if not nome:
            return None

        nome_normalizado = self.normalizar_nome(nome)
        cache_key = f"especialidade:nome:{nome_normalizado}"

        # Tentar cache
        cached = await cache_get_json(cache_key)
        if cached:
            logger.debug(f"Especialidade '{nome}' encontrada no cache")
            return cached.get("id")

        # Buscar no banco (case insensitive)
        try:
            response = (
                supabase.table("especialidades")
                .select("id, nome")
                .ilike("nome", f"%{nome_normalizado}%")
                .limit(1)
                .execute()
            )

            if response.data:
                especialidade = response.data[0]
                # Salvar no cache
                await cache_set_json(cache_key, especialidade, self._cache_ttl)
                logger.debug(f"Especialidade '{nome}' encontrada: {especialidade['id']}")
                return especialidade["id"]

            logger.warning(f"Especialidade '{nome}' não encontrada no banco")
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar especialidade por nome: {e}")
            return None

    async def resolver_especialidade_medico(
        self, especialidade_solicitada: Optional[str], medico: dict
    ) -> tuple[Optional[str], Optional[str], bool]:
        """
        Resolve a especialidade a ser usada na busca.

        Args:
            especialidade_solicitada: Nome solicitado pelo médico (ou None)
            medico: Dados do médico

        Returns:
            Tupla (especialidade_id, especialidade_nome, especialidade_diferente)
        """
        especialidade_medico = medico.get("especialidade")
        especialidade_id = None
        especialidade_nome = None
        especialidade_diferente = False

        # Se médico solicitou especialidade específica, usar ela
        if especialidade_solicitada:
            especialidade_id = await self.buscar_por_nome(especialidade_solicitada)
            if especialidade_id:
                especialidade_nome = especialidade_solicitada.title()
                # Verificar se é diferente da cadastrada
                if (
                    especialidade_medico
                    and especialidade_medico.lower() != especialidade_solicitada.lower()
                ):
                    especialidade_diferente = True
                    logger.info(
                        f"Medico pediu {especialidade_solicitada} mas cadastro é {especialidade_medico}"
                    )
            else:
                logger.warning(
                    f"Especialidade '{especialidade_solicitada}' não encontrada no banco"
                )
                return None, especialidade_solicitada, False
        else:
            # Usar especialidade cadastrada do médico
            especialidade_id = medico.get("especialidade_id")
            if not especialidade_id and especialidade_medico:
                especialidade_id = await self.buscar_por_nome(especialidade_medico)
            especialidade_nome = especialidade_medico

        return especialidade_id, especialidade_nome, especialidade_diferente


# Singleton factory
_instance: Optional[EspecialidadeService] = None


def get_especialidade_service() -> EspecialidadeService:
    """Retorna instância singleton do service."""
    global _instance
    if _instance is None:
        _instance = EspecialidadeService()
    return _instance
