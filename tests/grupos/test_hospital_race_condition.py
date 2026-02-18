"""
Testes de race condition para criação de hospitais.

Sprint 60 - Épico 2: Fix de Race Condition com Lock Atômico.
"""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest


MOCK_HOSPITAL_ID = "d1a298d9-5501-4ffb-afee-99a3218a9a7a"


def _mock_rpc_response(foi_criado: bool, nome: str = "Hospital Teste"):
    """Helper para criar mock de resposta do RPC."""
    mock = MagicMock()
    mock.data = [
        {
            "out_hospital_id": MOCK_HOSPITAL_ID,
            "out_nome": nome,
            "out_foi_criado": foi_criado,
        }
    ]
    return mock


class TestCriarHospitalUsaRPC:
    """Verifica que criar_hospital() usa RPC ao invés de INSERT direto."""

    @pytest.mark.asyncio
    async def test_criar_hospital_chama_rpc(self):
        """criar_hospital chama buscar_ou_criar_hospital via RPC."""
        from app.services.grupos.hospital_web import InfoHospitalWeb, criar_hospital

        info = InfoHospitalWeb(
            nome_oficial="Hospital São Paulo",
            cidade="São Paulo",
            estado="SP",
            confianca=0.8,
        )

        mock_rpc = MagicMock(return_value=MagicMock())
        mock_rpc.return_value.execute.return_value = _mock_rpc_response(True)

        with patch("app.services.grupos.hospital_web.supabase") as mock_supa:
            mock_supa.rpc = mock_rpc
            result = await criar_hospital(info, "Hosp São Paulo")

            mock_rpc.assert_called_once_with(
                "buscar_ou_criar_hospital",
                {
                    "p_nome": "Hospital São Paulo",
                    "p_alias_normalizado": "hosp sao paulo",
                    "p_cidade": "São Paulo",
                    "p_estado": "SP",
                    "p_confianca": 0.8,
                    "p_criado_por": "busca_web",
                },
            )
            assert result == UUID(MOCK_HOSPITAL_ID)

    @pytest.mark.asyncio
    async def test_criar_hospital_reutilizado(self):
        """criar_hospital retorna hospital existente quando RPC diz foi_criado=false."""
        from app.services.grupos.hospital_web import InfoHospitalWeb, criar_hospital

        info = InfoHospitalWeb(
            nome_oficial="Hospital Existente",
            cidade="São Paulo",
            estado="SP",
            confianca=0.9,
        )

        mock_rpc = MagicMock(return_value=MagicMock())
        mock_rpc.return_value.execute.return_value = _mock_rpc_response(
            False, "Hospital Existente Original"
        )

        with patch("app.services.grupos.hospital_web.supabase") as mock_supa:
            mock_supa.rpc = mock_rpc
            result = await criar_hospital(info, "Hosp Existente")

            assert result == UUID(MOCK_HOSPITAL_ID)


class TestIdempotencia:
    """Verifica idempotência via RPC."""

    @pytest.mark.asyncio
    async def test_mesma_chamada_duas_vezes_mesmo_resultado(self):
        """Duas chamadas com mesmo alias retornam mesmo hospital_id."""
        from app.services.grupos.hospital_web import InfoHospitalWeb, criar_hospital

        info = InfoHospitalWeb(
            nome_oficial="Hospital X",
            cidade="São Paulo",
            estado="SP",
            confianca=0.8,
        )

        mock_rpc = MagicMock(return_value=MagicMock())
        # Primeira chamada: criou. Segunda: reutilizou.
        mock_rpc.return_value.execute.side_effect = [
            _mock_rpc_response(True),
            _mock_rpc_response(False),
        ]

        with patch("app.services.grupos.hospital_web.supabase") as mock_supa:
            mock_supa.rpc = mock_rpc
            result1 = await criar_hospital(info, "Hospital X")
            result2 = await criar_hospital(info, "Hospital X")

            assert result1 == result2
            assert mock_rpc.call_count == 2
