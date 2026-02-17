"""
Testes do validador de nomes de hospitais.

Sprint 60 - Épico 1: Gate de validação de nomes.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.grupos.hospital_validator import (
    ResultadoValidacao,
    validar_nome_hospital,
)


# =============================================================================
# Testes unitários do validador
# =============================================================================


class TestValidarNomeHospital:
    """Testes da função validar_nome_hospital()."""

    # --- Rejeições ---

    def test_rejeita_nome_vazio(self):
        result = validar_nome_hospital("")
        assert not result.valido
        assert result.motivo == "nome_vazio"

    def test_rejeita_nome_none_like(self):
        result = validar_nome_hospital("   ")
        assert not result.valido
        assert result.motivo == "nome_muito_curto"

    def test_rejeita_nome_muito_curto(self):
        for nome in ["AB", "X", "  a "]:
            result = validar_nome_hospital(nome)
            assert not result.valido, f"Deveria rejeitar: '{nome}'"
            assert result.motivo == "nome_muito_curto"

    def test_rejeita_nome_sem_letras(self):
        for nome in ["123", "---", "...", "456789"]:
            result = validar_nome_hospital(nome)
            assert not result.valido, f"Deveria rejeitar: '{nome}'"
            assert result.motivo == "sem_letras"

    def test_rejeita_nome_muito_longo(self):
        nome = "A" * 121
        result = validar_nome_hospital(nome)
        assert not result.valido
        assert result.motivo == "nome_muito_longo"

    def test_aceita_nome_120_chars(self):
        nome = "Hospital " + "A" * 111
        result = validar_nome_hospital(nome)
        assert result.valido

    def test_rejeita_padrao_contato(self):
        exemplos = [
            "amar: Queila ()-",
            "João: Maria (11)",
            "contato: Ana (SP)",
        ]
        for nome in exemplos:
            result = validar_nome_hospital(nome)
            assert not result.valido, f"Deveria rejeitar contato: '{nome}'"
            assert "blocklist_regex" in result.motivo

    def test_rejeita_palavras_blocklist(self):
        exemplos = [
            "AMAZON",
            "hospedagem",
            "inbox",
            "Mercado Envios",
            "atacadão",
            "Ypioca",
            "a definir",
            "não informado",
            "teste",
        ]
        for nome in exemplos:
            result = validar_nome_hospital(nome)
            assert not result.valido, f"Deveria rejeitar blocklist: '{nome}'"
            assert "blocklist" in result.motivo

    def test_rejeita_especialidades(self):
        exemplos = [
            "GINECOLOGIA",
            "Ortopedia",
            "CARDIOLOGIA",
            "Pediatria",
            "Neurologia",
            "Urologia",
            "Dermatologia",
        ]
        for nome in exemplos:
            result = validar_nome_hospital(nome)
            assert not result.valido, f"Deveria rejeitar especialidade: '{nome}'"
            assert "especialidade_como_hospital" in result.motivo

    def test_rejeita_fragmentos_monetarios(self):
        exemplos = [
            "R$ 2.500",
            "R$1500",
            "VALOR BRUTO R$1500",
            "R$ 3.000,00 plantão",
        ]
        for nome in exemplos:
            result = validar_nome_hospital(nome)
            assert not result.valido, f"Deveria rejeitar monetário: '{nome}'"

    def test_rejeita_fragmento_truncado_1_palavra_curta(self):
        for nome in ["abcd"]:
            result = validar_nome_hospital(nome)
            assert not result.valido, f"Deveria rejeitar fragmento: '{nome}'"
            assert result.motivo == "fragmento_truncado"

        # SP e RJ são rejeitados, mas pelo motivo "nome_muito_curto" (< 3 chars)
        for nome in ["SP", "RJ"]:
            result = validar_nome_hospital(nome)
            assert not result.valido, f"Deveria rejeitar: '{nome}'"

        # "abc" tem 3 chars exatos — rejeitado como fragmento
        result = validar_nome_hospital("abc")
        assert not result.valido

    def test_rejeita_horarios(self):
        result = validar_nome_hospital("12h às 19h")
        assert not result.valido

    def test_rejeita_datas(self):
        result = validar_nome_hospital("15/03 segunda")
        assert not result.valido

    def test_rejeita_redes_sociais(self):
        result = validar_nome_hospital("WhatsApp grupo")
        assert not result.valido

    # --- Aceitações ---

    def test_aceita_hospitais_reais(self):
        exemplos = [
            "Hospital São Luiz",
            "UPA Santo André",
            "Santa Casa de Misericórdia",
            "Hospital Municipal Tide Setúbal",
            "Pronto Socorro Central",
            "Hospital Albert Einstein",
            "Hospital Sírio-Libanês",
            "Maternidade São Paulo",
            "Instituto do Coração",
            "Centro Médico ABC",
        ]
        for nome in exemplos:
            result = validar_nome_hospital(nome)
            assert result.valido, f"Deveria aceitar hospital: '{nome}'"
            assert result.score >= 0.8, f"Score baixo para: '{nome}'"

    def test_aceita_com_prefixo_score_alto(self):
        result = validar_nome_hospital("Hospital Regional de Cotia")
        assert result.valido
        assert result.score >= 0.9

    def test_aceita_nome_ambiguo_sem_prefixo(self):
        result = validar_nome_hospital("Beneficência Portuguesa")
        assert result.valido
        assert result.score >= 0.8

    def test_aceita_nome_multiplas_palavras_sem_prefixo(self):
        result = validar_nome_hospital("São Camilo Pompeia")
        assert result.valido
        assert result.score >= 0.4

    def test_aceita_palavra_unica_longa(self):
        result = validar_nome_hospital("Samaritano")
        assert result.valido
        assert result.score >= 0.3

    # --- Score ---

    def test_score_zero_para_invalidos(self):
        result = validar_nome_hospital("AMAZON")
        assert result.score == 0.0

    def test_score_alto_para_prefixo_hospitalar(self):
        result = validar_nome_hospital("Hospital São Paulo")
        assert result.score >= 0.9

    def test_score_medio_para_sem_prefixo(self):
        result = validar_nome_hospital("São Camilo Santana")
        assert result.score >= 0.4
        assert result.score <= 0.6


# =============================================================================
# Testes de integração com hospital_web.py
# =============================================================================


class TestValidadorIntegracaoHospitalWeb:
    """Testes de integração com normalizar_ou_criar_hospital()."""

    @pytest.mark.asyncio
    async def test_rejeita_nome_lixo_retorna_none(self):
        """normalizar_ou_criar_hospital retorna None para nomes lixo."""
        from app.services.grupos.hospital_web import normalizar_ou_criar_hospital

        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_similaridade",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await normalizar_ou_criar_hospital("AMAZON")
            assert result is None

    @pytest.mark.asyncio
    async def test_rejeita_contato_retorna_none(self):
        """normalizar_ou_criar_hospital retorna None para nomes de contato."""
        from app.services.grupos.hospital_web import normalizar_ou_criar_hospital

        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_similaridade",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await normalizar_ou_criar_hospital("amar: Queila ()-")
            assert result is None

    @pytest.mark.asyncio
    async def test_hospital_valido_continua_pipeline(self):
        """normalizar_ou_criar_hospital continua para nomes válidos."""
        from app.services.grupos.hospital_web import normalizar_ou_criar_hospital

        mock_hospital_id = "123e4567-e89b-12d3-a456-426614174000"

        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_similaridade",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.hospital_web.buscar_hospital_web",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.hospital_web.criar_hospital_minimo",
                new_callable=AsyncMock,
                return_value=mock_hospital_id,
            ),
        ):
            result = await normalizar_ou_criar_hospital("Hospital São Luiz")
            assert result is not None
            assert result.fonte == "fallback"

    @pytest.mark.asyncio
    async def test_alias_existente_bypassa_validacao(self):
        """Se alias existe, não passa pelo validador."""
        from app.services.grupos.hospital_web import normalizar_ou_criar_hospital

        mock_match = type(
            "Match",
            (),
            {
                "entidade_id": "123e4567-e89b-12d3-a456-426614174000",
                "nome": "Hospital Teste",
                "score": 1.0,
            },
        )()

        with patch(
            "app.services.grupos.normalizador.buscar_hospital_por_alias",
            new_callable=AsyncMock,
            return_value=mock_match,
        ):
            # Mesmo nome lixo, se alias existe, retorna
            result = await normalizar_ou_criar_hospital("AMAZON")
            assert result is not None
            assert result.fonte == "alias_exato"


# =============================================================================
# Testes de integração com extrator_hospitais.py
# =============================================================================


class TestValidadorIntegracaoExtrator:
    """Testes de integração com _extrair_nome_hospital()."""

    def test_extrator_rejeita_lixo(self):
        """_extrair_nome_hospital retorna vazio para lixo."""
        from app.services.grupos.extrator_v2.extrator_hospitais import (
            _extrair_nome_hospital,
        )

        # Blocklist exata
        nome, confianca = _extrair_nome_hospital("AMAZON")
        assert nome == ""
        assert confianca == 0.0

        # Especialidades
        nome, confianca = _extrair_nome_hospital("GINECOLOGIA")
        assert nome == ""
        assert confianca == 0.0

    def test_extrator_aceita_hospital(self):
        """_extrair_nome_hospital retorna nome para hospital válido."""
        from app.services.grupos.extrator_v2.extrator_hospitais import (
            _extrair_nome_hospital,
        )

        nome, confianca = _extrair_nome_hospital("Hospital São Luiz - Anália Franco")
        assert nome != ""
        assert "Hospital" in nome
        assert confianca > 0.0

    def test_extrator_rejeita_especialidade(self):
        """_extrair_nome_hospital rejeita especialidade como hospital."""
        from app.services.grupos.extrator_v2.extrator_hospitais import (
            _extrair_nome_hospital,
        )

        nome, confianca = _extrair_nome_hospital("GINECOLOGIA")
        assert nome == ""
        assert confianca == 0.0

    def test_extrator_ajusta_confianca_pelo_validador(self):
        """Confiança ajustada pelo score do validador."""
        from app.services.grupos.extrator_v2.extrator_hospitais import (
            _extrair_nome_hospital,
        )

        nome, confianca = _extrair_nome_hospital("Hospital Municipal Teste")
        assert nome != ""
        assert confianca <= 0.9  # Capped pelo validador
