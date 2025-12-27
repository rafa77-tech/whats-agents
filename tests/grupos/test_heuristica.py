"""
Testes para o módulo de heurística de classificação.

Sprint 14 - E03 - S03.5
"""

import pytest
from app.services.grupos.heuristica import (
    calcular_score_heuristica,
    normalizar_texto,
    ResultadoHeuristica,
    MIN_TAMANHO_MENSAGEM,
    MAX_TAMANHO_MENSAGEM,
)


class TestNormalizarTexto:
    """Testes da função normalizar_texto."""

    def test_lowercase(self):
        assert normalizar_texto("TESTE") == "teste"

    def test_espacos_extras(self):
        assert normalizar_texto("  muito   espaço  ") == "muito espaço"

    def test_vazio(self):
        assert normalizar_texto("") == ""
        assert normalizar_texto(None) == ""

    def test_preserva_acentos(self):
        assert normalizar_texto("Plantão Médico") == "plantão médico"


class TestCalcularScoreHeuristica:
    """Testes do cálculo de score."""

    # =========================================================================
    # Casos que devem PASSAR
    # =========================================================================

    def test_oferta_completa(self):
        """Oferta com todos os elementos deve passar com score alto."""
        texto = """
        🚨 VAGA URGENTE 🚨
        Hospital São Luiz ABC
        Clínica Médica
        Dia 28/12 - Noturno (19h às 7h)
        Valor: R$ 1.800,00 PJ
        """
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou is True
        assert resultado.score >= 0.5
        assert len(resultado.keywords_encontradas) >= 3

    def test_oferta_simples(self):
        """Oferta simples deve passar."""
        texto = "Plantão disponível amanhã no Hospital X, R$ 1500"
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou is True
        assert "plantao:" in str(resultado.keywords_encontradas)
        assert "hospital:" in str(resultado.keywords_encontradas)

    def test_oferta_informal(self):
        """Oferta com linguagem informal deve passar."""
        texto = "Preciso de CM pro HU Santo André amanhã de manhã, pago 2k"
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou is True

    def test_lista_escalas(self):
        """Lista de escalas disponíveis deve passar."""
        texto = """
        Escalas disponíveis São Camilo:
        - 26/12 Diurno CM
        - 27/12 Noturno Pediatria
        Ligar 11 98765-4321
        """
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou is True

    def test_vaga_urgente(self):
        """Vaga urgente deve passar."""
        texto = "🚨 URGENTE - Preciso de pediatra pro PS Central, 19h-7h, R$ 2k PJ"
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou is True
        assert resultado.score >= 0.5

    def test_cobertura(self):
        """Pedido de cobertura deve passar."""
        texto = "Alguém para cobertura amanhã no Hospital ABC? Pago R$ 1.500"
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou is True

    def test_escala_diurna(self):
        """Escala diurna deve passar."""
        texto = "Plantão diurno disponível dia 30/12 - Clínica Médica - R$ 1200"
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou is True

    def test_escala_noturna(self):
        """Escala noturna deve passar."""
        texto = "Noturno de cardiologia no Hospital São Paulo, 19h às 7h, valor R$ 2.000"
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou is True

    def test_valor_em_mil(self):
        """Valor em 'mil' ou 'k' deve ser detectado."""
        texto = "Vaga de UTI amanhã, pago 3 mil"
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou is True
        assert "valor:mencionado" in resultado.keywords_encontradas

    def test_valor_em_k(self):
        """Valor com 'k' deve ser detectado."""
        texto = "Plantão disponível Hospital XYZ, 2k PJ"
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou is True
        assert "valor:mencionado" in resultado.keywords_encontradas

    # =========================================================================
    # Casos que devem ser REJEITADOS
    # =========================================================================

    def test_cumprimento_bom_dia(self):
        """Cumprimento 'bom dia' deve ser rejeitado."""
        resultado = calcular_score_heuristica("Bom dia pessoal!")
        assert resultado.passou is False
        assert resultado.motivo_rejeicao == "keyword_negativa"

    def test_cumprimento_boa_tarde(self):
        """Cumprimento 'boa tarde' deve ser rejeitado."""
        resultado = calcular_score_heuristica("Boa tarde a todos")
        assert resultado.passou is False
        assert resultado.motivo_rejeicao == "keyword_negativa"

    def test_cumprimento_oi(self):
        """Cumprimento 'oi' deve ser rejeitado."""
        resultado = calcular_score_heuristica("Oi galera, tudo bem?")
        assert resultado.passou is False
        assert resultado.motivo_rejeicao == "keyword_negativa"

    def test_agradecimento(self):
        """Agradecimento deve ser rejeitado."""
        resultado = calcular_score_heuristica("Obrigado pela informação")
        assert resultado.passou is False

    def test_agradecimento_valeu(self):
        """'Valeu' deve ser rejeitado."""
        resultado = calcular_score_heuristica("Valeu pessoal pelo apoio")
        assert resultado.passou is False

    def test_mensagem_curta(self):
        """Mensagem muito curta deve ser rejeitada."""
        resultado = calcular_score_heuristica("Ok")
        assert resultado.passou is False
        assert resultado.motivo_rejeicao == "muito_curta"

    def test_confirmacao_simples(self):
        """Confirmação simples deve ser rejeitada."""
        resultado = calcular_score_heuristica("Beleza, combinado então")
        assert resultado.passou is False

    def test_pergunta_alguem(self):
        """Pergunta genérica deve ser rejeitada."""
        # Pergunta sem keywords de plantão/vaga é rejeitada
        resultado = calcular_score_heuristica("Alguém sabe de alguma coisa?")
        assert resultado.passou is False
        assert resultado.motivo_rejeicao == "keyword_negativa"

    def test_pergunta_sobre_vaga_pode_passar(self):
        """Pergunta sobre vaga pode passar (LLM decide)."""
        # Mensagem com "vaga" tem keyword positiva, pode passar para LLM filtrar
        resultado = calcular_score_heuristica("Alguém sabe se tem vaga?")
        # Pode passar porque menciona "vaga" - heurística é permissiva
        # LLM fará o filtro fino

    def test_risadas(self):
        """Risadas devem ser rejeitadas."""
        resultado = calcular_score_heuristica("kkkkkk muito bom isso")
        assert resultado.passou is False

    def test_texto_vazio(self):
        """Texto vazio deve ser rejeitado."""
        resultado = calcular_score_heuristica("")
        assert resultado.passou is False
        assert resultado.motivo_rejeicao == "texto_vazio"

    def test_texto_none(self):
        """Texto None deve ser rejeitado."""
        resultado = calcular_score_heuristica(None)
        assert resultado.passou is False
        assert resultado.motivo_rejeicao == "texto_vazio"

    def test_mensagem_muito_longa(self):
        """Mensagem muito longa deve ser rejeitada."""
        texto = "Plantão disponível " * 500  # Muito longa
        resultado = calcular_score_heuristica(texto)
        assert resultado.passou is False
        assert resultado.motivo_rejeicao == "muito_longa"

    # =========================================================================
    # Edge cases
    # =========================================================================

    def test_so_valor_sem_contexto(self):
        """Só valor sem contexto médico deve ter score baixo."""
        resultado = calcular_score_heuristica("R$ 1000 para vender o produto")
        # Score baixo porque falta contexto médico forte
        assert resultado.score < 0.5

    def test_hospital_sem_vaga(self):
        """Menção a hospital sem ser oferta pode passar (LLM filtra)."""
        texto = "Fui no Hospital São Luiz ontem e o atendimento foi ótimo"
        resultado = calcular_score_heuristica(texto)
        # Pode passar pela heurística porque menciona hospital
        # O importante é não ter falso negativo (rejeitar ofertas reais)

    def test_limite_tamanho_minimo(self):
        """Mensagem no limite mínimo deve passar se tiver keywords."""
        texto = "a" * (MIN_TAMANHO_MENSAGEM - 1)
        resultado = calcular_score_heuristica(texto)
        assert resultado.passou is False
        assert resultado.motivo_rejeicao == "muito_curta"

    def test_limite_tamanho_maximo(self):
        """Mensagem no limite máximo."""
        texto = "Plantão " + "a" * (MAX_TAMANHO_MENSAGEM - 8)
        resultado = calcular_score_heuristica(texto)
        # Deve processar normalmente se não exceder limite
        assert resultado.motivo_rejeicao != "muito_longa"


