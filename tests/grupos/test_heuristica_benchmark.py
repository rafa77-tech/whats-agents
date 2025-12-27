"""
Benchmark de performance da heurística.

Sprint 14 - E03 - S03.6

Meta: Processar 1000 mensagens em < 1 segundo
"""

import pytest
import time
from app.services.grupos.heuristica import calcular_score_heuristica


MENSAGENS_TESTE = [
    "Bom dia pessoal",
    "Plantão disponível Hospital São Luiz amanhã R$ 1500",
    "Obrigado",
    "Vaga urgente CM noturno 28/12",
    "Alguém sabe de vaga?",
    "🚨 URGENTE - Preciso de pediatra pro PS Central, 19h-7h, R$ 2k PJ",
    "Ok",
    "Escalas disponíveis: 26/12, 27/12, 28/12 - Clínica Médica",
    "kkkkkk",
    "Hospital XYZ precisa de anestesista para cobertura amanhã",
] * 100  # 1000 mensagens


class TestHeuristicaBenchmark:
    """Testes de performance da heurística."""

    def test_performance_1000_mensagens(self):
        """Deve processar 1000 mensagens em menos de 1 segundo."""
        inicio = time.time()

        for texto in MENSAGENS_TESTE:
            calcular_score_heuristica(texto)

        duracao = time.time() - inicio

        assert duracao < 1.0, f"Demorou {duracao:.2f}s para 1000 mensagens"
        print(f"\nBenchmark: 1000 mensagens em {duracao:.3f}s ({1000/duracao:.0f} msg/s)")

    def test_mensagem_longa(self):
        """Deve processar mensagem longa rapidamente."""
        texto_longo = "Plantão disponível " * 500

        inicio = time.time()
        resultado = calcular_score_heuristica(texto_longo)
        duracao = time.time() - inicio

        assert duracao < 0.01  # < 10ms
        assert resultado.passou is False  # Muito longa

    def test_mensagem_curta(self):
        """Deve processar mensagem curta instantaneamente."""
        inicio = time.time()

        for _ in range(1000):
            calcular_score_heuristica("Ok")

        duracao = time.time() - inicio

        assert duracao < 0.1  # < 100ms para 1000 mensagens curtas

    def test_mensagens_com_muitas_keywords(self):
        """Deve processar mensagens complexas rapidamente."""
        texto = """
        🚨 VAGA URGENTE 🚨
        Hospital São Luiz ABC
        Clínica Médica / Cardiologia / UTI
        Dia 28/12, 29/12, 30/12 - Noturno (19h às 7h)
        Valor: R$ 1.800,00 PJ
        Preciso de médico plantonista com CRM ativo
        Contato: 11 99999-9999
        """

        inicio = time.time()

        for _ in range(100):
            calcular_score_heuristica(texto)

        duracao = time.time() - inicio

        assert duracao < 0.5  # < 500ms para 100 mensagens complexas
        print(f"\nBenchmark complexo: 100 mensagens em {duracao:.3f}s")

    def test_consistencia_resultados(self):
        """Resultados devem ser consistentes em múltiplas execuções."""
        texto = "Plantão Hospital ABC R$ 1500 noturno"

        resultados = [calcular_score_heuristica(texto) for _ in range(100)]

        # Todos os resultados devem ser iguais
        primeiro = resultados[0]
        for r in resultados[1:]:
            assert r.passou == primeiro.passou
            assert r.score == primeiro.score
            assert r.keywords_encontradas == primeiro.keywords_encontradas
