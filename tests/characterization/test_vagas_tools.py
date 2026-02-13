"""
Testes de caracterização para app/tools/vagas.py

Sprint 58 - Epic 0: Safety Net
Captura o comportamento atual dos 3 tool handlers.

Foca em:
- Shape de retorno dos handlers (campos obrigatórios)
- Tool definitions (names, input_schema)
- Fluxos de erro e sucesso
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def medico():
    return {
        "id": str(uuid4()),
        "primeiro_nome": "Dr. Teste",
        "telefone": "5511999999999",
        "especialidade_nome": "Cardiologia",
        "especialidade_id": str(uuid4()),
        "especialidade": "Cardiologia",
        "stage_jornada": "novo",
        "preferencias_detectadas": {},
    }


@pytest.fixture
def conversa(medico):
    return {
        "id": str(uuid4()),
        "cliente_id": medico["id"],
        "status": "ativa",
    }


# =============================================================================
# Tool Definitions
# =============================================================================


class TestToolDefinitions:
    """Testa schemas das tool definitions."""

    def test_tool_buscar_vagas_shape(self):
        from app.tools.vagas import TOOL_BUSCAR_VAGAS

        assert TOOL_BUSCAR_VAGAS["name"] == "buscar_vagas"
        assert "input_schema" in TOOL_BUSCAR_VAGAS
        assert "description" in TOOL_BUSCAR_VAGAS
        schema = TOOL_BUSCAR_VAGAS["input_schema"]
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "especialidade" in props
        assert "regiao" in props
        assert "periodo" in props
        assert "valor_minimo" in props
        assert "dias_semana" in props
        assert "limite" in props

    def test_tool_reservar_plantao_shape(self):
        from app.tools.vagas import TOOL_RESERVAR_PLANTAO

        assert TOOL_RESERVAR_PLANTAO["name"] == "reservar_plantao"
        assert "input_schema" in TOOL_RESERVAR_PLANTAO
        schema = TOOL_RESERVAR_PLANTAO["input_schema"]
        assert "data_plantao" in schema["properties"]
        assert "confirmacao" in schema["properties"]
        assert "data_plantao" in schema["required"]
        assert "confirmacao" in schema["required"]

    def test_tool_buscar_info_hospital_shape(self):
        from app.tools.vagas import TOOL_BUSCAR_INFO_HOSPITAL

        assert TOOL_BUSCAR_INFO_HOSPITAL["name"] == "buscar_info_hospital"
        schema = TOOL_BUSCAR_INFO_HOSPITAL["input_schema"]
        assert "nome_hospital" in schema["properties"]
        assert "nome_hospital" in schema["required"]

    def test_tools_vagas_lista(self):
        from app.tools.vagas import TOOLS_VAGAS

        assert len(TOOLS_VAGAS) == 3
        nomes = [t["name"] for t in TOOLS_VAGAS]
        assert "buscar_vagas" in nomes
        assert "reservar_plantao" in nomes
        assert "buscar_info_hospital" in nomes


# =============================================================================
# handle_buscar_vagas
# =============================================================================


class TestHandleBuscarVagas:
    """Testa handle_buscar_vagas - busca de vagas disponíveis."""

    @pytest.mark.asyncio
    async def test_sem_especialidade_retorna_erro(self, medico, conversa):
        from app.tools.vagas import handle_buscar_vagas

        medico_sem_esp = {**medico, "especialidade_id": None, "especialidade": None}

        with patch("app.tools.vagas.get_especialidade_service") as mock_svc:
            mock_instance = MagicMock()
            mock_instance.resolver_especialidade_medico = AsyncMock(
                return_value=(None, None, False)
            )
            mock_svc.return_value = mock_instance
            with patch("app.tools.vagas.get_vagas_formatter") as mock_fmt:
                mock_formatter = MagicMock()
                mock_formatter.mensagem_especialidade_nao_identificada.return_value = (
                    "Qual sua especialidade?"
                )
                mock_fmt.return_value = mock_formatter

                result = await handle_buscar_vagas({}, medico_sem_esp, conversa)
                assert result["success"] is False
                assert "mensagem_sugerida" in result
                assert result["vagas"] == []

    @pytest.mark.asyncio
    async def test_com_vagas_retorna_lista(self, medico, conversa):
        from app.tools.vagas import handle_buscar_vagas

        esp_id = medico["especialidade_id"]

        with (
            patch("app.tools.vagas.get_especialidade_service") as mock_svc,
            patch("app.tools.vagas.get_vagas_formatter") as mock_fmt,
            patch(
                "app.tools.vagas.buscar_vagas_compativeis",
                new_callable=AsyncMock,
            ) as mock_buscar,
            patch("app.tools.vagas.aplicar_filtros") as mock_filtros,
            patch(
                "app.tools.vagas.filtrar_por_conflitos",
                new_callable=AsyncMock,
            ) as mock_conflitos,
            patch("app.tools.vagas.formatar_vagas_contexto") as mock_fmt_ctx,
        ):
            mock_instance = MagicMock()
            mock_instance.resolver_especialidade_medico = AsyncMock(
                return_value=(esp_id, "Cardiologia", False)
            )
            mock_svc.return_value = mock_instance

            mock_formatter = MagicMock()
            mock_formatter.formatar_vagas_resumo.return_value = [{"id": "v-1", "hospital": "H1"}]
            mock_formatter.construir_instrucao_vagas.return_value = "Apresente as vagas"
            mock_fmt.return_value = mock_formatter

            vagas = [
                {"id": "v-1", "hospital_nome": "H1", "data": "2025-01-20", "valor": 2500}
            ]
            mock_buscar.return_value = vagas
            mock_filtros.return_value = (vagas, [])
            mock_conflitos.return_value = vagas
            mock_fmt_ctx.return_value = "Contexto formatado"

            result = await handle_buscar_vagas({}, medico, conversa)
            assert result["success"] is True
            assert len(result["vagas"]) > 0
            assert "total_encontradas" in result
            assert "especialidade_buscada" in result

    @pytest.mark.asyncio
    async def test_sem_vagas_retorna_mensagem(self, medico, conversa):
        from app.tools.vagas import handle_buscar_vagas

        esp_id = medico["especialidade_id"]

        with (
            patch("app.tools.vagas.get_especialidade_service") as mock_svc,
            patch("app.tools.vagas.get_vagas_formatter") as mock_fmt,
            patch(
                "app.tools.vagas.buscar_vagas_compativeis",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("app.tools.vagas.aplicar_filtros", return_value=([], [])),
            patch(
                "app.tools.vagas.filtrar_por_conflitos",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            mock_instance = MagicMock()
            mock_instance.resolver_especialidade_medico = AsyncMock(
                return_value=(esp_id, "Cardiologia", False)
            )
            mock_svc.return_value = mock_instance

            mock_formatter = MagicMock()
            mock_formatter.mensagem_sem_vagas.return_value = "Sem vagas no momento"
            mock_fmt.return_value = mock_formatter

            result = await handle_buscar_vagas({}, medico, conversa)
            assert result["success"] is True
            assert result["vagas"] == []
            assert result["total_encontradas"] == 0
            assert "mensagem_sugerida" in result

    @pytest.mark.asyncio
    async def test_especialidade_nao_encontrada(self, medico, conversa):
        from app.tools.vagas import handle_buscar_vagas

        with (
            patch("app.tools.vagas.get_especialidade_service") as mock_svc,
            patch("app.tools.vagas.get_vagas_formatter") as mock_fmt,
        ):
            mock_instance = MagicMock()
            mock_instance.resolver_especialidade_medico = AsyncMock(
                return_value=(None, None, False)
            )
            mock_svc.return_value = mock_instance

            mock_formatter = MagicMock()
            mock_formatter.mensagem_especialidade_nao_encontrada.return_value = (
                "Especialidade não encontrada"
            )
            mock_fmt.return_value = mock_formatter

            result = await handle_buscar_vagas(
                {"especialidade": "xyz_inexistente"}, medico, conversa
            )
            assert result["success"] is False
            assert "mensagem_sugerida" in result

    @pytest.mark.asyncio
    async def test_erro_generico_capturado(self, medico, conversa):
        from app.tools.vagas import handle_buscar_vagas

        esp_id = medico["especialidade_id"]

        with (
            patch("app.tools.vagas.get_especialidade_service") as mock_svc,
            patch("app.tools.vagas.get_vagas_formatter") as mock_fmt,
            patch(
                "app.tools.vagas.buscar_vagas_compativeis",
                new_callable=AsyncMock,
                side_effect=Exception("DB error"),
            ),
        ):
            mock_instance = MagicMock()
            mock_instance.resolver_especialidade_medico = AsyncMock(
                return_value=(esp_id, "Cardiologia", False)
            )
            mock_svc.return_value = mock_instance

            mock_formatter = MagicMock()
            mock_formatter.mensagem_erro_generico.return_value = "Tive um probleminha"
            mock_fmt.return_value = mock_formatter

            result = await handle_buscar_vagas({}, medico, conversa)
            assert result["success"] is False
            assert "error" in result


# =============================================================================
# handle_reservar_plantao
# =============================================================================


class TestHandleReservarPlantao:
    """Testa handle_reservar_plantao - reserva de vaga."""

    @pytest.mark.asyncio
    async def test_sem_data_retorna_erro(self, medico, conversa):
        from app.tools.vagas import handle_reservar_plantao

        result = await handle_reservar_plantao({}, medico, conversa)
        assert result["success"] is False
        assert "Data" in result["error"] or "data" in result["error"]
        assert "mensagem_sugerida" in result

    @pytest.mark.asyncio
    async def test_sem_especialidade_retorna_erro(self, medico, conversa):
        from app.tools.vagas import handle_reservar_plantao

        medico_sem_esp = {**medico, "especialidade_id": None, "especialidade": None}
        result = await handle_reservar_plantao(
            {"data_plantao": "2025-01-20", "confirmacao": "ok"},
            medico_sem_esp,
            conversa,
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_vaga_nao_encontrada(self, medico, conversa):
        from app.tools.vagas import handle_reservar_plantao

        with patch("app.tools.vagas.supabase") as mock_sb:
            mock_response = MagicMock()
            mock_response.data = []
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
                mock_response
            )
            result = await handle_reservar_plantao(
                {"data_plantao": "2025-01-20", "confirmacao": "ok"},
                medico,
                conversa,
            )
            assert result["success"] is False
            assert "mensagem_sugerida" in result

    @pytest.mark.asyncio
    async def test_reserva_sucesso_shape(self, medico, conversa):
        from app.tools.vagas import handle_reservar_plantao

        vaga_id = str(uuid4())
        vaga = {
            "id": vaga_id,
            "data": "2025-01-20",
            "valor": 2500,
            "valor_minimo": None,
            "valor_maximo": None,
            "valor_tipo": "fixo",
            "status": "aberta",
            "source": None,
            "source_id": None,
            "hospitais": {"nome": "Hospital Teste", "endereco_formatado": "Rua X"},
            "periodos": {"nome": "noturno"},
            "setores": None,
        }

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch(
                "app.tools.vagas.reservar_vaga",
                new_callable=AsyncMock,
                return_value={"id": vaga_id, "status": "reservada", "data": "2025-01-20"},
            ),
            patch(
                "app.tools.vagas.formatar_vaga_para_mensagem",
                return_value="Noturno em Hospital Teste dia 20/01",
            ),
        ):
            mock_response = MagicMock()
            mock_response.data = [vaga]
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
                mock_response
            )

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-01-20", "confirmacao": "ok"},
                medico,
                conversa,
            )
            assert result["success"] is True
            assert "vaga" in result
            assert "instrucao" in result
            vaga_data = result["vaga"]
            assert "id" in vaga_data
            assert "hospital" in vaga_data
            assert "data" in vaga_data
            assert "valor_tipo" in vaga_data


# =============================================================================
# handle_buscar_info_hospital
# =============================================================================


class TestHandleBuscarInfoHospital:
    """Testa handle_buscar_info_hospital - busca de info de hospital."""

    @pytest.mark.asyncio
    async def test_sem_nome_retorna_erro(self, medico, conversa):
        from app.tools.vagas import handle_buscar_info_hospital

        result = await handle_buscar_info_hospital({}, medico, conversa)
        assert result["success"] is False
        assert "mensagem_sugerida" in result

    @pytest.mark.asyncio
    async def test_hospital_encontrado_shape(self, medico, conversa):
        from app.tools.vagas import handle_buscar_info_hospital

        with patch("app.tools.vagas.supabase") as mock_sb:
            mock_response = MagicMock()
            mock_response.data = [
                {
                    "nome": "Hospital São Luiz",
                    "endereco_formatado": "Rua X, 123",
                    "logradouro": "Rua X",
                    "numero": "123",
                    "bairro": "Centro",
                    "cidade": "São Paulo",
                    "estado": "SP",
                    "cep": "01001-000",
                }
            ]
            mock_sb.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = (
                mock_response
            )

            result = await handle_buscar_info_hospital(
                {"nome_hospital": "São Luiz"}, medico, conversa
            )
            assert result["success"] is True
            assert "hospital" in result
            hospital = result["hospital"]
            assert "nome" in hospital
            assert "endereco" in hospital
            assert "cidade" in hospital
            assert "instrucao" in result

    @pytest.mark.asyncio
    async def test_hospital_nao_encontrado(self, medico, conversa):
        from app.tools.vagas import handle_buscar_info_hospital

        with patch("app.tools.vagas.supabase") as mock_sb:
            mock_response = MagicMock()
            mock_response.data = []
            mock_sb.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = (
                mock_response
            )

            result = await handle_buscar_info_hospital(
                {"nome_hospital": "Inexistente"}, medico, conversa
            )
            assert result["success"] is False
            assert "mensagem_sugerida" in result


# =============================================================================
# Helpers internos
# =============================================================================


class TestHelpers:
    """Testa funções auxiliares."""

    def test_limpar_especialidade_input_none(self):
        from app.tools.vagas import _limpar_especialidade_input

        assert _limpar_especialidade_input(None) is None
        assert _limpar_especialidade_input("") is None

    def test_limpar_especialidade_input_normal(self):
        from app.tools.vagas import _limpar_especialidade_input

        assert _limpar_especialidade_input("cardiologia") == "cardiologia"

    def test_limpar_especialidade_input_array_json(self):
        from app.tools.vagas import _limpar_especialidade_input

        result = _limpar_especialidade_input('["cardiologia"]')
        assert result == "cardiologia"

    def test_preparar_medico_com_preferencias(self):
        from app.tools.vagas import _preparar_medico_com_preferencias

        medico = {"id": "123", "preferencias_detectadas": {"turno": "noturno"}}
        result = _preparar_medico_com_preferencias(medico, 2000)
        assert result["preferencias_detectadas"]["valor_minimo"] == 2000
        assert result["preferencias_detectadas"]["turno"] == "noturno"

    def test_preparar_medico_sem_valor_minimo(self):
        from app.tools.vagas import _preparar_medico_com_preferencias

        medico = {"id": "123", "preferencias_detectadas": None}
        result = _preparar_medico_com_preferencias(medico, 0)
        assert "valor_minimo" not in result["preferencias_detectadas"]
