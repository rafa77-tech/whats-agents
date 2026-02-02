"""Testes para tool SQL dinâmico Helena."""
import pytest
from unittest.mock import patch, MagicMock

from app.tools.helena.sql import validar_query, handle_consulta_sql


class TestValidarQuery:
    """Testes para validação de query."""

    def test_select_simples_valido(self):
        """SELECT simples com LIMIT é válido."""
        valido, erro = validar_query("SELECT * FROM clientes LIMIT 10")
        assert valido is True
        assert erro == ""

    def test_select_sem_limit_invalido(self):
        """SELECT sem LIMIT é inválido."""
        valido, erro = validar_query("SELECT * FROM clientes")
        assert valido is False
        assert "LIMIT" in erro

    def test_limit_maior_que_100_invalido(self):
        """LIMIT > 100 é inválido."""
        valido, erro = validar_query("SELECT * FROM clientes LIMIT 500")
        assert valido is False
        assert "100" in erro

    def test_insert_bloqueado(self):
        """INSERT é bloqueado."""
        valido, erro = validar_query("INSERT INTO clientes VALUES (1)")
        assert valido is False
        assert "SELECT" in erro

    def test_update_bloqueado(self):
        """UPDATE é bloqueado."""
        valido, erro = validar_query("UPDATE clientes SET nome = 'x'")
        assert valido is False
        assert "SELECT" in erro

    def test_delete_bloqueado(self):
        """DELETE é bloqueado."""
        valido, erro = validar_query("DELETE FROM clientes")
        assert valido is False
        assert "SELECT" in erro

    def test_drop_bloqueado(self):
        """DROP é bloqueado."""
        valido, erro = validar_query("SELECT * FROM clientes; DROP TABLE clientes;-- LIMIT 10")
        assert valido is False
        assert "DROP" in erro

    def test_truncate_bloqueado(self):
        """TRUNCATE é bloqueado."""
        valido, erro = validar_query("SELECT 1; TRUNCATE clientes; LIMIT 1")
        assert valido is False
        assert "TRUNCATE" in erro

    def test_tabela_sistema_bloqueada(self):
        """Acesso a pg_shadow é bloqueado."""
        valido, erro = validar_query("SELECT * FROM pg_shadow LIMIT 10")
        assert valido is False
        assert "não é permitido" in erro.lower()

    def test_select_complexo_valido(self):
        """SELECT complexo com JOIN é válido."""
        query = """
        SELECT c.primeiro_nome, e.nome
        FROM clientes c
        JOIN especialidades e ON e.id = c.especialidade_id
        WHERE c.created_at >= '2026-01-01'
        GROUP BY c.id, e.nome
        ORDER BY c.primeiro_nome
        LIMIT 50
        """
        valido, erro = validar_query(query)
        assert valido is True

    def test_select_com_subquery_valido(self):
        """SELECT com subquery é válido."""
        query = """
        SELECT * FROM clientes
        WHERE id IN (SELECT cliente_id FROM conversations WHERE status = 'ativa')
        LIMIT 20
        """
        valido, erro = validar_query(query)
        assert valido is True

    def test_limit_exato_100_valido(self):
        """LIMIT exatamente 100 é válido."""
        valido, erro = validar_query("SELECT * FROM clientes LIMIT 100")
        assert valido is True


class TestHandleConsultaSql:
    """Testes para handler consulta_sql."""

    @pytest.mark.asyncio
    async def test_executa_query_valida(self):
        """Executa query válida com sucesso."""
        mock_result = MagicMock()
        mock_result.data = [{"count": 42}]

        with patch('app.tools.helena.sql.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_consulta_sql(
                {
                    "query": "SELECT COUNT(*) as count FROM clientes LIMIT 1",
                    "explicacao": "Contagem de clientes",
                },
                "U123",
                "C456",
            )

        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["data"][0]["count"] == 42

    @pytest.mark.asyncio
    async def test_rejeita_query_sem_limit(self):
        """Rejeita query sem LIMIT."""
        result = await handle_consulta_sql(
            {
                "query": "SELECT * FROM clientes",
                "explicacao": "Listar clientes",
            },
            "U123",
            "C456",
        )

        assert result["success"] is False
        assert "LIMIT" in result["error"]

    @pytest.mark.asyncio
    async def test_query_vazia(self):
        """Query vazia retorna erro."""
        result = await handle_consulta_sql(
            {"query": "", "explicacao": ""},
            "U123",
            "C456",
        )

        assert result["success"] is False
        assert "não fornecida" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejeita_delete(self):
        """Rejeita tentativa de DELETE."""
        result = await handle_consulta_sql(
            {
                "query": "DELETE FROM clientes WHERE id = 1",
                "explicacao": "Deletar cliente",
            },
            "U123",
            "C456",
        )

        assert result["success"] is False
        assert "SELECT" in result["error"]

    @pytest.mark.asyncio
    async def test_erro_timeout_traduzido(self):
        """Erro de timeout é traduzido."""
        with patch('app.tools.helena.sql.supabase') as mock_db:
            mock_db.rpc.return_value.execute.side_effect = Exception(
                "Query excedeu timeout de 10 segundos"
            )

            result = await handle_consulta_sql(
                {
                    "query": "SELECT * FROM clientes LIMIT 10",
                    "explicacao": "teste",
                },
                "U123",
                "C456",
            )

        assert result["success"] is False
        assert "tempo limite" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_erro_syntax_traduzido(self):
        """Erro de sintaxe é traduzido."""
        with patch('app.tools.helena.sql.supabase') as mock_db:
            mock_db.rpc.return_value.execute.side_effect = Exception(
                "syntax error at or near FROM"
            )

            result = await handle_consulta_sql(
                {
                    "query": "SELECT FROM clientes LIMIT 10",
                    "explicacao": "teste",
                },
                "U123",
                "C456",
            )

        assert result["success"] is False
        assert "sintaxe" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_query_retorna_lista_vazia(self):
        """Query sem resultados retorna lista vazia."""
        mock_result = MagicMock()
        mock_result.data = []

        with patch('app.tools.helena.sql.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_consulta_sql(
                {
                    "query": "SELECT * FROM clientes WHERE id = 'inexistente' LIMIT 10",
                    "explicacao": "Buscar cliente inexistente",
                },
                "U123",
                "C456",
            )

        assert result["success"] is True
        assert result["data"] == []
        assert result["row_count"] == 0
