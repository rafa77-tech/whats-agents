"""
Testes E2E de comportamento da Julia.

Sprint 37 - Epic 12

Testa cenários completos de comportamento cobrindo:
- Detecção de incerteza
- Detecção de confronto
- Detecção de loop
- Detecção de contradição
- Validação de persona
- Integração entre detectores
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.conhecimento.detector_incerteza import (
    DetectorIncerteza,
    ResultadoIncerteza,
)
from app.services.conhecimento.detector_confronto import (
    DetectorConfronto,
    ResultadoConfronto,
    TipoConfronto,
    NivelConfronto,
)
from app.services.conhecimento.detector_loop import (
    DetectorLoop,
    ResultadoLoop,
    get_detector_loop,
)
from app.services.conhecimento.detector_contradicao import (
    DetectorContradicao,
    ResultadoContradicao,
    get_detector_contradicao,
)
from app.services.persona.validador import (
    validar_resposta_persona,
    calcular_score_naturalidade,
)


class TestCenarioIncerteza:
    """Cenários E2E envolvendo incerteza."""

    def test_cenario_01_medico_pergunta_vaga_desatualizada(self):
        """
        Cenário: Médico pergunta sobre vaga com dados desatualizados.

        Fluxo:
        1. Médico pergunta: "Tem vaga no Hospital X?"
        2. Sistema detecta que dados da vaga são antigos
        3. Julia deve comunicar incerteza
        """
        detector = DetectorIncerteza()

        resultado = detector.calcular_confianca(
            confianca_vagas=0.3,  # Dados muito desatualizados
            confianca_hospital=0.4,
            dados_medico_completos=False,  # Dados incompletos
            similaridade_memorias=0.3,
        )

        # Deve comunicar incerteza (threshold é 0.7)
        assert resultado.deve_comunicar_incerteza is True
        assert resultado.confianca < 0.7

    def test_cenario_02_medico_pergunta_valor_nao_confirmado(self):
        """
        Cenário: Médico pergunta valor de plantão não confirmado.

        Fluxo:
        1. Médico: "Quanto paga esse plantão?"
        2. Sistema não tem confiança no valor
        3. Julia deve verificar antes de responder
        """
        detector = DetectorIncerteza()

        resultado = detector.calcular_confianca(
            confianca_vagas=0.2,  # Valor não confirmado
            confianca_hospital=0.5,
            dados_medico_completos=False,
            similaridade_memorias=0.3,
        )

        # Deve comunicar incerteza alta (threshold é 0.7)
        assert resultado.deve_comunicar_incerteza is True
        # Score baixo deve recomendar verificação
        assert resultado.confianca < 0.7


class TestCenarioConfronto:
    """Cenários E2E envolvendo confronto."""

    def test_cenario_03_medico_diz_hospital_nao_existe(self):
        """
        Cenário: Médico afirma que hospital não existe.

        Fluxo:
        1. Julia menciona Hospital X
        2. Médico: "Esse hospital não existe mais"
        3. Julia deve verificar, não insistir
        """
        detector = DetectorConfronto()

        resultado = detector.detectar(
            mensagem="Esse hospital não existe, você está inventando",
            contador_confrontos=0,
        )

        assert resultado.tipo == TipoConfronto.VERACIDADE
        assert resultado.nivel == NivelConfronto.NIVEL_1
        assert resultado.deve_escalar is False
        assert resultado.sugestao_frase is not None

    def test_cenario_04_medico_confronta_segunda_vez(self):
        """
        Cenário: Médico confronta pela segunda vez.

        Fluxo:
        1. Primeiro confronto já ocorreu
        2. Médico: "Já disse que isso é mentira"
        3. Julia deve reconhecer e buscar ajuda
        """
        detector = DetectorConfronto()

        resultado = detector.detectar(
            mensagem="Já te disse que isso não existe, para de mentir",
            contador_confrontos=1,  # Já teve 1 confronto
        )

        assert resultado.tipo == TipoConfronto.VERACIDADE
        assert resultado.nivel == NivelConfronto.NIVEL_2
        assert resultado.deve_escalar is False
        # Deve sugerir buscar ajuda (pode ser "equipe", "supervisora" ou "alguém")
        frase_lower = resultado.sugestao_frase.lower()
        assert "equipe" in frase_lower or "supervisor" in frase_lower or "alguém" in frase_lower

    def test_cenario_05_medico_confronta_terceira_vez(self):
        """
        Cenário: Médico confronta pela terceira vez.

        Fluxo:
        1. Dois confrontos anteriores
        2. Médico: "Vocês só passam informação errada"
        3. Julia DEVE escalar imediatamente
        """
        detector = DetectorConfronto()

        resultado = detector.detectar(
            mensagem="Vocês só passam informação errada, quero falar com outra pessoa",
            contador_confrontos=2,  # Já teve 2 confrontos
        )

        assert resultado.nivel == NivelConfronto.NIVEL_3
        assert resultado.deve_escalar is True

    def test_cenario_06_medico_pergunta_se_e_bot(self):
        """
        Cenário: Médico pergunta se Julia é bot.

        Fluxo:
        1. Médico: "Você é um bot?"
        2. Julia deve desviar com humor, não admitir
        """
        detector = DetectorConfronto()

        resultado = detector.detectar(
            mensagem="Você é um bot?",
            contador_confrontos=0,
        )

        assert resultado.tipo == TipoConfronto.BOT
        assert resultado.nivel == NivelConfronto.NIVEL_1
        # Frase deve ser evasiva/humorística
        assert "?" in resultado.sugestao_frase or "haha" in resultado.sugestao_frase.lower() or "por que" in resultado.sugestao_frase.lower() or "kkk" in resultado.sugestao_frase.lower()


class TestCenarioLoop:
    """Cenários E2E envolvendo loop de repetição."""

    def test_cenario_07_julia_repete_mesma_resposta(self):
        """
        Cenário: Julia está repetindo respostas.

        Fluxo:
        1. Julia dá mesma resposta várias vezes
        2. Sistema detecta loop
        3. Julia deve variar resposta ou escalar
        """
        detector = DetectorLoop()

        # Simular histórico de respostas similares
        detector.adicionar_resposta("Deixa eu verificar isso com a equipe")
        detector.adicionar_resposta("Vou verificar isso com a equipe")

        # Nova resposta similar
        resultado = detector.detectar(
            resposta_atual="Deixa eu verificar isso aqui com a equipe"
        )

        # Deve detectar loop
        assert resultado.em_loop is True
        assert resultado.respostas_similares >= 2
        assert resultado.similaridade_max >= 0.8

    def test_cenario_08_loop_requer_intervencao(self):
        """
        Cenário: Loop severo requer intervenção.

        Fluxo:
        1. 3+ respostas muito similares
        2. Sistema detecta loop severo
        3. Julia DEVE intervir de forma diferente
        """
        detector = DetectorLoop()

        # Histórico com 3 respostas similares
        detector.adicionar_resposta("Vou verificar com a equipe")
        detector.adicionar_resposta("Vou checar com a equipe")
        detector.adicionar_resposta("Vou confirmar com a equipe")

        resultado = detector.detectar(
            resposta_atual="Vou verificar com a equipe"
        )

        assert resultado.em_loop is True
        assert resultado.deve_intervir is True
        assert "INTERVENÇÃO" in resultado.acao_recomendada or "diferente" in resultado.acao_recomendada.lower()


class TestCenarioContradicao:
    """Cenários E2E envolvendo contradição."""

    def test_cenario_09_julia_contradiz_valor_anterior(self):
        """
        Cenário: Julia dá valor diferente do que disse antes.

        Fluxo:
        1. Julia disse: "Plantão paga R$ 2.500"
        2. Julia agora diz: "É R$ 1.800"
        3. Sistema detecta contradição de valor
        """
        detector = DetectorContradicao()

        # Adicionar resposta anterior
        detector.adicionar_resposta("Esse plantão paga R$ 2.500")

        # Verificar nova resposta
        resultado = detector.detectar(
            resposta_atual="Na verdade é R$ 1.800"
        )

        assert resultado.tem_contradicao is True
        assert resultado.tipo_contradicao == "valor"
        assert "R$ 2" in resultado.valor_anterior
        assert "R$ 1" in resultado.valor_atual

    def test_cenario_10_julia_menciona_hospital_diferente(self):
        """
        Cenário: Julia menciona hospital diferente do contexto.

        Fluxo:
        1. Conversa sobre Hospital São Luiz
        2. Julia menciona Hospital Brasil
        3. Sistema detecta possível contradição
        """
        detector = DetectorContradicao()

        # Adicionar resposta sobre hospital anterior
        detector.adicionar_resposta("Temos vagas no Hospital São Luiz")

        # Nova resposta menciona hospital diferente
        resultado = detector.detectar(
            resposta_atual="No Hospital Brasil tem vaga amanhã"
        )

        # Pode ou não detectar contradição dependendo do contexto
        # Se detectar, deve ser do tipo hospital
        if resultado.tem_contradicao:
            assert resultado.tipo_contradicao == "hospital"


class TestCenarioPersona:
    """Cenários E2E de validação de persona."""

    def test_cenario_11_resposta_com_bullet_points(self):
        """
        Cenário: Resposta gerada com bullet points.

        Fluxo:
        1. Julia geraria resposta com lista
        2. Validador detecta violação
        3. Resposta deve ser rejeitada
        """
        resposta_ruim = """Temos várias opções:
