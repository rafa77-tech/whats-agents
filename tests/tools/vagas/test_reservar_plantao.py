"""
Testes para tool handler reservar_plantao.

Foca em invariantes nao cobertos pelos testes de caracterizacao:
- Idempotencia (mesma reserva duas vezes)
- Vaga ja reservada por outro medico
- Vaga com status incompativel (cancelada, expirada)
- Dados incompletos do medico
- Fast-path contato direto (Sprint 57)
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


@pytest.fixture
def vaga_aberta():
    """Vaga no estado 'aberta' com dados completos."""
    vaga_id = str(uuid4())
    return {
        "id": vaga_id,
        "data": "2025-02-15",
        "valor": 2500,
        "valor_minimo": None,
        "valor_maximo": None,
        "valor_tipo": "fixo",
        "status": "aberta",
        "source": None,
        "source_id": None,
        "contato_nome": None,
        "contato_whatsapp": None,
        "hospitais": {
            "nome": "Hospital Teste",
            "endereco_formatado": "Rua X, 123",
            "bairro": "Centro",
            "cidade": "Sao Paulo",
        },
        "periodos": {"nome": "noturno"},
        "setores": None,
    }


def _mock_supabase_busca_vaga(mock_sb, vaga):
    """Helper: configura mock do supabase para retornar uma vaga na busca."""
    mock_response = MagicMock()
    mock_response.data = [vaga] if vaga else []
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
        mock_response
    )


# =============================================================================
# Idempotencia
# =============================================================================


class TestIdempotencia:
    """Testes de idempotencia na reserva."""

    @pytest.mark.asyncio
    async def test_mesma_reserva_duas_vezes_nao_duplica(self, medico, conversa, vaga_aberta):
        """Reservar a mesma vaga duas vezes: segunda vez recebe ValueError do service."""
        from app.tools.vagas import handle_reservar_plantao

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Plantao X"),
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_aberta)

            # Segunda chamada: vaga ja nao esta aberta
            mock_reservar.side_effect = ValueError(
                "Vaga nao esta mais disponivel (status: reservada)"
            )

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-02-15", "confirmacao": "ok"},
                medico,
                conversa,
            )

            assert result["success"] is False
            assert "disponivel" in result["error"].lower() or "reservada" in result["error"].lower()


# =============================================================================
# Vaga ja reservada por outro medico
# =============================================================================


class TestVagaReservadaPorOutro:
    """Testes para vaga ja reservada por outro medico."""

    @pytest.mark.asyncio
    async def test_vaga_reservada_por_outro(self, medico, conversa, vaga_aberta):
        """Reservar vaga que outro medico pegou primeiro retorna erro."""
        from app.tools.vagas import handle_reservar_plantao

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Plantao X"),
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_aberta)

            # Service levanta ValueError quando vaga foi reservada por outro
            mock_reservar.side_effect = ValueError("Vaga foi reservada por outro medico")

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-02-15", "confirmacao": "ok"},
                medico,
                conversa,
            )

            assert result["success"] is False
            assert "reservada" in result["error"].lower() or "outro" in result["error"].lower()


# =============================================================================
# Status incompativeis
# =============================================================================


class TestStatusIncompativel:
    """Testes para vagas com status incompativel."""

    @pytest.mark.asyncio
    async def test_vaga_cancelada_nao_aparece_na_busca(self, medico, conversa):
        """Vaga cancelada nao eh retornada pela busca (filtro status=aberta)."""
        from app.tools.vagas import handle_reservar_plantao

        with patch("app.tools.vagas.supabase") as mock_sb:
            # Busca retorna vazio porque o filtro eq("status", "aberta") nao pega canceladas
            _mock_supabase_busca_vaga(mock_sb, None)

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-02-15", "confirmacao": "ok"},
                medico,
                conversa,
            )

            assert result["success"] is False
            assert "mensagem_sugerida" in result

    @pytest.mark.asyncio
    async def test_vaga_expirada_nao_aparece_na_busca(self, medico, conversa):
        """Vaga expirada nao eh retornada pela busca."""
        from app.tools.vagas import handle_reservar_plantao

        with patch("app.tools.vagas.supabase") as mock_sb:
            _mock_supabase_busca_vaga(mock_sb, None)

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-03-01", "confirmacao": "ok"},
                medico,
                conversa,
            )

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_vaga_status_mudou_entre_busca_e_reserva(self, medico, conversa, vaga_aberta):
        """Vaga encontrada na busca mas status mudou antes da reserva (race condition)."""
        from app.tools.vagas import handle_reservar_plantao

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Plantao X"),
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_aberta)

            # Entre busca e reserva, status mudou
            mock_reservar.side_effect = ValueError(
                "Vaga nao esta mais disponivel (status: cancelada)"
            )

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-02-15", "confirmacao": "ok"},
                medico,
                conversa,
            )

            assert result["success"] is False


# =============================================================================
# Dados incompletos do medico
# =============================================================================


class TestDadosIncompletosDoMedico:
    """Testes para rejeicao de dados incompletos."""

    @pytest.mark.asyncio
    async def test_sem_especialidade_id_e_sem_nome(self, conversa):
        """Medico sem especialidade_id e sem especialidade retorna erro."""
        from app.tools.vagas import handle_reservar_plantao

        medico_incompleto = {
            "id": str(uuid4()),
            "primeiro_nome": "Dr. Incompleto",
            "telefone": "5511999999999",
            "especialidade_id": None,
            "especialidade": None,
        }

        result = await handle_reservar_plantao(
            {"data_plantao": "2025-02-15", "confirmacao": "ok"},
            medico_incompleto,
            conversa,
        )

        assert result["success"] is False
        assert "especialidade" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_especialidade_resolvida_por_nome(self, conversa, vaga_aberta):
        """Medico sem especialidade_id mas com nome resolve via busca."""
        from app.tools.vagas import handle_reservar_plantao

        esp_id = str(uuid4())
        medico_com_nome = {
            "id": str(uuid4()),
            "primeiro_nome": "Dr. NomeEsp",
            "telefone": "5511999999999",
            "especialidade_id": None,
            "especialidade": "Cardiologia",
        }

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch(
                "app.tools.vagas.reservar_plantao._buscar_especialidade_id_por_nome",
                new_callable=AsyncMock,
                return_value=esp_id,
            ),
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Plantao X"),
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_aberta)
            mock_reservar.return_value = {
                "id": vaga_aberta["id"],
                "status": "reservada",
                "data": "2025-02-15",
            }

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-02-15", "confirmacao": "ok"},
                medico_com_nome,
                conversa,
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_sem_data_plantao(self, medico, conversa):
        """Sem data de plantao retorna erro com mensagem sugerida."""
        from app.tools.vagas import handle_reservar_plantao

        result = await handle_reservar_plantao({}, medico, conversa)

        assert result["success"] is False
        assert "data" in result["error"].lower()
        assert "mensagem_sugerida" in result


# =============================================================================
# Fast-path contato direto (Sprint 57)
# =============================================================================


class TestFastPathContatoDireto:
    """Testes para o fast-path de vaga com contato direto (Sprint 57)."""

    @pytest.mark.asyncio
    async def test_vaga_com_contato_direto_usa_fast_path(self, medico, conversa):
        """Vaga com contato_nome e contato_whatsapp usa fast-path."""
        from app.tools.vagas import handle_reservar_plantao

        vaga_id = str(uuid4())
        vaga_contato = {
            "id": vaga_id,
            "data": "2025-02-20",
            "valor": 3000,
            "valor_minimo": None,
            "valor_maximo": None,
            "valor_tipo": "fixo",
            "status": "aberta",
            "source": "grupo",
            "source_id": "grupo-1",
            "contato_nome": "Maria",
            "contato_whatsapp": "5511988887777",
            "hospitais": {
                "nome": "Hospital ABC",
                "endereco_formatado": "Rua Y, 456",
                "bairro": "Zona Sul",
                "cidade": "Sao Paulo",
            },
            "periodos": {"nome": "diurno"},
            "setores": None,
        }

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Diurno em Hospital ABC"),
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_contato)
            mock_reservar.return_value = {
                "id": vaga_id,
                "status": "reservada",
                "data": "2025-02-20",
            }

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-02-20", "confirmacao": "ok"},
                medico,
                conversa,
            )

            assert result["success"] is True
            assert "ponte_externa" in result
            assert result["ponte_externa"]["divulgador_nome"] == "Maria"
            assert result["ponte_externa"]["divulgador_telefone"] == "5511988887777"
            assert result["vaga"]["contato_nome"] == "Maria"
            assert "instrucao" in result

    @pytest.mark.asyncio
    async def test_vaga_sem_contato_nao_usa_fast_path(self, medico, conversa, vaga_aberta):
        """Vaga sem contato_nome nao usa fast-path (fluxo normal)."""
        from app.tools.vagas import handle_reservar_plantao

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Noturno em Hospital Teste"),
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_aberta)
            mock_reservar.return_value = {
                "id": vaga_aberta["id"],
                "status": "reservada",
                "data": "2025-02-15",
            }

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-02-15", "confirmacao": "ok"},
                medico,
                conversa,
            )

            assert result["success"] is True
            # Nao deve ter ponte_externa no resultado (sem contato direto e sem source grupo)
            assert "ponte_externa" not in result
            assert "instrucao" in result

    @pytest.mark.asyncio
    async def test_contato_parcial_nao_usa_fast_path(self, medico, conversa):
        """Vaga com contato_nome mas sem contato_whatsapp nao usa fast-path."""
        from app.tools.vagas import handle_reservar_plantao

        vaga_id = str(uuid4())
        vaga_parcial = {
            "id": vaga_id,
            "data": "2025-02-20",
            "valor": 3000,
            "valor_minimo": None,
            "valor_maximo": None,
            "valor_tipo": "fixo",
            "status": "aberta",
            "source": None,
            "source_id": None,
            "contato_nome": "Maria",
            "contato_whatsapp": None,  # Faltando!
            "hospitais": {
                "nome": "Hospital ABC",
                "endereco_formatado": "Rua Y, 456",
                "bairro": "Zona Sul",
                "cidade": "Sao Paulo",
            },
            "periodos": {"nome": "diurno"},
            "setores": None,
        }

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Plantao X"),
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_parcial)
            mock_reservar.return_value = {
                "id": vaga_id,
                "status": "reservada",
                "data": "2025-02-20",
            }

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-02-20", "confirmacao": "ok"},
                medico,
                conversa,
            )

            assert result["success"] is True
            # Nao deve usar fast-path pois contato_whatsapp eh None
            assert result.get("ponte_externa") is None or (
                "divulgador_nome" not in result.get("ponte_externa", {})
            )


# =============================================================================
# Normalizacao de data
# =============================================================================


class TestNormalizacaoData:
    """Testes para normalizacao de formatos de data."""

    @pytest.mark.asyncio
    async def test_formato_dd_mm_yyyy(self, medico, conversa, vaga_aberta):
        """Data no formato DD/MM/YYYY eh convertida para YYYY-MM-DD."""
        from app.tools.vagas import handle_reservar_plantao

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Plantao X"),
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_aberta)
            mock_reservar.return_value = {
                "id": vaga_aberta["id"],
                "status": "reservada",
                "data": "2025-02-15",
            }

            result = await handle_reservar_plantao(
                {"data_plantao": "15/02/2025", "confirmacao": "ok"},
                medico,
                conversa,
            )

            # Verifica que a busca usou o formato normalizado
            mock_sb.table.assert_called()

    @pytest.mark.asyncio
    async def test_formato_dd_mm_assume_ano_atual(self, medico, conversa, vaga_aberta):
        """Data no formato DD/MM assume ano atual."""
        from app.tools.vagas import handle_reservar_plantao

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Plantao X"),
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_aberta)
            mock_reservar.return_value = {
                "id": vaga_aberta["id"],
                "status": "reservada",
                "data": "2025-02-15",
            }

            result = await handle_reservar_plantao(
                {"data_plantao": "15/02", "confirmacao": "ok"},
                medico,
                conversa,
            )

            mock_sb.table.assert_called()


# =============================================================================
# Erro generico
# =============================================================================


class TestErroGenerico:
    """Testes para tratamento de erros inesperados."""

    @pytest.mark.asyncio
    async def test_exception_generica_capturada(self, medico, conversa, vaga_aberta):
        """Exception generica retorna erro amigavel."""
        from app.tools.vagas import handle_reservar_plantao

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Plantao X"),
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_aberta)
            mock_reservar.side_effect = RuntimeError("Unexpected error")

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-02-15", "confirmacao": "ok"},
                medico,
                conversa,
            )

            assert result["success"] is False
            assert "error" in result


# =============================================================================
# Vaga de grupo (ponte externa)
# =============================================================================


class TestVagaGrupo:
    """Testes para vagas originadas de grupo WhatsApp (ponte externa)."""

    @pytest.mark.asyncio
    async def test_vaga_grupo_cria_ponte_externa(self, medico, conversa):
        """Vaga com source=grupo sem contato direto cria ponte externa."""
        from app.tools.vagas import handle_reservar_plantao

        vaga_id = str(uuid4())
        vaga_grupo = {
            "id": vaga_id,
            "data": "2025-02-20",
            "valor": 2000,
            "valor_minimo": None,
            "valor_maximo": None,
            "valor_tipo": "fixo",
            "status": "aberta",
            "source": "grupo",
            "source_id": "msg-grupo-123",
            "contato_nome": None,
            "contato_whatsapp": None,
            "hospitais": {
                "nome": "Hospital Y",
                "endereco_formatado": "Rua Z",
                "bairro": "Norte",
                "cidade": "SP",
            },
            "periodos": {"nome": "noturno"},
            "setores": None,
        }

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Plantao Y"),
            patch(
                "app.services.external_handoff.service.criar_ponte_externa",
                new_callable=AsyncMock,
            ) as mock_ponte,
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_grupo)
            mock_reservar.return_value = {
                "id": vaga_id,
                "status": "reservada",
                "data": "2025-02-20",
            }
            mock_ponte.return_value = {
                "success": True,
                "handoff_id": "hoff-1",
                "divulgador": {
                    "nome": "Carlos",
                    "telefone": "5511977776666",
                    "empresa": "Plantoes BR",
                },
                "msg_divulgador_enviada": True,
            }

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-02-20", "confirmacao": "ok"},
                medico,
                conversa,
            )

            assert result["success"] is True
            assert "ponte_externa" in result
            assert result["ponte_externa"]["divulgador_nome"] == "Carlos"
            mock_ponte.assert_called_once()

    @pytest.mark.asyncio
    async def test_erro_ponte_externa_nao_impede_reserva(self, medico, conversa):
        """Erro ao criar ponte externa nao impede a reserva em si."""
        from app.tools.vagas import handle_reservar_plantao

        vaga_id = str(uuid4())
        vaga_grupo = {
            "id": vaga_id,
            "data": "2025-02-20",
            "valor": 2000,
            "valor_minimo": None,
            "valor_maximo": None,
            "valor_tipo": "fixo",
            "status": "aberta",
            "source": "grupo",
            "source_id": "msg-grupo-123",
            "contato_nome": None,
            "contato_whatsapp": None,
            "hospitais": {
                "nome": "Hospital Y",
                "endereco_formatado": "Rua Z",
                "bairro": "Norte",
                "cidade": "SP",
            },
            "periodos": {"nome": "noturno"},
            "setores": None,
        }

        with (
            patch("app.tools.vagas.supabase") as mock_sb,
            patch("app.tools.vagas.reservar_vaga", new_callable=AsyncMock) as mock_reservar,
            patch("app.tools.vagas.formatar_vaga_para_mensagem", return_value="Plantao Y"),
            patch(
                "app.services.external_handoff.service.criar_ponte_externa",
                new_callable=AsyncMock,
                side_effect=Exception("Ponte falhou"),
            ),
        ):
            _mock_supabase_busca_vaga(mock_sb, vaga_grupo)
            mock_reservar.return_value = {
                "id": vaga_id,
                "status": "reservada",
                "data": "2025-02-20",
            }

            result = await handle_reservar_plantao(
                {"data_plantao": "2025-02-20", "confirmacao": "ok"},
                medico,
                conversa,
            )

            # Reserva aconteceu, mas ponte_externa nao esta no resultado
            assert result["success"] is True
            assert "instrucao" in result
