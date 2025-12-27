"""
Testes para as tools de grupos WhatsApp no Slack.

Sprint 14 - E10 - Interface Slack
"""

import pytest
from uuid import uuid4
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock

from app.tools.slack.grupos import (
    handle_listar_vagas_revisao,
    handle_aprovar_vaga_grupo,
    handle_rejeitar_vaga_grupo,
    handle_detalhes_vaga_grupo,
    handle_estatisticas_grupos,
    handle_adicionar_alias_hospital,
    handle_buscar_hospital_grupos,
    resolver_id_vaga,
    TOOL_LISTAR_VAGAS_REVISAO,
    TOOL_APROVAR_VAGA_GRUPO,
    TOOL_REJEITAR_VAGA_GRUPO,
    TOOL_DETALHES_VAGA_GRUPO,
    TOOL_ESTATISTICAS_GRUPOS,
    TOOL_ADICIONAR_ALIAS_HOSPITAL,
    TOOL_BUSCAR_HOSPITAL,
)


class TestToolDefinitions:
    """Testes das definições de tools."""

    def test_listar_vagas_revisao_structure(self):
        """Tool deve ter estrutura correta."""
        assert TOOL_LISTAR_VAGAS_REVISAO["name"] == "listar_vagas_revisao"
        assert "description" in TOOL_LISTAR_VAGAS_REVISAO
        assert "input_schema" in TOOL_LISTAR_VAGAS_REVISAO
        assert TOOL_LISTAR_VAGAS_REVISAO["input_schema"]["type"] == "object"

    def test_aprovar_vaga_structure(self):
        """Tool de aprovar deve ter vaga_id obrigatório."""
        assert TOOL_APROVAR_VAGA_GRUPO["name"] == "aprovar_vaga_grupo"
        assert "vaga_id" in TOOL_APROVAR_VAGA_GRUPO["input_schema"]["required"]

    def test_rejeitar_vaga_structure(self):
        """Tool de rejeitar deve ter vaga_id obrigatório."""
        assert TOOL_REJEITAR_VAGA_GRUPO["name"] == "rejeitar_vaga_grupo"
        assert "vaga_id" in TOOL_REJEITAR_VAGA_GRUPO["input_schema"]["required"]

    def test_detalhes_vaga_structure(self):
        """Tool de detalhes deve ter vaga_id obrigatório."""
        assert TOOL_DETALHES_VAGA_GRUPO["name"] == "detalhes_vaga_grupo"
        assert "vaga_id" in TOOL_DETALHES_VAGA_GRUPO["input_schema"]["required"]

    def test_estatisticas_structure(self):
        """Tool de estatísticas deve ter período opcional."""
        assert TOOL_ESTATISTICAS_GRUPOS["name"] == "estatisticas_grupos"
        assert "periodo" in TOOL_ESTATISTICAS_GRUPOS["input_schema"]["properties"]

    def test_adicionar_alias_structure(self):
        """Tool de alias deve ter campos obrigatórios."""
        assert TOOL_ADICIONAR_ALIAS_HOSPITAL["name"] == "adicionar_alias_hospital"
        assert "hospital_id" in TOOL_ADICIONAR_ALIAS_HOSPITAL["input_schema"]["required"]
        assert "alias" in TOOL_ADICIONAR_ALIAS_HOSPITAL["input_schema"]["required"]

    def test_buscar_hospital_structure(self):
        """Tool de busca deve ter termo obrigatório."""
        assert TOOL_BUSCAR_HOSPITAL["name"] == "buscar_hospital_grupos"
        assert "termo" in TOOL_BUSCAR_HOSPITAL["input_schema"]["required"]


class TestResolverIdVaga:
    """Testes do resolvedor de ID."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.tools.slack.grupos.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_id_completo(self, mock_supabase):
        """Deve retornar ID completo diretamente."""
        uuid_completo = str(uuid4())

        resultado = await resolver_id_vaga(uuid_completo)

        assert resultado == uuid_completo

    @pytest.mark.asyncio
    async def test_id_curto_encontrado(self, mock_supabase):
        """Deve resolver ID curto para completo."""
        id_completo = str(uuid4())

        mock_supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": id_completo}]
        )

        resultado = await resolver_id_vaga("abc123")

        assert resultado == id_completo

    @pytest.mark.asyncio
    async def test_id_curto_nao_encontrado(self, mock_supabase):
        """Deve retornar None se não encontrar."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        resultado = await resolver_id_vaga("xyz789")

        assert resultado is None