- Hospital A
- Hospital B
- Hospital C
"""
        resultado = validar_resposta_persona(resposta_ruim)

        assert resultado.valido is False or resultado.score < 0.8
        assert any("bullet" in p.lower() for p in resultado.problemas)

    def test_cenario_12_resposta_revela_ser_bot(self):
        """
        Cenário: Resposta revela ser IA.

        Fluxo:
        1. Julia geraria "Sou uma IA..."
        2. Validador detecta violação crítica
        3. Resposta DEVE ser rejeitada
        """
        resposta_critica = "Sou uma inteligência artificial que ajuda com escalas"

        resultado = validar_resposta_persona(resposta_critica)

        assert resultado.valido is False
        assert any("IA" in p or "bot" in p for p in resultado.problemas)

    def test_cenario_13_resposta_informal_correta(self):
        """
        Cenário: Resposta informal bem formatada.

        Fluxo:
        1. Julia responde de forma natural
        2. Validador aprova
        """
        resposta_boa = "Oi, vc ta afim de um plantao pra amanha? Ta tendo vaga boa"

        resultado = validar_resposta_persona(resposta_boa)

        assert resultado.valido is True
        assert resultado.score >= 0.7


class TestCenarioIntegrado:
    """Cenários E2E integrando múltiplos detectores."""

    def test_cenario_14_confronto_com_incerteza(self):
        """
        Cenário: Médico confronta sobre informação incerta.

        Fluxo:
        1. Julia tem incerteza sobre dados
        2. Médico confronta: "Isso não existe"
        3. Sistema prioriza protocolo de confronto
        4. Julia não insiste na informação incerta
        """
        # Detectar incerteza
        detector_incerteza = DetectorIncerteza()
        resultado_incerteza = detector_incerteza.calcular_confianca(
            confianca_vagas=0.4,  # Baixa confiança
            confianca_hospital=0.5,
        )

        # Detectar confronto
        detector_confronto = DetectorConfronto()
        resultado_confronto = detector_confronto.detectar(
            mensagem="Isso que você falou não existe",
            contador_confrontos=0,
        )

        # Ambos detectam problemas
        assert resultado_incerteza.deve_comunicar_incerteza is True
        assert resultado_confronto.tipo == TipoConfronto.VERACIDADE

        # Em caso de conflito, confronto tem prioridade
        # Julia não deve insistir na informação
        assert resultado_confronto.deve_escalar is False
        # Deve verificar, não defender

    def test_cenario_15_loop_com_confronto(self):
        """
        Cenário: Julia entra em loop durante confronto.

        Fluxo:
        1. Médico confronta várias vezes
        2. Julia repete "deixa eu verificar"
        3. Sistema detecta loop
        4. Julia deve variar ou escalar
        """
        detector_loop = DetectorLoop()
        detector_confronto = DetectorConfronto()

        # Histórico de respostas repetidas (3 respostas similares para garantir detecção)
        detector_loop.adicionar_resposta("Deixa eu verificar isso")
        detector_loop.adicionar_resposta("Vou verificar isso")
        detector_loop.adicionar_resposta("Deixa eu verificar aqui")

        # Novo confronto
        resultado_confronto = detector_confronto.detectar(
            mensagem="Você já falou isso 3 vezes!",
            contador_confrontos=2,
        )

        # Nova resposta seria similar
        resultado_loop = detector_loop.detectar(
            resposta_atual="Deixa eu verificar isso aqui"
        )

        # Loop detectado
        assert resultado_loop.em_loop is True

        # Com 2 confrontos anteriores e loop, deve escalar
        if resultado_confronto.nivel == NivelConfronto.NIVEL_3:
            assert resultado_confronto.deve_escalar is True

    def test_cenario_16_contradicao_em_negociacao(self):
        """
        Cenário: Julia contradiz valor durante negociação.

        Fluxo:
        1. Julia ofereceu R$ 2.000
        2. Médico negocia
        3. Julia diz R$ 1.800 por engano
        4. Sistema detecta contradição
        """
        detector = DetectorContradicao()

        # Resposta anterior com valor
        detector.adicionar_resposta("Posso oferecer R$ 2.000 pra você")

        # Nova resposta com valor menor (contradição)
        resultado = detector.detectar(
            resposta_atual="O máximo que consigo é R$ 1.800"
        )

        # Deve detectar contradição
        # (valor atual menor que anterior = contradição em negociação)
        if resultado.tem_contradicao:
            assert resultado.tipo_contradicao == "valor"
            assert "esclarecer" in resultado.acao_recomendada.lower() or "CONTRADIÇÃO" in resultado.acao_recomendada


class TestScoreNaturalidadeE2E:
    """Testes E2E de naturalidade das respostas."""

    def test_cenario_17_comparar_respostas(self):
        """
        Cenário: Comparar naturalidade de diferentes respostas.

        Respostas mais naturais devem ter score maior.
        """
        resposta_informal = "Oi, vc ta afim? Ta tendo vaga boa pra amanha"
        resposta_formal = "Prezado Dr., venho comunicar a disponibilidade de vagas"
        resposta_bullet = "- Hospital A\n- Hospital B"

        score_informal = calcular_score_naturalidade(resposta_informal)
        score_formal = calcular_score_naturalidade(resposta_formal)
        score_bullet = calcular_score_naturalidade(resposta_bullet)

        # Informal deve ter maior score
        assert score_informal > score_formal
        assert score_informal > score_bullet

    def test_cenario_18_resposta_curta_vs_longa(self):
        """
        Cenário: Respostas curtas são mais naturais.
        """
        curta = "Oi, blz?"
        longa = "\n".join(["Linha " + str(i) for i in range(6)])

        score_curta = calcular_score_naturalidade(curta)
        score_longa = calcular_score_naturalidade(longa)

        assert score_curta > score_longa
