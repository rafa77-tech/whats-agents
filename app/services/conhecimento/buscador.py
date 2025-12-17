"""
Buscador semântico de conhecimento Julia.
"""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Cache TTL para buscas (5 minutos)
CACHE_TTL_BUSCA = 300


@dataclass
class ResultadoBusca:
    """Resultado de busca de conhecimento."""

    id: str
    arquivo: str
    secao: str
    conteudo: str
    tipo: str
    subtipo: Optional[str]
    tags: list[str]
    similaridade: float


class BuscadorConhecimento:
    """Busca semântica na base de conhecimento."""

    def __init__(self, threshold: float = 0.65, limite_padrao: int = 3):
        self.threshold = threshold
        self.limite_padrao = limite_padrao

    async def buscar(
        self,
        query: str,
        tipo: Optional[str] = None,
        subtipo: Optional[str] = None,
        limite: Optional[int] = None,
        usar_cache: bool = True,
    ) -> list[ResultadoBusca]:
        """
        Busca conhecimento relevante para a query.

        Args:
            query: Texto para buscar
            tipo: Filtrar por tipo (perfil, objecao, etc)
            subtipo: Filtrar por subtipo (senior, preco, etc)
            limite: Número máximo de resultados
            usar_cache: Se deve usar cache

        Returns:
            Lista de resultados ordenados por relevância
        """
        import json

        from app.services.embedding import gerar_embedding
        from app.services.supabase import supabase
        from app.services.redis import cache_get, cache_set

        limite = limite or self.limite_padrao

        # Tentar cache
        if usar_cache:
            cache_key = f"conhecimento:{hash(query)}:{tipo}:{subtipo}:{limite}"
            cached = await cache_get(cache_key)
            if cached:
                logger.debug(f"Busca em cache: {query[:50]}...")
                return [ResultadoBusca(**r) for r in json.loads(cached)]

        # Gerar embedding da query
        query_embedding = await gerar_embedding(query)

        # Buscar via função SQL
        response = supabase.rpc(
            "buscar_conhecimento",
            {
                "query_embedding": query_embedding,
                "tipo_filtro": tipo,
                "subtipo_filtro": subtipo,
                "limite": limite,
                "threshold": self.threshold,
            },
        ).execute()

        resultados = [
            ResultadoBusca(
                id=r["id"],
                arquivo=r["arquivo"],
                secao=r["secao"],
                conteudo=r["conteudo"],
                tipo=r["tipo"],
                subtipo=r["subtipo"],
                tags=r["tags"] or [],
                similaridade=r["similaridade"],
            )
            for r in response.data
        ]

        # Salvar em cache (serializa lista para JSON string)
        if usar_cache and resultados:
            cache_data = json.dumps([
                {
                    "id": r.id,
                    "arquivo": r.arquivo,
                    "secao": r.secao,
                    "conteudo": r.conteudo,
                    "tipo": r.tipo,
                    "subtipo": r.subtipo,
                    "tags": r.tags,
                    "similaridade": r.similaridade,
                }
                for r in resultados
            ], ensure_ascii=False)
            await cache_set(cache_key, cache_data, CACHE_TTL_BUSCA)

        logger.info(f"Busca '{query[:30]}...': {len(resultados)} resultados")
        return resultados

    async def buscar_para_objecao(self, mensagem: str) -> list[ResultadoBusca]:
        """
        Busca conhecimento específico para lidar com objeção.

        Args:
            mensagem: Mensagem do médico com objeção

        Returns:
            Conhecimento sobre como responder
        """
        return await self.buscar(
            query=f"Como responder quando médico diz: {mensagem}",
            tipo="objecao",
            limite=3,
        )

    async def buscar_para_perfil(self, perfil: str) -> list[ResultadoBusca]:
        """
        Busca conhecimento sobre como abordar perfil específico.

        Args:
            perfil: Nome do perfil (senior, recem_formado, etc)

        Returns:
            Conhecimento sobre abordagem para perfil
        """
        return await self.buscar(
            query=f"Como abordar médico {perfil.replace('_', ' ')}",
            tipo="perfil",
            subtipo=perfil,
            limite=3,
        )

    async def buscar_exemplos_conversa(self, contexto: str) -> list[ResultadoBusca]:
        """
        Busca exemplos de conversas reais relevantes.

        Args:
            contexto: Contexto da situação atual

        Returns:
            Exemplos de conversas de referência
        """
        return await self.buscar(query=contexto, tipo="conversa", limite=2)

    async def buscar_por_tags(
        self, tags: list[str], limite: int = 5
    ) -> list[ResultadoBusca]:
        """
        Busca por tags específicas.

        Args:
            tags: Lista de tags para filtrar
            limite: Número máximo de resultados

        Returns:
            Resultados que contêm todas as tags
        """
        from app.services.supabase import supabase

        # Busca direta por tags (sem embedding)
        response = (
            supabase.table("conhecimento_julia")
            .select("id, arquivo, secao, conteudo, tipo, subtipo, tags")
            .contains("tags", tags)
            .eq("ativo", True)
            .limit(limite)
            .execute()
        )

        return [
            ResultadoBusca(
                id=r["id"],
                arquivo=r["arquivo"],
                secao=r["secao"],
                conteudo=r["conteudo"],
                tipo=r["tipo"],
                subtipo=r["subtipo"],
                tags=r["tags"] or [],
                similaridade=1.0,  # Tag match = relevância máxima
            )
            for r in response.data
        ]
