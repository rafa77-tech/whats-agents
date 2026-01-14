"""
Testes para TemplateRepository.

Sprint 30 - S30.E7.4

Testes do sistema de templates com cache Redis.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.templates.repository import (
    MessageTemplate,
    TemplateRepository,
    get_template,
    get_template_repository,
    CACHE_TTL,
)


class MockTable:
    """Mock para Supabase table chain."""

    def __init__(self, data=None, should_fail=False):
        self.data = data or []
        self.should_fail = should_fail
        self._filters = {}

    def select(self, *args, **kwargs):
        return self

    def insert(self, data):
        self._insert_data = data
        return self

    def update(self, data):
        self._update_data = data
        return self

    def eq(self, field, value):
        self._filters[field] = value
        return self

    def execute(self):
        if self.should_fail:
            raise Exception("Database error")
        response = MagicMock()
        response.data = self.data
        return response


class MockDatabase:
    """Mock para Supabase client."""

    def __init__(self, table_data=None, should_fail=False):
        self.table_data = table_data or []
        self.should_fail = should_fail

    def table(self, name):
        return MockTable(self.table_data, self.should_fail)


class TestMessageTemplate:
    """Testes para a entidade MessageTemplate."""

    def test_from_dict_completo(self):
        """Deve criar template com todos os campos."""
        data = {
            "id": "uuid-123",
            "slug": "optout_confirmacao",
            "categoria": "optout",
            "conteudo": "Entendi! Removido da lista",
            "descricao": "Template de opt-out",
            "variaveis": [],
            "ativo": True,
        }

        template = MessageTemplate.from_dict(data)

        assert template.id == "uuid-123"
        assert template.slug == "optout_confirmacao"
        assert template.categoria == "optout"
        assert template.conteudo == "Entendi! Removido da lista"
        assert template.ativo is True

    def test_from_dict_minimo(self):
        """Deve criar template com campos minimos."""
        data = {
            "id": "uuid-456",
            "slug": "teste",
            "categoria": "teste",
            "conteudo": "Conteudo teste",
        }

        template = MessageTemplate.from_dict(data)

        assert template.id == "uuid-456"
        assert template.variaveis == []
        assert template.ativo is True

    def test_render_sem_variaveis(self):
        """Deve renderizar template sem variaveis."""
        template = MessageTemplate(
            id="1",
            slug="teste",
            categoria="teste",
            conteudo="Mensagem fixa sem variaveis",
        )

        resultado = template.render()

        assert resultado == "Mensagem fixa sem variaveis"

    def test_render_com_uma_variavel(self):
        """Deve substituir uma variavel."""
        template = MessageTemplate(
            id="1",
            slug="saudacao",
            categoria="saudacao",
            conteudo="Oi {nome}! Tudo bem?",
            variaveis=["nome"],
        )

        resultado = template.render(nome="Dr. Carlos")

        assert resultado == "Oi Dr. Carlos! Tudo bem?"

    def test_render_com_multiplas_variaveis(self):
        """Deve substituir multiplas variaveis."""
        template = MessageTemplate(
            id="1",
            slug="oferta",
            categoria="oferta",
            conteudo="Oi {nome}! Tenho uma vaga em {hospital} para {data}",
            variaveis=["nome", "hospital", "data"],
        )

        resultado = template.render(
            nome="Dr. Carlos",
            hospital="Hospital Sao Luiz",
            data="15/01",
        )

        assert resultado == "Oi Dr. Carlos! Tenho uma vaga em Hospital Sao Luiz para 15/01"

    def test_render_variavel_ausente(self):
        """Deve manter placeholder se variavel ausente."""
        template = MessageTemplate(
            id="1",
            slug="teste",
            categoria="teste",
            conteudo="Oi {nome}!",
            variaveis=["nome"],
        )

        resultado = template.render()

        assert resultado == "Oi {nome}!"

    def test_render_variavel_none(self):
        """Deve substituir None por string vazia."""
        template = MessageTemplate(
            id="1",
            slug="teste",
            categoria="teste",
            conteudo="Oi {nome}!",
            variaveis=["nome"],
        )

        resultado = template.render(nome=None)

        assert resultado == "Oi !"


class TestTemplateRepository:
    """Testes para TemplateRepository."""

    @pytest.mark.asyncio
    @patch("app.services.templates.repository.cache_get_json")
    @patch("app.services.templates.repository.cache_set_json")
    async def test_buscar_por_slug_cache_hit(self, mock_set, mock_get):
        """Deve retornar do cache quando disponivel."""
        mock_get.return_value = {
            "id": "uuid-123",
            "slug": "optout_confirmacao",
            "categoria": "optout",
            "conteudo": "Entendi!",
            "ativo": True,
        }

        mock_db = MockDatabase()
        repo = TemplateRepository(mock_db)

        template = await repo.buscar_por_slug("optout_confirmacao")

        assert template is not None
        assert template.slug == "optout_confirmacao"
        mock_get.assert_called_once()
        mock_set.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.templates.repository.cache_get_json")
    @patch("app.services.templates.repository.cache_set_json")
    async def test_buscar_por_slug_cache_miss(self, mock_set, mock_get):
        """Deve buscar no banco quando cache vazio."""
        mock_get.return_value = None
        mock_set.return_value = True

        mock_data = [{
            "id": "uuid-123",
            "slug": "optout_confirmacao",
            "categoria": "optout",
            "conteudo": "Entendi!",
            "ativo": True,
        }]
        mock_db = MockDatabase(table_data=mock_data)
        repo = TemplateRepository(mock_db)

        template = await repo.buscar_por_slug("optout_confirmacao")

        assert template is not None
        assert template.slug == "optout_confirmacao"
        mock_get.assert_called_once()
        mock_set.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.templates.repository.cache_get_json")
    async def test_buscar_por_slug_nao_encontrado(self, mock_get):
        """Deve retornar None quando template nao existe."""
        mock_get.return_value = None

        mock_db = MockDatabase(table_data=[])
        repo = TemplateRepository(mock_db)

        template = await repo.buscar_por_slug("slug_inexistente")

        assert template is None

    @pytest.mark.asyncio
    @patch("app.services.templates.repository.cache_get_json")
    async def test_buscar_por_slug_erro_banco(self, mock_get):
        """Deve retornar None em erro de banco."""
        mock_get.return_value = None

        mock_db = MockDatabase(should_fail=True)
        repo = TemplateRepository(mock_db)

        template = await repo.buscar_por_slug("optout_confirmacao")

        assert template is None

    @pytest.mark.asyncio
    async def test_listar_por_categoria(self):
        """Deve listar templates de uma categoria."""
        mock_data = [
            {"id": "1", "slug": "confirmacao_aceite", "categoria": "confirmacao", "conteudo": "OK"},
            {"id": "2", "slug": "confirmacao_recusa", "categoria": "confirmacao", "conteudo": "Entendido"},
        ]
        mock_db = MockDatabase(table_data=mock_data)
        repo = TemplateRepository(mock_db)

        templates = await repo.listar_por_categoria("confirmacao")

        assert len(templates) == 2
        assert templates[0].slug == "confirmacao_aceite"
        assert templates[1].slug == "confirmacao_recusa"

    @pytest.mark.asyncio
    async def test_listar_por_categoria_vazia(self):
        """Deve retornar lista vazia quando categoria sem templates."""
        mock_db = MockDatabase(table_data=[])
        repo = TemplateRepository(mock_db)

        templates = await repo.listar_por_categoria("categoria_vazia")

        assert templates == []

    @pytest.mark.asyncio
    @patch("app.services.templates.repository.cache_delete")
    async def test_atualizar_template(self, mock_delete):
        """Deve atualizar template e invalidar cache."""
        mock_delete.return_value = True

        mock_data = [{
            "id": "uuid-123",
            "slug": "optout_confirmacao",
            "categoria": "optout",
            "conteudo": "Novo conteudo!",
            "ativo": True,
        }]
        mock_db = MockDatabase(table_data=mock_data)
        repo = TemplateRepository(mock_db)

        template = await repo.atualizar("optout_confirmacao", "Novo conteudo!")

        assert template is not None
        assert template.conteudo == "Novo conteudo!"
        mock_delete.assert_called_once_with("template:optout_confirmacao")

    @pytest.mark.asyncio
    @patch("app.services.templates.repository.cache_delete")
    async def test_atualizar_template_nao_encontrado(self, mock_delete):
        """Deve retornar None quando template nao existe."""
        mock_db = MockDatabase(table_data=[])
        repo = TemplateRepository(mock_db)

        template = await repo.atualizar("slug_inexistente", "Novo conteudo")

        assert template is None
        mock_delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_criar_template(self):
        """Deve criar novo template."""
        mock_data = [{
            "id": "novo-uuid",
            "slug": "novo_template",
            "categoria": "teste",
            "conteudo": "Conteudo do novo template",
            "variaveis": ["nome"],
            "ativo": True,
        }]
        mock_db = MockDatabase(table_data=mock_data)
        repo = TemplateRepository(mock_db)

        template = await repo.criar(
            slug="novo_template",
            categoria="teste",
            conteudo="Conteudo do novo template",
            variaveis=["nome"],
        )

        assert template is not None
        assert template.slug == "novo_template"

    @pytest.mark.asyncio
    @patch("app.services.templates.repository.cache_delete")
    async def test_invalidar_cache(self, mock_delete):
        """Deve invalidar cache de um template."""
        mock_delete.return_value = True

        mock_db = MockDatabase()
        repo = TemplateRepository(mock_db)

        resultado = await repo.invalidar_cache("optout_confirmacao")

        assert resultado is True
        mock_delete.assert_called_once_with("template:optout_confirmacao")


class TestGetTemplate:
    """Testes para a funcao helper get_template."""

    @pytest.mark.asyncio
    @patch("app.services.templates.repository.cache_get_json")
    async def test_get_template_simples(self, mock_get):
        """Deve retornar template renderizado."""
        mock_get.return_value = {
            "id": "uuid-123",
            "slug": "optout_confirmacao",
            "categoria": "optout",
            "conteudo": "Entendi! Removido da lista",
            "ativo": True,
        }

        # Reset singleton
        import app.services.templates.repository as repo_module
        repo_module._repository = None

        resultado = await get_template("optout_confirmacao")

        assert resultado == "Entendi! Removido da lista"

    @pytest.mark.asyncio
    @patch("app.services.templates.repository.cache_get_json")
    async def test_get_template_com_variaveis(self, mock_get):
        """Deve retornar template com variaveis substituidas."""
        mock_get.return_value = {
            "id": "uuid-123",
            "slug": "saudacao_inicial",
            "categoria": "saudacao",
            "conteudo": "Oi {nome}! Tudo bem?",
            "variaveis": ["nome"],
            "ativo": True,
        }

        # Reset singleton
        import app.services.templates.repository as repo_module
        repo_module._repository = None

        resultado = await get_template("saudacao_inicial", nome="Dr. Carlos")

        assert resultado == "Oi Dr. Carlos! Tudo bem?"

    @pytest.mark.asyncio
    @patch("app.services.templates.repository.cache_get_json")
    async def test_get_template_nao_encontrado(self, mock_get):
        """Deve retornar None quando template nao existe."""
        mock_get.return_value = None

        # Reset singleton e usar mock db
        import app.services.templates.repository as repo_module
        repo_module._repository = TemplateRepository(MockDatabase(table_data=[]))

        resultado = await get_template("slug_inexistente")

        assert resultado is None


class TestCacheKey:
    """Testes para geracao de chave de cache."""

    def test_cache_key_format(self):
        """Deve gerar chave com prefixo correto."""
        mock_db = MockDatabase()
        repo = TemplateRepository(mock_db)

        key = repo._cache_key("optout_confirmacao")

        assert key == "template:optout_confirmacao"

    def test_cache_key_diferentes_slugs(self):
        """Deve gerar chaves diferentes para slugs diferentes."""
        mock_db = MockDatabase()
        repo = TemplateRepository(mock_db)

        key1 = repo._cache_key("optout_confirmacao")
        key2 = repo._cache_key("saudacao_inicial")

        assert key1 != key2
        assert key1 == "template:optout_confirmacao"
        assert key2 == "template:saudacao_inicial"