class TestHandleListarVagasRevisao:
    """Testes do handler de listagem."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.tools.slack.grupos.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_lista_vagas(self, mock_supabase):
        """Deve listar vagas em revisão."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": str(uuid4()),
                    "hospital_raw": "Hospital X",
                    "especialidade_raw": "CM",
                    "data": "2024-12-28",
                    "periodo_raw": "Noturno",
                    "valor": 1500,
                    "confianca_geral": 0.85,
                    "created_at": "2024-12-27T10:00:00",
                    "grupos_whatsapp": {"nome": "Grupo ABC"},
                    "hospitais": {"nome": "Hospital X Completo"},
                    "especialidades": {"nome": "Clínica Médica"},
                }
            ]
        )

        resultado = await handle_listar_vagas_revisao({"limite": 10})

        assert resultado["success"] is True
        assert resultado["total"] == 1
        assert len(resultado["vagas"]) == 1
        assert resultado["vagas"][0]["hospital"] == "Hospital X Completo"

    @pytest.mark.asyncio
    async def test_lista_vazia(self, mock_supabase):
        """Deve retornar lista vazia se não houver vagas."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        resultado = await handle_listar_vagas_revisao({})

        assert resultado["success"] is True
        assert resultado["total"] == 0


class TestHandleAprovarVagaGrupo:
    """Testes do handler de aprovação."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.tools.slack.grupos.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_vaga_id_obrigatorio(self, mock_supabase):
        """Deve exigir ID da vaga."""
        resultado = await handle_aprovar_vaga_grupo({})

        assert resultado["success"] is False
        assert "obrigatório" in resultado["error"]

    @pytest.mark.asyncio
    async def test_vaga_nao_encontrada(self, mock_supabase):
        """Deve retornar erro se vaga não existe."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        resultado = await handle_aprovar_vaga_grupo({"vaga_id": "xyz123"})

        assert resultado["success"] is False
        assert "não encontrada" in resultado["error"]


class TestHandleRejeitarVagaGrupo:
    """Testes do handler de rejeição."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.tools.slack.grupos.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_vaga_id_obrigatorio(self, mock_supabase):
        """Deve exigir ID da vaga."""
        resultado = await handle_rejeitar_vaga_grupo({})

        assert resultado["success"] is False
        assert "obrigatório" in resultado["error"]

    @pytest.mark.asyncio
    async def test_rejeita_vaga(self, mock_supabase):
        """Deve rejeitar vaga com sucesso."""
        vaga_id = str(uuid4())

        # Mock para resolver ID
        mock_supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": vaga_id}]
        )

        # Mock para update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resultado = await handle_rejeitar_vaga_grupo({
            "vaga_id": vaga_id[:8],
            "motivo": "dados_incorretos"
        })

        assert resultado["success"] is True
        assert "rejeitada" in resultado["mensagem"]


class TestHandleDetalhesVagaGrupo:
    """Testes do handler de detalhes."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.tools.slack.grupos.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_vaga_id_obrigatorio(self, mock_supabase):
        """Deve exigir ID da vaga."""
        resultado = await handle_detalhes_vaga_grupo({})

        assert resultado["success"] is False
        assert "obrigatório" in resultado["error"]

    @pytest.mark.asyncio
    async def test_mostra_detalhes(self, mock_supabase):
        """Deve mostrar detalhes da vaga."""
        vaga_id = str(uuid4())

        # Mock para select da vaga
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": vaga_id,
                "status": "aguardando_revisao",
                "hospital_raw": "Hospital X",
                "especialidade_raw": "CM",
                "data": "2024-12-28",
                "periodo_raw": "Noturno",
                "valor": 1500,
                "confianca_geral": 0.85,
                "created_at": "2024-12-27T10:00:00",
                "grupos_whatsapp": {"nome": "Grupo ABC", "regiao": "ABC"},
                "contatos_grupo": {"nome": "João", "telefone": "11999999999"},
                "hospitais": {"nome": "Hospital X Completo", "cidade": "São Paulo"},
                "especialidades": {"nome": "Clínica Médica"},
                "periodos": {"nome": "Noturno"},
            }
        )

        # Mock para fontes
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {"ordem": 1, "grupos_whatsapp": {"nome": "Grupo ABC"}, "valor_informado": 1500}
            ]
        )

        resultado = await handle_detalhes_vaga_grupo({"vaga_id": vaga_id})

        assert resultado["success"] is True
        assert resultado["status"] == "aguardando_revisao"
        assert "dados_extraidos" in resultado
        assert "dados_normalizados" in resultado
        assert "origem" in resultado


class TestHandleEstatisticasGrupos:
    """Testes do handler de estatísticas."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.tools.slack.grupos.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_estatisticas_hoje(self, mock_supabase):
        """Deve retornar estatísticas do dia."""
        # Mocks para cada query
        mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(count=100)
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(count=50)

        resultado = await handle_estatisticas_grupos({"periodo": "hoje"})

        assert resultado["success"] is True
        assert resultado["periodo"] == "hoje"
        assert "mensagens" in resultado
        assert "vagas" in resultado
        assert "taxas" in resultado

    @pytest.mark.asyncio
    async def test_estatisticas_semana(self, mock_supabase):
        """Deve retornar estatísticas da semana."""
        mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(count=500)
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(count=200)

        resultado = await handle_estatisticas_grupos({"periodo": "semana"})

        assert resultado["success"] is True
        assert resultado["periodo"] == "semana"


