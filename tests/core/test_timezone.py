"""
Testes para o módulo de timezone.

Sprint 40 - Padronização de fuso horário.
"""

import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.timezone import (
    TZ_BRASILIA,
    TZ_UTC,
    agora_utc,
    agora_brasilia,
    para_brasilia,
    para_utc,
    formatar_data_brasilia,
    hoje_brasilia,
    iso_utc,
)


class TestTimezoneConstants:
    """Testes para constantes de timezone."""

    def test_tz_brasilia_is_sao_paulo(self):
        """TZ_BRASILIA deve ser America/Sao_Paulo."""
        assert TZ_BRASILIA == ZoneInfo("America/Sao_Paulo")

    def test_tz_utc_is_utc(self):
        """TZ_UTC deve ser UTC."""
        assert TZ_UTC == timezone.utc


class TestAgoraUtc:
    """Testes para agora_utc()."""

    def test_retorna_datetime_timezone_aware(self):
        """agora_utc() deve retornar datetime com timezone."""
        dt = agora_utc()
        assert dt.tzinfo is not None

    def test_retorna_datetime_em_utc(self):
        """agora_utc() deve retornar datetime em UTC."""
        dt = agora_utc()
        assert dt.tzinfo == TZ_UTC

    def test_retorna_horario_proximo_do_agora(self):
        """agora_utc() deve retornar horário próximo do atual."""
        dt1 = datetime.now(timezone.utc)
        dt2 = agora_utc()
        diff = abs((dt2 - dt1).total_seconds())
        assert diff < 1  # Menos de 1 segundo de diferença


class TestAgoraBrasilia:
    """Testes para agora_brasilia()."""

    def test_retorna_datetime_timezone_aware(self):
        """agora_brasilia() deve retornar datetime com timezone."""
        dt = agora_brasilia()
        assert dt.tzinfo is not None

    def test_retorna_datetime_em_brasilia(self):
        """agora_brasilia() deve retornar datetime em São Paulo."""
        dt = agora_brasilia()
        assert dt.tzinfo == TZ_BRASILIA

    def test_diferenca_com_utc(self):
        """agora_brasilia() deve ter diferença correta com UTC."""
        dt_utc = agora_utc()
        dt_brt = agora_brasilia()

        # Converter ambos para UTC para comparar
        dt_brt_as_utc = dt_brt.astimezone(TZ_UTC)
        diff = abs((dt_utc - dt_brt_as_utc).total_seconds())
        assert diff < 1  # Menos de 1 segundo (são o mesmo momento)


class TestParaBrasilia:
    """Testes para para_brasilia()."""

    def test_converte_utc_para_brasilia(self):
        """para_brasilia() deve converter UTC para Brasília."""
        dt_utc = datetime(2025, 1, 15, 15, 0, 0, tzinfo=TZ_UTC)  # 15:00 UTC
        dt_brt = para_brasilia(dt_utc)

        assert dt_brt.tzinfo == TZ_BRASILIA
        # No verão, Brasília é UTC-3 (sem horário de verão desde 2019)
        # 15:00 UTC = 12:00 BRT
        assert dt_brt.hour == 12

    def test_converte_naive_assumindo_utc(self):
        """para_brasilia() com datetime naive deve assumir UTC."""
        dt_naive = datetime(2025, 1, 15, 15, 0, 0)  # Naive
        dt_brt = para_brasilia(dt_naive)

        assert dt_brt.tzinfo == TZ_BRASILIA
        assert dt_brt.hour == 12  # 15:00 UTC = 12:00 BRT


class TestParaUtc:
    """Testes para para_utc()."""

    def test_converte_brasilia_para_utc(self):
        """para_utc() deve converter Brasília para UTC."""
        dt_brt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=TZ_BRASILIA)  # 12:00 BRT
        dt_utc = para_utc(dt_brt)

        assert dt_utc.tzinfo == TZ_UTC
        # 12:00 BRT = 15:00 UTC
        assert dt_utc.hour == 15

    def test_converte_naive_assumindo_brasilia(self):
        """para_utc() com datetime naive deve assumir Brasília."""
        dt_naive = datetime(2025, 1, 15, 12, 0, 0)  # Naive
        dt_utc = para_utc(dt_naive)

        assert dt_utc.tzinfo == TZ_UTC
        assert dt_utc.hour == 15  # 12:00 BRT = 15:00 UTC


class TestFormatarDataBrasilia:
    """Testes para formatar_data_brasilia()."""

    def test_formata_utc_para_exibicao_brasilia(self):
        """formatar_data_brasilia() deve formatar em horário de Brasília."""
        dt_utc = datetime(2025, 1, 15, 15, 30, 0, tzinfo=TZ_UTC)
        resultado = formatar_data_brasilia(dt_utc)

        # 15:30 UTC = 12:30 BRT
        assert "12:30" in resultado
        assert "15/01/2025" in resultado

    def test_formato_customizado(self):
        """formatar_data_brasilia() deve aceitar formato customizado."""
        dt_utc = datetime(2025, 1, 15, 15, 30, 0, tzinfo=TZ_UTC)
        resultado = formatar_data_brasilia(dt_utc, formato="%H:%M")

        assert resultado == "12:30"


class TestHojeBrasilia:
    """Testes para hoje_brasilia()."""

    def test_retorna_meia_noite(self):
        """hoje_brasilia() deve retornar meia-noite."""
        dt = hoje_brasilia()

        assert dt.hour == 0
        assert dt.minute == 0
        assert dt.second == 0
        assert dt.microsecond == 0

    def test_retorna_timezone_brasilia(self):
        """hoje_brasilia() deve estar em timezone Brasília."""
        dt = hoje_brasilia()
        assert dt.tzinfo == TZ_BRASILIA


class TestIsoUtc:
    """Testes para iso_utc()."""

    def test_retorna_string_iso_utc(self):
        """iso_utc() deve retornar string ISO em UTC."""
        dt = datetime(2025, 1, 15, 12, 30, 45, tzinfo=TZ_BRASILIA)
        resultado = iso_utc(dt)

        # 12:30 BRT = 15:30 UTC
        assert "15:30:45" in resultado
        assert "+00:00" in resultado

    def test_sem_argumento_usa_agora(self):
        """iso_utc() sem argumento deve usar hora atual."""
        resultado = iso_utc()

        # Deve ser uma string ISO válida
        assert "T" in resultado
        assert "+00:00" in resultado
