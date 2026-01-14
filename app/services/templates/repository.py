"""
Repository para Templates de Mensagem.

Sprint 30 - Epic 07

Templates armazenados no banco de dados com cache Redis
para permitir atualizacoes dinamicas sem deploy.
"""
import logging
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from app.services.supabase import supabase
from app.services.redis import cache_get_json, cache_set_json, cache_delete

logger = logging.getLogger(__name__)

# Cache TTL (5 minutos)
CACHE_TTL = 300
CACHE_PREFIX = "template:"


@dataclass
class MessageTemplate:
    """Entidade de template de mensagem."""
    id: str
    slug: str
    categoria: str
    conteudo: str
    descricao: Optional[str] = None
    variaveis: List[str] = None
    ativo: bool = True

    def __post_init__(self):
        if self.variaveis is None:
            self.variaveis = []

    @classmethod
    def from_dict(cls, data: dict) -> "MessageTemplate":
        """Cria MessageTemplate a partir de dict do banco."""
        return cls(
            id=data.get("id", ""),
            slug=data.get("slug", ""),
            categoria=data.get("categoria", ""),
            conteudo=data.get("conteudo", ""),
            descricao=data.get("descricao"),
            variaveis=data.get("variaveis") or [],
            ativo=data.get("ativo", True),
        )

    def render(self, **kwargs) -> str:
        """
        Renderiza template substituindo variaveis.

        Args:
            **kwargs: Variaveis para substituir

        Returns:
            Conteudo renderizado

        Example:
            template.render(nome="Dr. Carlos")
        """
        resultado = self.conteudo
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            resultado = resultado.replace(placeholder, str(value) if value else "")
        return resultado


class TemplateRepository:
    """
    Repository para templates de mensagem com cache Redis.

    Uso:
        repo = TemplateRepository()
        template = await repo.buscar_por_slug("optout_confirmacao")
        mensagem = template.render(nome="Dr. Carlos")

    Cache:
        - TTL de 5 minutos
        - Invalidado automaticamente em updates
    """

    def __init__(self, db_client=None):
        """
        Inicializa repository.

        Args:
            db_client: Cliente do banco (default: supabase global)
        """
        self.db = db_client or supabase
        self.table_name = "message_templates"

    def _cache_key(self, slug: str) -> str:
        """Gera chave de cache para um slug."""
        return f"{CACHE_PREFIX}{slug}"

    async def buscar_por_slug(self, slug: str) -> Optional[MessageTemplate]:
        """
        Busca template por slug (com cache).

        Args:
            slug: Identificador do template

        Returns:
            MessageTemplate ou None
        """
        cache_key = self._cache_key(slug)

        # Tentar cache primeiro
        cached = await cache_get_json(cache_key)
        if cached:
            logger.debug(f"Template {slug} encontrado no cache")
            return MessageTemplate.from_dict(cached)

        # Buscar no banco
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("slug", slug)
                .eq("ativo", True)
                .execute()
            )

            if response.data:
                template_data = response.data[0]
                # Salvar no cache
                await cache_set_json(cache_key, template_data, CACHE_TTL)
                logger.debug(f"Template {slug} carregado do banco e cacheado")
                return MessageTemplate.from_dict(template_data)

            logger.warning(f"Template {slug} nao encontrado")
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar template {slug}: {e}")
            return None

    async def listar_por_categoria(self, categoria: str) -> List[MessageTemplate]:
        """
        Lista templates de uma categoria.

        Args:
            categoria: Categoria dos templates

        Returns:
            Lista de templates
        """
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("categoria", categoria)
                .eq("ativo", True)
                .execute()
            )

            return [MessageTemplate.from_dict(item) for item in response.data or []]

        except Exception as e:
            logger.error(f"Erro ao listar templates da categoria {categoria}: {e}")
            return []

    async def atualizar(self, slug: str, conteudo: str) -> Optional[MessageTemplate]:
        """
        Atualiza conteudo de um template.

        Args:
            slug: Identificador do template
            conteudo: Novo conteudo

        Returns:
            Template atualizado ou None
        """
        try:
            response = (
                self.db.table(self.table_name)
                .update({"conteudo": conteudo})
                .eq("slug", slug)
                .execute()
            )

            if response.data:
                # Invalidar cache
                await cache_delete(self._cache_key(slug))
                logger.info(f"Template {slug} atualizado e cache invalidado")
                return MessageTemplate.from_dict(response.data[0])

            return None

        except Exception as e:
            logger.error(f"Erro ao atualizar template {slug}: {e}")
            return None

    async def criar(self, slug: str, categoria: str, conteudo: str,
                    descricao: str = None, variaveis: List[str] = None) -> Optional[MessageTemplate]:
        """
        Cria novo template.

        Args:
            slug: Identificador unico
            categoria: Categoria do template
            conteudo: Conteudo com placeholders
            descricao: Descricao do template
            variaveis: Lista de variaveis aceitas

        Returns:
            Template criado ou None
        """
        try:
            data = {
                "slug": slug,
                "categoria": categoria,
                "conteudo": conteudo,
                "descricao": descricao,
                "variaveis": variaveis or [],
            }

            response = (
                self.db.table(self.table_name)
                .insert(data)
                .execute()
            )

            if response.data:
                logger.info(f"Template {slug} criado")
                return MessageTemplate.from_dict(response.data[0])

            return None

        except Exception as e:
            logger.error(f"Erro ao criar template {slug}: {e}")
            return None

    async def invalidar_cache(self, slug: str) -> bool:
        """
        Invalida cache de um template.

        Args:
            slug: Identificador do template

        Returns:
            True se invalidado com sucesso
        """
        return await cache_delete(self._cache_key(slug))


# Singleton para uso direto
_repository: Optional[TemplateRepository] = None


def get_template_repository() -> TemplateRepository:
    """Retorna instancia singleton do repository."""
    global _repository
    if _repository is None:
        _repository = TemplateRepository()
    return _repository


async def get_template(slug: str, **kwargs) -> Optional[str]:
    """
    Helper para obter template renderizado.

    Args:
        slug: Identificador do template
        **kwargs: Variaveis para substituir

    Returns:
        Mensagem renderizada ou None

    Example:
        msg = await get_template("saudacao_inicial", nome="Dr. Carlos")
    """
    repo = get_template_repository()
    template = await repo.buscar_por_slug(slug)

    if template:
        return template.render(**kwargs)

    return None
