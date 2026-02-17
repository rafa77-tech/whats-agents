"""
Testes de merge e limpeza de hospitais.

Sprint 60 - Épico 3: Limpeza de dados existentes.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.grupos.hospital_cleanup import (
    deletar_hospital_seguro,
    listar_candidatos_limpeza_tier1,
    mesclar_hospitais,
)


MOCK_PRINCIPAL = "aaaa1111-0000-0000-0000-000000000001"
MOCK_DUPLICADO = "bbbb2222-0000-0000-0000-000000000002"


class TestMesclarHospitais:
    """Testes da função mesclar_hospitais()."""

    @pytest.mark.asyncio
    async def test_merge_retorna_contagens(self):
        """Merge retorna JSON com contagens de registros migrados."""
        mock_result = {
            "principal_id": MOCK_PRINCIPAL,
            "duplicado_id": MOCK_DUPLICADO,
            "duplicado_nome": "Hospital Duplicado",
            "vagas_migradas": 5,
            "vagas_grupo_migradas": 3,
            "eventos_migrados": 10,
            "alertas_migrados": 2,
            "grupos_migrados": 1,
            "conhecimento_migrado": 0,
            "diretrizes_migradas": 0,
            "bloqueios_migrados": 0,
            "aliases_migrados": 2,
        }

        with patch("app.services.grupos.hospital_cleanup.supabase") as mock_supa:
            mock_supa.rpc.return_value.execute.return_value = MagicMock(
                data=mock_result
            )

            result = await mesclar_hospitais(MOCK_PRINCIPAL, MOCK_DUPLICADO)

            assert result is not None
            assert result["vagas_migradas"] == 5
            assert result["aliases_migrados"] == 2
            mock_supa.rpc.assert_called_once_with(
                "mesclar_hospitais",
                {
                    "p_principal_id": MOCK_PRINCIPAL,
                    "p_duplicado_id": MOCK_DUPLICADO,
                    "p_executado_por": "system",
                },
            )

    @pytest.mark.asyncio
    async def test_merge_com_executor_custom(self):
        """Merge passa executado_por corretamente."""
        with patch("app.services.grupos.hospital_cleanup.supabase") as mock_supa:
            mock_supa.rpc.return_value.execute.return_value = MagicMock(data={})

            await mesclar_hospitais(MOCK_PRINCIPAL, MOCK_DUPLICADO, "dashboard_user")

            call_args = mock_supa.rpc.call_args[0][1]
            assert call_args["p_executado_por"] == "dashboard_user"

    @pytest.mark.asyncio
    async def test_merge_propaga_erro(self):
        """Merge propaga exceção do banco."""
        with patch("app.services.grupos.hospital_cleanup.supabase") as mock_supa:
            mock_supa.rpc.return_value.execute.side_effect = Exception(
                "Hospital principal não encontrado"
            )

            with pytest.raises(Exception, match="Hospital principal"):
                await mesclar_hospitais(MOCK_PRINCIPAL, MOCK_DUPLICADO)


class TestDeletarHospitalSeguro:
    """Testes da função deletar_hospital_seguro()."""

    @pytest.mark.asyncio
    async def test_deleta_hospital_sem_fks(self):
        """Retorna True quando hospital sem referências é deletado."""
        with patch("app.services.grupos.hospital_cleanup.supabase") as mock_supa:
            mock_supa.rpc.return_value.execute.return_value = MagicMock(data=True)

            result = await deletar_hospital_seguro(MOCK_PRINCIPAL)

            assert result is True

    @pytest.mark.asyncio
    async def test_nao_deleta_hospital_com_fks(self):
        """Retorna False quando hospital tem referências."""
        with patch("app.services.grupos.hospital_cleanup.supabase") as mock_supa:
            mock_supa.rpc.return_value.execute.return_value = MagicMock(data=False)

            result = await deletar_hospital_seguro(MOCK_PRINCIPAL)

            assert result is False

    @pytest.mark.asyncio
    async def test_retorna_false_em_caso_de_erro(self):
        """Retorna False quando ocorre exceção."""
        with patch("app.services.grupos.hospital_cleanup.supabase") as mock_supa:
            mock_supa.rpc.return_value.execute.side_effect = Exception("DB error")

            result = await deletar_hospital_seguro(MOCK_PRINCIPAL)

            assert result is False


class TestListarCandidatosTier1:
    """Testes de listagem de candidatos para limpeza."""

    @pytest.mark.asyncio
    async def test_filtra_nomes_invalidos(self):
        """Retorna apenas hospitais cujos nomes falham no validador."""
        hospitais_mock = [
            {"id": "1", "nome": "AMAZON"},
            {"id": "2", "nome": "Hospital São Luiz"},
            {"id": "3", "nome": "GINECOLOGIA"},
            {"id": "4", "nome": "inbox"},
        ]

        with patch("app.services.grupos.hospital_cleanup.supabase") as mock_supa:
            mock_supa.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=hospitais_mock
            )

            candidatos = await listar_candidatos_limpeza_tier1()

            # AMAZON, GINECOLOGIA, inbox são inválidos
            nomes = [c["nome"] for c in candidatos]
            assert "AMAZON" in nomes
            assert "GINECOLOGIA" in nomes
            assert "inbox" in nomes
            assert "Hospital São Luiz" not in nomes

    @pytest.mark.asyncio
    async def test_lista_vazia(self):
        """Retorna lista vazia quando todos os nomes são válidos."""
        with patch("app.services.grupos.hospital_cleanup.supabase") as mock_supa:
            mock_supa.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"id": "1", "nome": "Hospital ABC"}]
            )

            candidatos = await listar_candidatos_limpeza_tier1()

            assert len(candidatos) == 0