class TestHandleAdicionarAliasHospital:
    """Testes do handler de alias."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.tools.slack.grupos.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_campos_obrigatorios(self, mock_supabase):
        """Deve exigir hospital_id e alias."""
        resultado = await handle_adicionar_alias_hospital({})

        assert resultado["success"] is False
        assert "obrigatórios" in resultado["error"]

    @pytest.mark.asyncio
    async def test_hospital_nao_encontrado(self, mock_supabase):
        """Deve retornar erro se hospital não existe."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        resultado = await handle_adicionar_alias_hospital({
            "hospital_id": str(uuid4()),
            "alias": "HSL"
        })

        assert resultado["success"] is False
        assert "não encontrado" in resultado["error"]

    @pytest.mark.asyncio
    async def test_adiciona_alias(self, mock_supabase):
        """Deve adicionar alias com sucesso."""
        hospital_id = str(uuid4())

        # Mock para buscar hospital
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": hospital_id, "nome": "Hospital São Luiz"}
        )

        # Mock para verificar existente
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        # Mock para insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        with patch("app.services.grupos.normalizador.normalizar_para_busca", return_value="hsl"):
            resultado = await handle_adicionar_alias_hospital({
                "hospital_id": hospital_id,
                "alias": "HSL"
            })

        assert resultado["success"] is True
        assert "adicionado" in resultado["mensagem"]


class TestHandleBuscarHospitalGrupos:
    """Testes do handler de busca de hospital."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.tools.slack.grupos.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_termo_obrigatorio(self, mock_supabase):
        """Deve exigir termo de busca."""
        resultado = await handle_buscar_hospital_grupos({})

        assert resultado["success"] is False
        assert "obrigatório" in resultado["error"]

    @pytest.mark.asyncio
    async def test_busca_hospital(self, mock_supabase):
        """Deve buscar hospital por nome."""
        hospital_id = str(uuid4())

        # Mock genérico que funciona para qualquer query
        mock_execute = MagicMock(
            data=[
                {
                    "hospital_id": hospital_id,
                    "id": hospital_id,
                    "alias": "HSL",
                    "nome": "Hospital São Luiz",
                    "cidade": "São Paulo",
                    "hospitais": {"id": hospital_id, "nome": "Hospital São Luiz", "cidade": "São Paulo"}
                }
            ]
        )

        mock_supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_execute

        with patch("app.services.grupos.normalizador.normalizar_para_busca", return_value="sao luiz"):
            resultado = await handle_buscar_hospital_grupos({"termo": "São Luiz"})

        assert resultado["success"] is True
        assert resultado["termo"] == "São Luiz"
        assert resultado["total"] >= 1


class TestIntegracaoComSlack:
    """Testes de integração com o sistema Slack."""

    def test_tools_registradas(self):
        """Todas as tools devem estar registradas."""
        from app.tools.slack import SLACK_TOOLS

        nomes_tools = [t["name"] for t in SLACK_TOOLS]

        assert "listar_vagas_revisao" in nomes_tools
        assert "aprovar_vaga_grupo" in nomes_tools
        assert "rejeitar_vaga_grupo" in nomes_tools
        assert "detalhes_vaga_grupo" in nomes_tools
        assert "estatisticas_grupos" in nomes_tools
        assert "adicionar_alias_hospital" in nomes_tools
        assert "buscar_hospital_grupos" in nomes_tools

    def test_tools_criticas(self):
        """Tools de ação devem estar em TOOLS_CRITICAS."""
        from app.tools.slack import TOOLS_CRITICAS

        assert "aprovar_vaga_grupo" in TOOLS_CRITICAS
        assert "rejeitar_vaga_grupo" in TOOLS_CRITICAS
        assert "adicionar_alias_hospital" in TOOLS_CRITICAS

        # Tools de leitura não devem estar
        assert "listar_vagas_revisao" not in TOOLS_CRITICAS
        assert "detalhes_vaga_grupo" not in TOOLS_CRITICAS
        assert "estatisticas_grupos" not in TOOLS_CRITICAS

    @pytest.mark.asyncio
    async def test_executor_tool(self):
        """Executor deve reconhecer as novas tools."""
        from app.tools.slack import executar_tool

        with patch("app.tools.slack.grupos.supabase") as mock:
            mock.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )

            resultado = await executar_tool("listar_vagas_revisao", {}, "user123")

            assert resultado["success"] is True