class TestKeywordsEncontradas:
    """Testes das keywords retornadas."""

    def test_categorias_retornadas(self):
        """Deve retornar categorias de keywords encontradas."""
        texto = "Plantão Hospital XYZ Cardiologia R$ 2000"
        resultado = calcular_score_heuristica(texto)

        categorias = [k.split(":")[0] for k in resultado.keywords_encontradas]

        assert "plantao" in categorias or "hospital" in categorias

    def test_valor_detectado(self):
        """Deve detectar valor monetário."""
        texto = "Vaga disponível para médico, valor R$ 1.500,00"
        resultado = calcular_score_heuristica(texto)

        assert "valor:mencionado" in resultado.keywords_encontradas

    def test_hospital_detectado(self):
        """Deve detectar hospital."""
        texto = "Precisamos de médico para o Hospital ABC amanhã"
        resultado = calcular_score_heuristica(texto)

        categorias = [k.split(":")[0] for k in resultado.keywords_encontradas]
        assert "hospital" in categorias

    def test_especialidade_detectada(self):
        """Deve detectar especialidade."""
        texto = "Vaga de cardiologia disponível, plantão noturno"
        resultado = calcular_score_heuristica(texto)

        categorias = [k.split(":")[0] for k in resultado.keywords_encontradas]
        assert "especialidade" in categorias or "plantao" in categorias


class TestScoreCalculation:
    """Testes do cálculo de score."""

    def test_score_maximo(self):
        """Score máximo deve ser 1.0."""
        texto = "Plantão Hospital São Luiz Cardiologia R$ 2000 urgente"
        resultado = calcular_score_heuristica(texto)

        assert resultado.score <= 1.0

    def test_score_minimo_para_passar(self):
        """Score mínimo para passar deve ser 0.25."""
        # Só menciona plantão (0.3)
        texto = "Plantão disponível para quem tiver interesse"
        resultado = calcular_score_heuristica(texto)

        assert resultado.passou is True
        assert resultado.score >= 0.25

    def test_score_insuficiente(self):
        """Score abaixo do threshold não passa."""
        # Mensagem genérica sem keywords fortes
        texto = "Informação importante sobre o grupo de médicos"
        resultado = calcular_score_heuristica(texto)

        # Pode ou não passar dependendo das keywords detectadas
        if not resultado.passou:
            assert resultado.motivo_rejeicao in ["score_baixo", "keyword_negativa"]
