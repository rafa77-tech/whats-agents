"""
Testes para severity_mapper.

Sprint 15 - Policy Engine
"""
import pytest

from app.services.classificacao.severity_mapper import (
    map_severity,
    is_opt_out,
    is_handoff_required,
    ObjectionSeverity,
    GRAVE_KEYWORDS,
    HIGH_KEYWORDS,
)


class TestMapSeverity:
    """Testes para map_severity."""

    def test_type_mapping_low(self):
        """Tipos LOW mapeiam corretamente."""
        assert map_severity("comunicacao", None, "prefiro por email") == ObjectionSeverity.LOW
        assert map_severity("disponibilidade", None, "agora não posso") == ObjectionSeverity.LOW

    def test_type_mapping_medium(self):
        """Tipos MEDIUM mapeiam corretamente."""
        assert map_severity("preco", None, "está caro") == ObjectionSeverity.MEDIUM
        assert map_severity("tempo", None, "não tenho tempo") == ObjectionSeverity.MEDIUM
        assert map_severity("processo", None, "muito burocrático") == ObjectionSeverity.MEDIUM

    def test_type_mapping_high(self):
        """Tipos HIGH mapeiam corretamente."""
        assert map_severity("confianca", None, "desconfio de vocês") == ObjectionSeverity.HIGH
        assert map_severity("qualidade", None, "hospital ruim") == ObjectionSeverity.HIGH

    def test_type_mapping_grave(self):
        """Tipos GRAVE mapeiam corretamente."""
        assert map_severity("opt_out", None, "não me procure") == ObjectionSeverity.GRAVE
        assert map_severity("ameaca", None, "vou processar") == ObjectionSeverity.GRAVE
        assert map_severity("pedido_humano", None, "quero falar com pessoa") == ObjectionSeverity.GRAVE


class TestKeywordOverride:
    """Testes para keywords que elevam severidade."""

    def test_grave_keywords_override(self):
        """Keywords graves elevam para GRAVE independente do tipo."""
        # Tipo seria LOW, mas keyword eleva
        result = map_severity("comunicacao", None, "não me procure mais")
        assert result == ObjectionSeverity.GRAVE

        result = map_severity("preco", None, "vou denunciar vocês")
        assert result == ObjectionSeverity.GRAVE

        result = map_severity("tempo", None, "isso é spam")
        assert result == ObjectionSeverity.GRAVE

    def test_high_keywords_override(self):
        """Keywords HIGH elevam para HIGH se não for GRAVE."""
        # Tipo seria LOW, mas keyword eleva para HIGH
        result = map_severity("comunicacao", None, "desconfio muito de vocês")
        assert result == ObjectionSeverity.HIGH

        result = map_severity("disponibilidade", None, "péssimo atendimento")
        assert result == ObjectionSeverity.HIGH

    def test_grave_keywords_not_overridden_by_high(self):
        """Keywords HIGH não elevam se já é GRAVE."""
        # Tipo GRAVE + keyword HIGH = ainda GRAVE
        result = map_severity("ameaca", None, "desconfio muito")
        assert result == ObjectionSeverity.GRAVE

    def test_all_grave_keywords_work(self):
        """Todas as keywords graves funcionam."""
        for keyword in GRAVE_KEYWORDS:
            result = map_severity("comunicacao", None, f"blah {keyword} blah")
            assert result == ObjectionSeverity.GRAVE, f"Keyword '{keyword}' não elevou para GRAVE"


class TestIsOptOut:
    """Testes para is_opt_out."""

    def test_explicit_type_opt_out(self):
        """Tipo explícito opt_out é detectado."""
        assert is_opt_out("opt_out", "qualquer coisa") is True

    def test_keyword_opt_out(self):
        """Keywords de opt-out são detectadas."""
        assert is_opt_out("comunicacao", "não me procure mais") is True
        assert is_opt_out("preco", "para de me mandar mensagem") is True
        assert is_opt_out("tempo", "me tire da lista") is True
        assert is_opt_out("qualidade", "remove meu número") is True

    def test_not_opt_out(self):
        """Mensagens normais não são opt-out."""
        assert is_opt_out("preco", "está caro demais") is False
        assert is_opt_out("tempo", "agora não posso") is False
        assert is_opt_out("confianca", "desconfio de vocês") is False

    def test_case_insensitive(self):
        """Detecção é case insensitive."""
        assert is_opt_out("comunicacao", "NÃO ME PROCURE MAIS") is True
        assert is_opt_out("preco", "Para De Me Mandar") is True


class TestIsHandoffRequired:
    """Testes para is_handoff_required."""

    def test_grave_requires_handoff(self):
        """Objeção grave requer handoff."""
        assert is_handoff_required("ameaca", "vou processar") is True
        assert is_handoff_required("opt_out", "não me procure") is True

    def test_grave_keyword_requires_handoff(self):
        """Keyword grave requer handoff."""
        assert is_handoff_required("comunicacao", "vou denunciar vocês") is True
        assert is_handoff_required("preco", "isso é golpe") is True

    def test_medium_does_not_require_handoff(self):
        """Objeção medium não requer handoff."""
        assert is_handoff_required("preco", "está caro") is False
        assert is_handoff_required("tempo", "não tenho tempo") is False

    def test_high_does_not_require_handoff(self):
        """Objeção high não requer handoff (só cautela)."""
        assert is_handoff_required("confianca", "desconfio de vocês") is False


class TestDefaultSeverity:
    """Testes para severidade padrão."""

    def test_unknown_type_defaults_to_medium(self):
        """Tipo desconhecido usa severidade MEDIUM."""
        result = map_severity("tipo_desconhecido", None, "qualquer coisa")
        assert result == ObjectionSeverity.MEDIUM

    def test_empty_type_defaults_to_low(self):
        """Tipo 'nenhuma' usa severidade LOW."""
        result = map_severity("nenhuma", None, "qualquer coisa")
        assert result == ObjectionSeverity.LOW
