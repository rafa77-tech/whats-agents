"""
Testes para formatadores interativos de vagas.

Sprint 67 (Chunk 8) — 2 testes.
"""

from app.tools.response_formatter import VagasResponseFormatter


class TestVagasInteractiveFormatters:
    """Testes dos métodos de formatação interativa."""

    def setup_method(self):
        self.formatter = VagasResponseFormatter()
        self.vagas = [
            {
                "hospital": "Hospital São Luiz",
                "data": "2026-03-01",
                "periodo": "Noturno",
                "valor_display": "R$ 2.500",
            },
            {
                "hospital": "Hospital Albert Einstein",
                "data": "2026-03-02",
                "periodo": "Diurno",
                "valor_display": "R$ 3.000",
            },
        ]

    def test_formatar_vagas_interactive_list(self):
        """Deve gerar payload de lista com itens formatados."""
        result = self.formatter.formatar_vagas_interactive_list(
            self.vagas, "Cardiologia"
        )
        assert "texto" in result
        assert "botao_texto" in result
        assert "itens" in result
        assert len(result["itens"]) == 2
        assert result["botao_texto"] == "Ver vagas"
        # Cada item deve ter titulo e descricao
        for item in result["itens"]:
            assert "titulo" in item
            assert "descricao" in item
            assert len(item["titulo"]) <= 24
            assert len(item["descricao"]) <= 72

    def test_formatar_vagas_interactive_buttons(self):
        """Deve gerar payload de botões para até 3 vagas."""
        result = self.formatter.formatar_vagas_interactive_buttons(
            self.vagas, "Cardiologia"
        )
        assert result is not None
        assert "texto" in result
        assert "opcoes" in result
        assert len(result["opcoes"]) == 2
        for opcao in result["opcoes"]:
            assert len(opcao) <= 20

        # Mais de 3 vagas deve retornar None
        muitas_vagas = self.vagas * 3  # 6 vagas
        result_none = self.formatter.formatar_vagas_interactive_buttons(muitas_vagas)
        assert result_none is None
